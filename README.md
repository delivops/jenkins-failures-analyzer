[![DelivOps banner](https://raw.githubusercontent.com/delivops/.github/main/images/banner.png?raw=true)](https://delivops.com)

# Jenkins Failure Analysis System

Monitors Jenkins build failures, analyzes ### Slack### Slack
```
🔴 reddit_search_posts (3 failures)
• java.lang.IllegalArgumentException (x1)
• ERROR (x1)
• AttributeError (x1)
Total failures: 3 | Exception types: 3 | Unique messages: 3

[Attached: reddit_search_posts_exceptions.txt]
```dit_search_posts (3 failures)
*java.lang.IllegalArgumentException* (x1)
*ERROR* (x1)
*AttributeError* (x1)

� Complete exception details for job reddit_search_posts
reddit_search_posts_exceptions.txt
```sends detailed Slack notifications with zero disk usage.

## � Quick Start

```bash
# Set environment variables
export JENKINS_URL="https://your-jenkins.com"
export JENKINS_USER="your-username"  
export JENKINS_TOKEN="your-api-token"
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_CHANNEL="#jenkins-health"

# Run with Docker (recommended)
docker-compose up --build

# Or run locally
pip install -r requirements.txt
python main.py
```

## ✨ Features

- **🔥 In-Memory Processing** - Zero disk usage, processes logs entirely in memory
- **🎯 Smart Analysis** - Detects Python exceptions and extracts relevant context
- **💬 Slack Integration** - Summary messages with threaded job details  
- **🐳 Docker Ready** - Complete containerization support
- **⚙️ Configurable** - Environment-based configuration

## ⚙️ Configuration

### Required Environment Variables

```bash
export JENKINS_URL="https://your-jenkins.com"
export JENKINS_USER="your-username"  
export JENKINS_TOKEN="your-api-token"
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_CHANNEL="#jenkins-health"
```

### Optional Settings

```bash
export WINDOW_HOURS="24"                    # Analysis time window (default: 24 hours)
export MAX_FAILURES_COUNT_PER_JOB="100"     # Max failed builds per job (default: 100)
export IGNORE_EXCEPTIONS="Exception,Warning" # Comma-separated exception types to ignore
```

### Setup Tokens

**Jenkins API Token:**
1. Jenkins → User Profile → Configure → API Token → Add new Token

**Slack Bot Token:**
1. [Slack App Directory](https://api.slack.com/apps) → Create/select app
2. OAuth & Permissions → Add scopes: `chat:write`, `chat:write.public`, `files:write`, `files:read`
3. Install app → Copy "Bot User OAuth Token" (starts with `xoxb-`)

## 📊 Example Output

### Console
```
🚀 Starting Jenkins Failure Analysis System
🔍 Processing failed build logs in memory...
Found 130 jobs
Processing logs for job: my_job (5 failed builds)
  Processed: build_400828 -> ValueError
  
Summary: 15 jobs with failures, 42 total failed builds
🔍 Analyzing for exceptions...

🔴 my_job: ValueError (4 occurrences)
   🔗 https://jenkins.mydomain.com/job/my_job/400/
```

### Slack
**Snippet File Mode (MAX_SNIPPETS_PER_EXCEPTION=0):**
```
🔴 search_user_feed_instagram (10+ failures)
📊 Exception (x9, 7 unique)
📊 instagram.vs_lobster_instagram.InstagramAPIException (x1)

Attached Files:
📎 search_user_feed_instagram_Exception.txt
� search_user_feed_instagram_instagram.vs_lobster_instagram.InstagramAPIException.txt
```

**Traditional Mode (MAX_SNIPPETS_PER_EXCEPTION > 0):**
```
🔴 Find Fake Tweets - Priority (12 failures)
📊 Exception (x10, 5 unique)
• Omar's API encountered an issue. Contact Omar... (🔗, +4)
• API response problem with search continuation... (🔗)
... and 3 more unique messages
```

**Key Features:**
- Clean single message per job with exception counts and summary stats
- File attachment included in the same message (not separate or threaded)
- Clear visual separators between exception types and individual messages in files
- Up to 3 build URLs provided per unique exception message
- Grouped exceptions with counts and unique message indicators

## 🐛 Troubleshooting

**Jenkins Connection Issues:** Verify `JENKINS_URL`, `JENKINS_USER`, `JENKINS_TOKEN`
**Slack Failures:** Check `SLACK_BOT_TOKEN`, `SLACK_CHANNEL`, and bot permissions
**No Failures Found:** Increase `WINDOW_HOURS` or check actual failures exist
**Memory Issues:** Reduce `MAX_FAILURES_COUNT_PER_JOB` or increase available RAM
