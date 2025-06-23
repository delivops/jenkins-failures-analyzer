# Jenkins Failure Analysis System

A comprehensive system for monitoring Jenkins build failures, analyzing logs, and sending detailed Slack notifications. **All processing is done in memory with zero disk usage.**

## 🏗️ Architecture

The system is organized into focused modules:

- **`main.py`** - Main entry point with in-memory processing
- **`streaming_log_processor.py`** - In-memory log processing engine
- **`config.py`** - Configuration settings and environment variables
- **`jenkins_client.py`** - Jenkins API client for fetching jobs and logs
- **`log_analyzer.py`** - Analyzes logs for exceptions and extracts context
- **`slack_notifier.py`** - Sends formatted Slack notifications

## 🚀 Features

### In-Memory Processing
- **🔥 Zero Disk Usage** - Processes logs entirely in memory
- **Memory Efficiency** - Fetch and analyze logs one by one
- **Fast Processing** - Direct memory processing without I/O
- **Same Quality** - Full exception detection and context extraction

### Log Analysis
- **Smart Exception Detection** - Uses regex patterns to find Python exceptions
- **Context Extraction** - Captures relevant log context around failures  
- **Timestamp-based Context** - Extracts context from latest timestamp to failure
- **Multiple Error Types** - Detects exceptions, errors, and build failures

### Slack Notifications
- **Summary Message** - Overall health status with exception counts
- **Detailed Messages** - Separate message per exception type
- **Code Formatting** - Context displayed as properly escaped code blocks
- **Severity Indicators** - Color-coded and emoji-based severity levels
- **Rate Limiting** - Controlled message sending to avoid Slack limits

### Operational
- **Clean Slate** - Removes old logs before each run
- **Organized Storage** - Logs stored in job-specific directories
- **Error Handling** - Graceful handling of network and parsing errors
- **Console Output** - Detailed console logging for debugging

## 📦 Installation

```bash
pip install requests
```

## ⚙️ Configuration

Set environment variables:

```bash
export JENKINS_URL="https://your-jenkins.com"
export JENKINS_USER="your-username"  
export JENKINS_TOKEN="your-api-token"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

## 🎯 Usage

Process Jenkins build failures in memory:

```bash
python main.py
```

**All processing is done in memory with zero disk usage - no setup required!**

## 📊 Example Output

### Console Output (Streaming Mode)
```
🚀 Starting Jenkins Failure Analysis System (Streaming Mode)
============================================================

� Processing failed build logs in memory...
Fetching jobs…
Found 130 jobs
Processing logs for job: search_posts_instagram (5 failed builds)
  Processed: build_400828_20250623_123533 -> tenacity.RetryError
  Processed: build_400829_20250623_123634 -> tenacity.RetryError
  ...

Summary:
  Jobs with failures: 15
  Total failed builds processed: 42
  Processed entirely in memory (no disk usage)

🔍 Analyzing processed logs for exceptions...

=== JENKINS FAILURE EXCEPTIONS SUMMARY ===

🔴 search_posts_instagram:
   📊 tenacity.RetryError (4 occurrences)
      Exception: tenacity.RetryError: RetryError[<Future at 0x7fbc2b864220 state=finished raised InstagramAPIException>]
      Build URLs:
         🔗 https://jenkins.internal.vinesight.com/job/search_posts_instagram/400828/
         🔗 https://jenkins.internal.vinesight.com/job/search_posts_instagram/400829/
```

### Slack Notifications
- **Summary**: Overall health with failed jobs/builds count and exception summary
- **Details**: Per-exception breakdown with job names, counts, and code-formatted context

## 🔧 Customization

### Analysis Window
Modify `DEFAULT_WINDOW_HOURS` in `config.py` to change the time window for analysis.

### Build Limit
Modify `DEFAULT_COUNT` in `config.py` to change max builds per job to analyze.

### Context Length
Modify `max_lines` parameter in `SlackNotifier._format_context_as_code()` to adjust context length.

## 🎨 Key Features

1. **🔥 In-Memory Processing** - Process logs entirely in memory (zero disk usage)
2. **Memory Efficiency** - Fetch and analyze logs one by one  
3. **Production Ready** - Optimized for production use
4. **Modular Design** - Clear separation of concerns across focused modules
5. **Code Formatting** - Slack context properly formatted as escaped code blocks
6. **Enhanced Readability** - Clean imports and focused classes
7. **Proper Escaping** - All Slack text properly escaped to avoid parsing issues
8. **Documentation** - Comprehensive docstrings and README

## 🐛 Error Handling

- Network timeouts and HTTP errors are handled gracefully
- Missing environment variables are handled with defaults
- Log parsing errors are captured and reported
- Slack webhook failures include detailed error information

## 🎉 Benefits

- **💽 Zero Disk Usage** - No log files created or stored
- **🚀 Faster Processing** - Direct in-memory analysis  
- **🧹 No Cleanup** - Nothing to clean up between runs
- **📉 Lower Resource Usage** - Reduced I/O operations
- **🔒 Same Quality** - Identical analysis results
