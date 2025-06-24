#!/usr/bin/env python3
"""
Jenkins Failure Analysis System
==============================

A comprehensive system that:
1. Processes failed Jenkins build logs in memory
2. Analyzes them for exceptions and errors  
3. Sends formatted Slack notifications with detailed failure analysis

Usage:
    python main.py

Environment Variables:
    JENKINS_URL        - Jenkins base URL (required)
    JENKINS_USER       - Jenkins API user (required)
    JENKINS_TOKEN      - Jenkins API token (required)
    SLACK_BOT_TOKEN    - Slack bot token for notifications (required)
    SLACK_CHANNEL      - Slack channel for notifications (required)

The system will:
- Process failure logs from Jenkins API directly in memory
- Analyze logs for Python exceptions and context
- Send multiple Slack messages with beautiful formatting
- Provide console output with detailed failure analysis
- Use minimal disk space (no log files saved)
"""

from config import JENKINS_URL, JENKINS_USER, JENKINS_TOKEN
from jenkins_client import JenkinsClient
from streaming_log_processor import StreamingLogProcessor
from log_analyzer import LogAnalyzer
from slack_notifier import SlackNotifier


def main():
    """Main entry point for Jenkins failure analysis using streaming processing."""
    
    print("🚀 Starting Jenkins Failure Analysis System")
    print("=" * 50)
    
    # Initialize components
    jenkins_client = JenkinsClient(JENKINS_URL, JENKINS_USER, JENKINS_TOKEN)
    processor = StreamingLogProcessor(jenkins_client)
    analyzer = LogAnalyzer()
    notifier = SlackNotifier()
    
    # Process failed builds directly in memory
    print("\n🔍 Processing failed build logs in memory...")
    job_exceptions, total_failed_jobs, total_failed_builds = processor.process_failed_builds()
    
    # Analyze and send notifications if we have failures
    if total_failed_builds > 0:
        # Print console summary
        analyzer.print_console_summary(job_exceptions)
        
        # Send Slack notifications
        print(f"\n📤 Sending Slack notifications...")
        notifier.send_all_messages(job_exceptions, total_failed_jobs, total_failed_builds)
    else:
        print("\n✅ No failed builds to analyze.")
        # Send success message to Slack
        print(f"\n📤 Sending success notification to Slack...")
        notifier.send_all_messages({}, 0, 0)
    
    print("\n🎉 Jenkins failure analysis completed!")


if __name__ == '__main__':
    main()
