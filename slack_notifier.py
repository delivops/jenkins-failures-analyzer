"""
Slack notification module for sending Jenkins failure analysis results with threading support.
"""

import datetime as _dt
import time
import uuid
from typing import Dict, Optional, Tuple

import requests

from config import SLACK_BOT_TOKEN, SLACK_CHANNEL, WINDOW_HOURS, MAX_FAILURES_COUNT_PER_JOB, JENKINS_URL


class SlackNotifier:
    """Handles Slack notifications for Jenkins failure analysis using bot token and threading."""
    
    def __init__(self, bot_token: str = None, channel: str = None):
        self.bot_token = bot_token or SLACK_BOT_TOKEN
        self.channel = channel or SLACK_CHANNEL
        self.report_id = None  # Unique identifier for each report session
    
    def _escape_slack_text(self, text: str) -> str:
        """Escape special characters for Slack formatting."""
        # Escape &, <, > characters that have special meaning in Slack
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text
    
    def _truncate_for_slack(self, text: str, max_chars: int = 2900) -> str:
        """Truncate text to fit Slack's character limits for text blocks."""
        if len(text) <= max_chars:
            return text
        
        # Try to truncate at a reasonable point (newline or space)
        truncated = text[:max_chars-10]  # Leave room for "..." indicator
        
        # Find the last newline or space to break cleanly
        last_newline = truncated.rfind('\n')
        last_space = truncated.rfind(' ')
        
        if last_newline > max_chars - 200:  # If newline is reasonably close to limit
            truncated = truncated[:last_newline]
        elif last_space > max_chars - 200:  # If space is reasonably close to limit
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
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
    def send_summary(self, total_failed_jobs: int, total_failed_builds: int, job_exceptions: Dict) -> Tuple[bool, Optional[str]]:
        """Send a summary Slack message using Block Kit format."""
        
        if not self.bot_token or not self.channel:
            print("❌ SLACK_BOT_TOKEN and SLACK_CHANNEL must be configured.")
            return False, None
        
        # Generate unique report ID
        self.report_id = str(uuid.uuid4())[:8]
        
        # Determine the header text
        time_unit = "Hour" if WINDOW_HOURS == 1 else "Hours"
        header_text = f"Jenkins Health Report Last {WINDOW_HOURS} {time_unit}"
        
        # Start building blocks
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
        
        # Add job breakdown if there are failures
        if total_failed_builds > 0 and job_exceptions:
            blocks.append({"type": "divider"})
            
            # Sort jobs by total failure count (descending)
            sorted_jobs = sorted(job_exceptions.items(), 
                               key=lambda x: sum(data['count'] for data in x[1].values()), 
                               reverse=True)
            
            for job_name, exceptions in sorted_jobs:
                total_job_failures = sum(data['count'] for data in exceptions.values())
                
                # Format the job failure count with "+" if at limit
                if total_job_failures >= MAX_FAILURES_COUNT_PER_JOB:
                    failure_display = f"{MAX_FAILURES_COUNT_PER_JOB}+ failures"
                else:
                    failure_display = f"{total_job_failures} failures"
                
                # Create job title block with link
                if JENKINS_URL:
                    job_link = f"<{JENKINS_URL}/job/{job_name}/|{job_name}>"
                else:
                    job_link = job_name
                
                job_title_block = {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{job_link}* ({failure_display})"
                    }
                }
                blocks.append(job_title_block)
                
                # Sort exceptions within job by count (descending)
                sorted_exceptions = sorted(exceptions.items(), 
                                         key=lambda x: x[1]['count'], 
                                         reverse=True)
                
                # Create separate block for each exception
                for exception_type, data in sorted_exceptions:
                    count = data['count']
                    
                    # Format the exception count with "+" if at limit
                    if count >= MAX_FAILURES_COUNT_PER_JOB:
                        count_display = f"x{MAX_FAILURES_COUNT_PER_JOB}+"
                    else:
                        count_display = f"x{count}"
                    
                    # Truncate and escape exception preview
                    exception_preview = self._escape_slack_text(data['latest_line'])
                    exception_preview = self._truncate_for_slack(exception_preview, 2500)  # Leave room for other text
                    
                    # Build exception detail text
                    exception_detail = f"*{exception_type}* ({count_display})\n```\n{exception_preview}\n```"
                    
                    # Add build URLs if available
                    if data.get('build_urls'):
                        build_links = []
                        for url in data['build_urls'][:3]:  # Show max 3 URLs
                            # Extract build number from URL for display
                            build_num = url.split('/')[-1] if url.split('/')[-1] else url.split('/')[-2]
                            build_links.append(f"<{url}|{build_num}>")
                        
                        links_text = f"\nAppeared in {', '.join(build_links)}"
                        
                        # Add "and X more" if there are additional builds
                        if len(data['build_urls']) > 3:
                            links_text += f" and {len(data['build_urls']) - 3} more"
                        
                        # Check if adding links would exceed limit
                        if len(exception_detail + links_text) <= 2900:
                            exception_detail += links_text
                    
                    # Create exception block
                    exception_block = {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": exception_detail
                        }
                    }
                    blocks.append(exception_block)
                
                # Add divider after each job (except the last one)
                if job_name != sorted_jobs[-1][0]:
                    blocks.append({"type": "divider"})
        
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

        payload = {
            "blocks": blocks,
            "text": header_text  # Fallback text for notifications
        }

        return self._send_message(payload, "Summary")
    def send_job_detail(self, job_name: str, exceptions: Dict, thread_ts: str = None) -> bool:
        """Send a detailed Slack message for a specific job's failures using Block Kit."""
        
        if not self.bot_token or not self.channel:
            print("❌ SLACK_BOT_TOKEN and SLACK_CHANNEL must be configured.")
            return False
        
        # Calculate total failures for this job
        total_failures = sum(data['count'] for data in exceptions.values())
        
        # Format total failures with "+" if at limit
        if total_failures >= MAX_FAILURES_COUNT_PER_JOB:
            failure_display = f"{MAX_FAILURES_COUNT_PER_JOB}+ failures"
        else:
            failure_display = f"{total_failures} failures"
        
        # Start building blocks for job detail
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Job Details: {job_name}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "plain_text",
                        "text": failure_display,
                        "emoji": True
                    }
                ]
            },
            {"type": "divider"}
        ]

        # Add exception details
        for exception_type, data in sorted(exceptions.items(), key=lambda x: x[1]['count'], reverse=True):
            # Escape and truncate exception lines
            exception_preview = self._escape_slack_text(data['latest_line'])
            exception_preview = self._truncate_for_slack(exception_preview, 2500)  # Leave room for other text
            
            # Format count with "+" if at limit
            count = data['count']
            if count >= MAX_FAILURES_COUNT_PER_JOB:
                count_display = f"x{MAX_FAILURES_COUNT_PER_JOB}+"
            else:
                count_display = f"x{count}"
            
            # Build exception section text
            section_text = f"*{exception_type}* ({count_display})\n```\n{exception_preview}\n```"
            
            # Add build URLs if available
            if data.get('build_urls'):
                build_links_text = "\n*Build URLs:*"
                for url in data['build_urls'][:3]:  # Show max 3 URLs
                    build_links_text += f"\n• <{url}|Build Link>"
                if len(data['build_urls']) > 3:
                    build_links_text += f"\n• ... and {len(data['build_urls']) - 3} more"
                
                # Check if adding links would exceed limit
                if len(section_text + build_links_text) <= 2900:
                    section_text += build_links_text
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": section_text
                }
            })
            
            # Add divider between exceptions
            blocks.append({"type": "divider"})
        
        # Remove the last divider
        if blocks and blocks[-1]["type"] == "divider":
            blocks.pop()

        payload = {
            "blocks": blocks,
            "text": f"Job Failure Details: {job_name} ({failure_display})"  # Fallback text
        }

        success, _ = self._send_message(payload, f"Job: {job_name}", thread_ts)
        return success
    
    def send_all_messages(self, job_exceptions: Dict, total_failed_jobs: int, total_failed_builds: int) -> bool:
        """Send summary message followed by individual job messages."""
        
        if not self.bot_token or not self.channel:
            print("❌ SLACK_BOT_TOKEN and SLACK_CHANNEL must be configured for Slack notifications.")
            print("💡 Set SLACK_BOT_TOKEN and SLACK_CHANNEL environment variables.")
            return False
        
        # Send summary header first
        print("📤 Sending Jenkins health summary...")
        summary_success, thread_ts = self.send_summary_header(total_failed_jobs, total_failed_builds)
        
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
                self.send_job_summary(job_name, exceptions, thread_ts)
        
        return True
    
    def send_summary_header(self, total_failed_jobs: int, total_failed_builds: int) -> Tuple[bool, Optional[str]]:
        """Send just the summary header with overall stats."""
        
        # Generate unique report ID
        self.report_id = str(uuid.uuid4())[:8]
        
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
    
    def send_job_summary(self, job_name: str, exceptions: Dict, thread_ts: str = None) -> bool:
        """Send a summary message for a single job with all its exceptions."""
        
        total_job_failures = sum(data['count'] for data in exceptions.values())
        
        # Format the job failure count with "+" if at limit
        if total_job_failures >= MAX_FAILURES_COUNT_PER_JOB:
            failure_display = f"{MAX_FAILURES_COUNT_PER_JOB}+ failures"
        else:
            failure_display = f"{total_job_failures} failures"
        
        # Create job title with link
        if JENKINS_URL:
            job_link = f"<{JENKINS_URL}/job/{job_name}/|{job_name}>"
        else:
            job_link = job_name
        
        blocks = [
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔴 *{job_link}* ({failure_display})"
                }
            }
        ]
        
        # Sort exceptions within job by count (descending)
        sorted_exceptions = sorted(exceptions.items(), 
                                 key=lambda x: x[1]['count'], 
                                 reverse=True)
        
        # Add each exception as a separate block
        for exception_type, data in sorted_exceptions:
            count = data['count']
            
            # Format the exception count with "+" if at limit
            if count >= MAX_FAILURES_COUNT_PER_JOB:
                count_display = f"x{MAX_FAILURES_COUNT_PER_JOB}+"
            else:
                count_display = f"x{count}"
            
            # Truncate and escape exception preview
            exception_preview = self._escape_slack_text(data['latest_line'])
            exception_preview = self._truncate_for_slack(exception_preview, 2000)
            
            # Build exception detail text
            exception_detail = f"📊 *{exception_type}* ({count_display})\n```{exception_preview}```"
            
            # Add build URLs if available
            if data.get('build_urls'):
                build_links = []
                for url in data['build_urls'][:3]:  # Show max 3 URLs
                    build_links.append(f"<{url}|🔗>")
                
                links_text = f"\nBuild URLs: {', '.join(build_links)}"
                
                # Add "and X more" if there are additional builds
                if len(data['build_urls']) > 3:
                    links_text += f" and {len(data['build_urls']) - 3} more"
                
                # Check if adding links would exceed limit
                if len(exception_detail + links_text) <= 2900:
                    exception_detail += links_text
            
            # Create exception block
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": exception_detail
                }
            })
        
        payload = {
            "blocks": blocks,
            "text": f"Job: {job_name} ({failure_display})"
        }

        success, _ = self._send_message(payload, f"Job: {job_name}", thread_ts)
        return success

