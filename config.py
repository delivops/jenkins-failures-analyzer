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
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')

# Analysis Configuration
DEFAULT_WINDOW_HOURS = 24
DEFAULT_COUNT = 100
SLICE_SIZE = 100_000  # how many recent builds to fetch per job
