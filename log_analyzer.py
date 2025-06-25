"""
Log analysis module for extracting exceptions and context from Jenkins build logs.
"""

import re
from typing import Dict, Tuple, List


class LogAnalyzer:
    """Analyzer for Jenkins build logs to extract exceptions and context."""
    
    @staticmethod
    def extract_exception_from_log(log_content: str, ignore_exceptions: List[str] = None) -> Tuple[str, str]:
        """Extract the latest line containing 'Exception' from a log file with extended context, excluding ignored exceptions."""
        if ignore_exceptions is None:
            ignore_exceptions = []
        
        lines = log_content.strip().split('\n')
        
        # Find the latest timestamp line (pattern: YYYY-MM-DD HH:MM:SS)
        timestamp_pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        latest_timestamp_index = -1
        
        for i in range(len(lines) - 1, -1, -1):
            if re.match(timestamp_pattern, lines[i]):
                latest_timestamp_index = i
                break
        
        # Look for the last line containing a real Python exception
        # Match patterns like: "SomeException:", "module.SomeException:", etc.
        exception_index = -1
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            # Look for actual exception patterns (not just any line containing "Exception")
            # Pattern: word boundary + Exception type + colon
            if re.search(r'\b\w*Exception\s*:', line) or re.search(r'\b\w*Error\s*:', line):
                # Exclude common false positives
                if not any(exclude in line for exclude in [
                    '<method', 'with_traceback', 'of \'', 'objects>',
                    'raise', 'except', 'try:', 'catch'
                ]):
                    # Check if this exception should be ignored
                    should_ignore = False
                    for ignore_pattern in ignore_exceptions:
                        if ignore_pattern and ignore_pattern in line:
                            should_ignore = True
                            break
                    
                    if not should_ignore:
                        exception_index = i
                        break
        
        if exception_index != -1:
            # If the latest timestamp is after the exception, find an earlier timestamp
            if latest_timestamp_index != -1 and latest_timestamp_index > exception_index:
                # Find the timestamp before the exception
                for i in range(exception_index - 1, -1, -1):
                    if re.match(timestamp_pattern, lines[i]):
                        latest_timestamp_index = i
                        break
            
            # Get context from latest timestamp to build failure marker (exclusive)
            if latest_timestamp_index != -1:
                context_start = latest_timestamp_index
            else:
                context_start = max(0, exception_index - 10)
            
            # Find the end point - stop before "Build step 'Execute shell' marked build as failure"
            context_end = len(lines)
            for i in range(context_start, len(lines)):
                if "Build step 'Execute shell' marked build as failure" in lines[i]:
                    context_end = i  # Don't include the build failure line
                    break
            
            context_lines = lines[context_start:context_end]
            context = '\n'.join(context_lines)
            return lines[exception_index].strip(), context
        
        # Fallback to other error patterns if no Exception found
        error_patterns = [
            r'ERROR:',
            r'FATAL:',
            r'FAILED',
            r'Build step.*failed'
        ]
        
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            for pattern in error_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Check if this error line should be ignored
                    should_ignore = False
                    for ignore_pattern in ignore_exceptions:
                        if ignore_pattern and ignore_pattern in line:
                            should_ignore = True
                            break
                    
                    if not should_ignore:
                        if latest_timestamp_index != -1:
                            context_start = latest_timestamp_index
                        else:
                            context_start = max(0, i - 10)
                        
                        # Find the end point - stop before "Build step 'Execute shell' marked build as failure"
                        context_end = len(lines)
                        for j in range(context_start, len(lines)):
                            if "Build step 'Execute shell' marked build as failure" in lines[j]:
                                context_end = j  # Don't include the build failure line
                                break
                        
                        context_lines = lines[context_start:context_end]
                        context = '\n'.join(context_lines)
                        return line.strip(), context
        
        return "No clear error found", ""
    
    @staticmethod
    def _extract_exception_type(exception_line: str) -> str:
        """Extract the exception type from an exception line, handling various formats."""
        if not exception_line:
            return "Unknown"
        
        # Remove leading timestamp and log level if present
        import re
        # Pattern: YYYY-MM-DD HH:MM:SS[.mmm] [|] [LEVEL] [|] 
        timestamp_pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:[.,]\d+)?\s*(?:\|\s*)?(?:INFO|ERROR|WARN|DEBUG|FATAL|TRACE)?\s*(?:\|\s*)?'
        line_without_timestamp = re.sub(timestamp_pattern, '', exception_line).strip()
        
        if not line_without_timestamp:
            return "Unknown"
        
        # Look for Python exception patterns (SomeException: message)
        exception_pattern = r'^([A-Za-z_][A-Za-z0-9_.]*(?:Exception|Error|Warning))\s*:'
        match = re.match(exception_pattern, line_without_timestamp)
        if match:
            return match.group(1)
        
        # Look for other error patterns with colon
        if ':' in line_without_timestamp:
            # Split on first colon and check if the first part looks like an exception
            parts = line_without_timestamp.split(':', 1)
            potential_exception = parts[0].strip()
            
            # Check if it looks like a Python exception (contains dots, ends with Exception/Error)
            if ('.' in potential_exception and 
                (potential_exception.endswith('Exception') or 
                 potential_exception.endswith('Error') or
                 potential_exception.endswith('Warning'))):
                return potential_exception
            
            # Check if it's a single word that might be an exception
            if (len(potential_exception.split()) == 1 and 
                potential_exception[0].isupper() and
                len(potential_exception) > 3):
                return potential_exception
        
        # Fallback: use first word if it looks like an error
        first_word = line_without_timestamp.split()[0] if line_without_timestamp.split() else "Unknown"
        
        # Common error patterns
        if any(pattern in first_word.lower() for pattern in ['error', 'exception', 'failed', 'fatal']):
            return first_word
        
        return "BuildFailure"
    
    @staticmethod
    def _normalize_exception_line(exception_line: str) -> str:
        """Normalize exception line by removing timestamps only."""
        if not exception_line:
            return exception_line
        
        # Remove leading timestamp and log level if present
        # Pattern: YYYY-MM-DD HH:MM:SS[.mmm] [|] [LEVEL] [|]
        timestamp_pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:[.,]\d+)?\s*(?:\|\s*)?(?:INFO|ERROR|WARN|DEBUG|FATAL|TRACE)?\s*(?:\|\s*)?'
        normalized = re.sub(timestamp_pattern, '<timestamp>', exception_line).strip()
        
        # Replace very long token-like strings with <token>
        # Matches quoted strings longer than 50 characters that look like tokens (base64, API keys, etc.)
        normalized = re.sub(r"'[A-Za-z0-9+/=_-]{50,}'", "'<token>'", normalized)
        normalized = re.sub(r'"[A-Za-z0-9+/=_-]{50,}"', '"<token>"', normalized)
        
        # Clean up any leading colons left over
        normalized = re.sub(r'^:\s*', '', normalized)
        
        return normalized

    def print_console_summary(self, job_exceptions: Dict):
        """Print summary to console."""
        print("\n=== JENKINS FAILURE EXCEPTIONS SUMMARY ===\n")
        
        for job_name, exceptions in sorted(job_exceptions.items()):
            print(f"🔴 {job_name}:")
            
            for exception_type, data in sorted(exceptions.items()):
                print(f"   📊 {exception_type} ({data['count']} occurrences)")
                
                # Print all unique exception messages
                for message, build_urls in data['unique_messages'].items():
                    print(f"      Exception: {message}")
                    if build_urls:
                        print(f"\n      Build URLs:")
                        for url in build_urls[:3]:  # Show max 3 URLs
                            print(f"         🔗 {url}")
                        if len(build_urls) > 3:
                            print(f"         ... and {len(build_urls) - 3} more")
                    else:
                        print(f"\n      Build URLs: No URLs available")
                    print()
            print()
