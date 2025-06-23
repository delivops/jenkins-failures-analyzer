"""
Slack notification module for sending Jenkins failure analysis results.
"""

import datetime as _dt
import json
import time
from collections import defaultdict
from typing import Dict

import requests

from config import SLACK_WEBHOOK_URL


class SlackNotifier:
    """Handles Slack notifications for Jenkins failure analysis."""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or SLACK_WEBHOOK_URL
    
    def _escape_slack_text(self, text: str) -> str:
        """Escape special characters for Slack formatting."""
        # Escape &, <, > characters that have special meaning in Slack
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text
    
    def send_summary(self, total_failed_jobs: int, total_failed_builds: int, exception_summary: Dict) -> bool:
        """Send a summary Slack message with overall health status."""
        
        if not self.webhook_url:
            print("❌ SLACK_WEBHOOK_URL not configured. Skipping Slack notification.")
            return False
        
        # Determine overall health status
        if total_failed_builds == 0:
            color = "good"
            status_emoji = "✅"
        elif total_failed_builds <= 5:
            color = "warning" 
            status_emoji = "⚠️"
        else:
            color = "danger"
            status_emoji = "🚨"

        timestamp = int(_dt.datetime.now(_dt.UTC).timestamp())

        payload = {
            "text": f"{status_emoji} Jenkins Health Report - {_dt.datetime.now(_dt.UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Failed Jobs",
                            "value": str(total_failed_jobs),
                            "short": True
                        },
                        {
                            "title": "Failed Builds", 
                            "value": str(total_failed_builds),
                            "short": True
                        }
                    ],
                    "footer": "Jenkins Health Monitor",
                    "ts": timestamp
                }
            ]
        }
        
        # Add exception summary if there are failures
        if total_failed_builds > 0 and exception_summary:
            summary_text = ""
            for exc_type, count in sorted(exception_summary.items(), key=lambda x: x[1], reverse=True):
                emoji = "🔥" if count >= 5 else "⚠️" if count >= 3 else "🟡"
                escaped_exc_type = self._escape_slack_text(exc_type)
                summary_text += f"{emoji} {escaped_exc_type}: {count} occurrences\n"
            
            payload["attachments"][0]["fields"].append({
                "title": "Exception Summary",
                "value": summary_text,
                "short": False
            })

        return self._send_message(payload, "Summary")
    
    def send_job_detail(self, job_name: str, exceptions: Dict) -> bool:
        """Send a detailed Slack message for a specific job's failures."""
        
        if not self.webhook_url:
            print("❌ SLACK_WEBHOOK_URL not configured. Skipping Slack notification.")
            return False
        
        # Calculate total failures for this job
        total_failures = sum(data['count'] for data in exceptions.values())
        
        # Determine color based on severity
        if total_failures >= 10:
            color = "danger"
            emoji = "🔥"
        elif total_failures >= 5:
            color = "warning"
            emoji = "⚠️"
        else:
            color = "#ffcc00"
            emoji = "🟡"

        # Build fields for exception details
        fields = []
        for exception_type, data in sorted(exceptions.items(), key=lambda x: x[1]['count'], reverse=True):
            # Escape and truncate exception lines
            exception_preview = self._escape_slack_text(data['latest_line'])
            
            exception_detail = f"```\n{exception_preview}\n```"
            
            # Add build URLs
            if data.get('build_urls'):
                exception_detail += f"\n🔗 **Build URLs:**"
                for url in data['build_urls'][:3]:  # Show max 3 URLs
                    exception_detail += f"\n• {url}"
                if len(data['build_urls']) > 3:
                    exception_detail += f"\n• ... and {len(data['build_urls']) - 3} more"
            
            fields.append({
                "title": f"{self._escape_slack_text(exception_type)} ({data['count']} occurrences)",
                "value": exception_detail,
                "short": False
            })

        payload = {
            "text": f"{emoji} Job Failure: {self._escape_slack_text(job_name)} ({total_failures} total failures)",
            "attachments": [
                {
                    "color": color,
                    "fields": fields,
                    "footer": f"Jenkins Health Monitor - {self._escape_slack_text(job_name)}",
                    "ts": int(_dt.datetime.now(_dt.UTC).timestamp())
                }
            ]
        }

        return self._send_message(payload, f"Job: {job_name}")
    
    def _send_message(self, payload: Dict, message_type: str) -> bool:
        """Send a message to Slack webhook."""
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            print(f"✅ {message_type} Slack message sent successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to send {message_type} Slack message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response status: {e.response.status_code}")
                print(f"   Response text: {e.response.text}")
            return False
    
    def send_all_messages(self, job_exceptions: Dict, total_failed_jobs: int, total_failed_builds: int) -> bool:
        """Send multiple Slack messages - summary plus details per job."""
        
        if not self.webhook_url:
            print("⚠️  SLACK_WEBHOOK_URL not configured. Skipping all Slack notifications.")
            print("💡 To enable Slack notifications, set the SLACK_WEBHOOK_URL environment variable.")
            return False
        
        if total_failed_builds == 0:
            # Send success message
            return self.send_summary(total_failed_jobs, total_failed_builds, {})
        
        # Create exception summary for the overview
        exception_summary = defaultdict(int)
        for job_name, exceptions in job_exceptions.items():
            for exception_type, data in exceptions.items():
                exception_summary[exception_type] += data["count"]
        
        # Send summary message first
        success = self.send_summary(total_failed_jobs, total_failed_builds, exception_summary)
        
        # Send detailed messages for each job
        for job_name, exceptions in sorted(job_exceptions.items()):
            success &= self.send_job_detail(job_name, exceptions)
            
            # Small delay between messages to avoid rate limiting
            time.sleep(1)
        
        return success
