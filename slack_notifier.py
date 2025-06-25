"""
Slack notification module for sending Jenkins failure analysis results.
"""

from typing import Dict, Optional, Tuple
from urllib.parse import quote

import requests

from config import SLACK_BOT_TOKEN, SLACK_CHANNEL, WINDOW_HOURS, MAX_FAILURES_COUNT_PER_JOB, JENKINS_URL


class SlackNotifier:
    """Handles Slack notifications for Jenkins failure analysis."""
    
    def __init__(self, bot_token: str = None, channel: str = None):
        self.bot_token = bot_token or SLACK_BOT_TOKEN
        self.channel = channel or SLACK_CHANNEL
    
    def _send_message(self, payload: Dict, message_type: str, thread_ts: str = None) -> Tuple[bool, Optional[str]]:
        """Send a message using Slack Web API."""
        if not self.bot_token:
            print("❌ SLACK_BOT_TOKEN not configured. Cannot send Slack notifications.")
            return False, None
            
        if not self.channel:
            print("❌ SLACK_CHANNEL not configured. Cannot send Slack notifications.")
            return False, None
            
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json"
        }
        
        # Add channel and thread_ts to payload
        payload["channel"] = self.channel
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                ts = result.get("ts")
                print(f"✅ {message_type} Slack message sent successfully!")
                return True, ts
            else:
                print(f"❌ Slack API error for {message_type}: {result.get('error', 'Unknown error')}")
                return False, None
                
        except Exception as e:
            print(f"❌ Failed to send {message_type} Slack message: {e}")
            return False, None
    def send_all_messages(self, job_exceptions: Dict, total_failed_jobs: int, total_failed_builds: int) -> bool:
        """Send summary message followed by individual job messages."""
        
        if not self.bot_token or not self.channel:
            print("❌ SLACK_BOT_TOKEN and SLACK_CHANNEL must be configured for Slack notifications.")
            print("💡 Set SLACK_BOT_TOKEN and SLACK_CHANNEL environment variables.")
            return False
        
        # Send summary header first
        print("📤 Sending Jenkins health summary...")
        summary_success, _ = self._send_summary_header(total_failed_jobs, total_failed_builds)
        
        if not summary_success:
            return False
        
        # Send each job as a separate message
        if job_exceptions:
            # Sort jobs by total failure count (descending)
            sorted_jobs = sorted(job_exceptions.items(), 
                               key=lambda x: sum(data['count'] for data in x[1].values()), 
                               reverse=True)
            
            for job_name, exceptions in sorted_jobs:
                print(f"📤 Sending details for job: {job_name}")
                self._send_job_summary(job_name, exceptions)
        
        return True
    
    def _send_summary_header(self, total_failed_jobs: int, total_failed_builds: int) -> Tuple[bool, Optional[str]]:
        """Send just the summary header with overall stats."""
        
        # Determine the header text
        time_unit = "Hour" if WINDOW_HOURS == 1 else "Hours"
        header_text = f"Jenkins Health Report Last {WINDOW_HOURS} {time_unit}"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header_text
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "plain_text",
                        "emoji": True,
                        "text": f"Failed Jobs: {total_failed_jobs}"
                    },
                    {
                        "type": "plain_text",
                        "emoji": True,
                        "text": f"Failed Builds: {total_failed_builds}"
                    }
                ]
            }
        ]
        
        # If no failures, add a success message
        if total_failed_builds == 0:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*All systems healthy!* No failed builds in the specified time window."
                }
            })
        else:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Individual job details will follow below..."
                }
            })

        payload = {
            "blocks": blocks,
            "text": header_text
        }

        return self._send_message(payload, "Summary")
    
    def _send_job_summary(self, job_name: str, exceptions: Dict) -> bool:
        """Send a clean summary message for a single job with exception counts and file attachment."""
        
        total_job_failures = sum(data['count'] for data in exceptions.values())
        
        # Format the job failure count with "+" if at limit
        if total_job_failures >= MAX_FAILURES_COUNT_PER_JOB:
            failure_display = f"{MAX_FAILURES_COUNT_PER_JOB}+ failures"
        else:
            failure_display = f"{total_job_failures} failures"
        
        # Create job title with link
        if JENKINS_URL:
            encoded_job_name = quote(job_name, safe='')
            job_link = f"<{JENKINS_URL}/job/{encoded_job_name}/|{job_name}>"
        else:
            job_link = job_name
        
        # Sort exceptions within job by count (descending)
        sorted_exceptions = sorted(exceptions.items(), 
                                 key=lambda x: x[1]['count'], 
                                 reverse=True)
        
        # Add each exception as a simple count line
        exception_lines = []
        for exception_type, data in sorted_exceptions:
            count = data['count']
            
            # Format the exception count with "+" if at limit
            if count >= MAX_FAILURES_COUNT_PER_JOB:
                count_display = f"x{MAX_FAILURES_COUNT_PER_JOB}+"
            else:
                count_display = f"x{count}"
            
            # Create simple summary for this exception type
            unique_count = len(data['unique_messages'])
            if unique_count == 1:
                summary_text = f"*{exception_type}* ({count_display})"
            else:
                summary_text = f"*{exception_type}* ({count_display}, {unique_count} unique)"
            
            exception_lines.append(summary_text)
        
        # Create the message text
        message_text = f"🔴 *{job_link}* ({failure_display})"
        if exception_lines:
            message_text += "\n" + "\n".join(exception_lines)
        
        # Send the message with file attachment
        return self._send_message_with_file(message_text, job_name, exceptions)

    def _send_message_with_file(self, message_text: str, job_name: str, exceptions: Dict) -> bool:
        """Send a message with text and attach a file with exception details using modern Slack API."""
        if not self.bot_token or not self.channel:
            print("❌ Cannot send message with file without SLACK_BOT_TOKEN and SLACK_CHANNEL")
            return False
        
        # Create a safe filename
        safe_job_name = "".join(c for c in job_name if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_job_name}_exceptions.txt"
        
        # Create file content
        file_content = self._create_snippet_content(job_name, exceptions)
        
        # Step 1: Get upload URL using files.getUploadURLExternal
        upload_url_endpoint = "https://slack.com/api/files.getUploadURLExternal"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        upload_url_payload = {
            "filename": filename,
            "length": str(len(file_content.encode('utf-8')))
        }
        
        try:
            # Get upload URL using form data instead of JSON
            upload_url_response = requests.post(upload_url_endpoint, headers=headers, data=upload_url_payload, timeout=30)
            upload_url_response.raise_for_status()
            
            upload_url_result = upload_url_response.json()
            
            if not upload_url_result.get("ok"):
                print(f"❌ Failed to get upload URL: {upload_url_result.get('error', 'Unknown error')}")
                return False
            
            upload_url = upload_url_result.get("upload_url")
            file_id = upload_url_result.get("file_id")
            
            if not upload_url or not file_id:
                print("❌ Missing upload_url or file_id in response")
                return False
            
            # Step 2: Upload file to the URL
            upload_response = requests.post(upload_url, files={'file': (filename, file_content, 'text/plain')}, timeout=30)
            upload_response.raise_for_status()
            
            # Step 3: Complete the upload using files.completeUploadExternal
            complete_upload_endpoint = "https://slack.com/api/files.completeUploadExternal"
            complete_headers = {
                "Authorization": f"Bearer {self.bot_token}",
                "Content-Type": "application/json"
            }
            
            complete_upload_payload = {
                "files": [
                    {
                        "id": file_id,
                        "title": f"Exception details for {job_name}"
                    }
                ],
                "channel_id": self.channel,
                "initial_comment": message_text
            }
            
            complete_response = requests.post(complete_upload_endpoint, headers=complete_headers, json=complete_upload_payload, timeout=30)
            complete_response.raise_for_status()
            
            complete_result = complete_response.json()
            
            if complete_result.get("ok"):
                print(f"✅ Sent message with attached file: {filename}")
                return True
            else:
                print(f"❌ Failed to complete file upload {filename}: {complete_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send message with file {filename}: {e}")
            return False
    
    def _create_snippet_content(self, job_name: str, exceptions: Dict) -> str:
        """Create the snippet file content for all exception types in a job."""
        lines = []
        
        # Sort exceptions by count (descending)
        sorted_exceptions = sorted(exceptions.items(), 
                                 key=lambda x: x[1]['count'], 
                                 reverse=True)
        
        for i, (exception_type, data) in enumerate(sorted_exceptions):
            # Add section header for each exception type
            lines.append("=" * 80)
            lines.append(f"{exception_type} | {data['count']} Failures")
            lines.append("=" * 80)
            lines.append("")
            
            # Add each unique exception message with build URLs
            for j, (exception_message, build_urls) in enumerate(data['unique_messages'].items()):
                lines.append(exception_message)
                lines.append("")
                # Provide up to 3 build URLs per unique message
                for url in build_urls[:3]:
                    lines.append(f"  - {url}")
                if len(build_urls) > 3:
                    lines.append(f"  ... and {len(build_urls) - 3} more")
                lines.append("-" * 80)
            
            # Add extra spacing between exception types (except for the last one)
            if i < len(sorted_exceptions) - 1:
                lines.append("")
        
        return "\n".join(lines)

