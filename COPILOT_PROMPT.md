# VS Code Copilot / Claude Code Prompt

Paste this prompt into VS Code Copilot Chat or Claude Code to discuss this project:

---

## Google Form Automation Script - Project Overview

I have a Python project that automates Google Form submissions using HTTP requests (no Selenium/browser automation).

### Project Files
- **gform_bot.py** - Main script with full automation logic
- **config.json** - Form configuration (URL, entry IDs, field types)
- **requirements.txt** - Python dependencies (requests, faker)
- **setup_config.py** - Interactive configuration helper
- **log_analyzer.py** - Log analysis and reporting tool
- **README.md** - Full documentation
- **QUICKSTART.md** - 5-minute setup guide

### Stack
- Python 3.10+
- requests library for HTTP
- faker for realistic random data
- JSON-based configuration
- CLI with argparse

### Key Features Implemented
✓ Read config from JSON file
✓ Generate realistic answers using Faker
✓ Submit via HTTP POST to Google Forms
✓ Random 2-5 second delays between submissions
✓ Logging to console and log.txt
✓ CLI arguments: --count, --config
✓ Retry logic (max 3 attempts per submission)
✓ Support for multiple field types

### Usage
```bash
# Single submission test
python gform_bot.py --count 1

# Full automation
python gform_bot.py --count 100

# Custom config
python gform_bot.py --count 50 --config custom.json

# Interactive setup
python setup_config.py

# Analyze results
python log_analyzer.py report
```

### Field Types Supported
- choice (multiple choice / dropdown)
- email (generates realistic emails)
- name (generates random names)
- phone (generates phone numbers)
- text (short text)
- paragraph (multi-sentence text)
- number (random integers)
- date (random dates)
- time (random times)

### Configuration Format (config.json)
```json
{
  "form_url": "https://docs.google.com/forms/d/FORM_ID/viewform",
  "fields": [
    {
      "entry_id": "entry.1234567890",
      "type": "choice",
      "options": ["A", "B", "C"]
    },
    {
      "entry_id": "entry.1234567891",
      "type": "email"
    }
  ]
}
```

### What I Need Help With
[Specify what you need - examples:]
- Help finding entry IDs in my specific form
- Modify the data generation logic
- Add new field types
- Improve error handling
- Scale to handle thousands of submissions
- Add proxy support
- Add authentication support
- Implement better rate limiting
- Add progress bar
- Create a GUI version

---

### For Further Reference
Check the following files for detailed information:
- **README.md** - Complete documentation and troubleshooting
- **QUICKSTART.md** - Step-by-step setup guide
- **gform_bot.py** - Source code with comments
