#!/usr/bin/env python3
"""
Configuration settings for Jenkins failure analysis system.
"""

import os

# Jenkins Configuration
JENKINS_URL = os.getenv('JENKINS_URL')
JENKINS_USER = os.getenv('JENKINS_USER')
JENKINS_TOKEN = os.getenv('JENKINS_TOKEN')

# Slack Configuration
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.getenv('SLACK_CHANNEL', '#jenkins-health')  # Default channel

# Analysis Configuration
WINDOW_HOURS = int(os.getenv('WINDOW_HOURS', 1))
MAX_FAILURES_COUNT_PER_JOB = int(os.getenv('MAX_FAILURES_COUNT_PER_JOB', 100))

# Exception filtering - comma-separated list of exception types to ignore
IGNORE_EXCEPTIONS_RAW = os.getenv('IGNORE_EXCEPTIONS', '')
IGNORE_EXCEPTIONS = [exc.strip() for exc in IGNORE_EXCEPTIONS_RAW.split(',') if exc.strip()]
