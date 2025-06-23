"""
Streaming log processor - processes Jenkins build logs one by one in memory.
"""

import datetime as _dt
import sys
from collections import defaultdict
from typing import Dict, Tuple

from jenkins_client import JenkinsClient
from log_analyzer import LogAnalyzer
from config import DEFAULT_WINDOW_HOURS, DEFAULT_COUNT


class StreamingLogProcessor:
    """Processes Jenkins build logs one by one in memory without saving to disk."""
    
    def __init__(self, jenkins_client: JenkinsClient):
        self.client = jenkins_client
        self.analyzer = LogAnalyzer()
    
    def _fetch_log_content(self, build_url: str) -> str:
        """Fetch build log content directly into memory."""
        import urllib.parse as _url
        import requests
        
        log_url = _url.urljoin(build_url, 'consoleText')
        try:
            r = requests.get(log_url, auth=self.client.auth, timeout=60)
            r.raise_for_status()
            return r.text
        except Exception as exc:
            print(f"[WARN] Failed to fetch log for {build_url}: {exc}", file=sys.stderr)
            return ""
    
    def process_failed_builds(self, window_hours: int = DEFAULT_WINDOW_HOURS, 
                            max_builds_per_job: int = DEFAULT_COUNT) -> Tuple[Dict, int, int]:
        """
        Process failed build logs for all jobs in memory.
        
        Returns:
            Tuple of (job_exceptions_dict, total_failed_jobs, total_failed_builds)
        """
        cutoff = int((_dt.datetime.now(_dt.UTC) - _dt.timedelta(hours=window_hours)).timestamp() * 1000)
        
        try:
            print(f"Fetching jobs…")
            jobs = self.client.get_jobs()
            print(f"Found {len(jobs)} jobs")
        except Exception as exc:
            sys.exit(f'Error fetching job list: {exc}')

        if not jobs:
            print('No jobs found – check credentials / folder permissions', file=sys.stderr)
            return {}, 0, 0

        job_exceptions = defaultdict(lambda: defaultdict(lambda: {"count": 0, "latest_line": "", "build_urls": []}))
        total_failed_jobs = 0
        total_failed_builds = 0

        for job in jobs:
            try:
                failures = self.client.get_failed_builds(job['url'], cutoff, max_builds_per_job)
            except Exception as exc:
                # Check if it's a server error (502, 503, etc.)
                if "502" in str(exc) or "Bad Gateway" in str(exc):
                    print(f"[WARN] Skipping job '{job['name']}' – Jenkins server error (502 Bad Gateway). This may be due to special characters in the job name or server issues.", file=sys.stderr)
                else:
                    print(f"[WARN] Skipping job '{job['name']}' – {exc}", file=sys.stderr)
                continue

            if failures:
                job_has_failures = False
                job_name = job['name']
                
                print(f"Processing logs for job: {job_name} ({len(failures)} failed builds)")
                
                for build in failures:
                    # Fetch log content directly into memory
                    log_content = self._fetch_log_content(build['url'])
                    
                    if log_content:
                        job_has_failures = True
                        total_failed_builds += 1
                        
                        # Analyze the log content in memory
                        exception_line, context = self.analyzer.extract_exception_from_log(log_content)
                        
                        # Extract exception type
                        exception_type = self.analyzer._extract_exception_type(exception_line)
                        
                        # Count occurrences and keep latest
                        job_exceptions[job_name][exception_type]["count"] += 1
                        job_exceptions[job_name][exception_type]["latest_line"] = exception_line
                        
                        # Add build URL if not already present
                        build_url = build['url']
                        if build_url not in job_exceptions[job_name][exception_type]["build_urls"]:
                            job_exceptions[job_name][exception_type]["build_urls"].append(build_url)
                        
                        # Format timestamp for display
                        ts = _dt.datetime.fromtimestamp(build['timestamp'] / 1000, tz=_dt.UTC).strftime('%Y%m%d_%H%M%S')
                        print(f"  Processed: build_{build['number']}_{ts} -> {exception_type}")
                    else:
                        # Log fetch failed
                        job_exceptions[job_name]["LogFetchError"]["count"] += 1
                        job_exceptions[job_name]["LogFetchError"]["latest_line"] = "Error fetching log content"
                        job_exceptions[job_name]["LogFetchError"]["build_urls"].append(build['url'])
                        print(f"  Failed to fetch: build_{build['number']}")
                
                if job_has_failures:
                    total_failed_jobs += 1

        print(f"\nSummary:")
        print(f"  Jobs with failures: {total_failed_jobs}")
        print(f"  Total failed builds processed: {total_failed_builds}")
        print(f"  Processed entirely in memory (no disk usage)")
        
        return dict(job_exceptions), total_failed_jobs, total_failed_builds
