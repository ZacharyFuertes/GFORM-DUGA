# Getting Started - Google Form Automation Bot

Welcome! This guide walks you through setting up and running the Google Form automation bot.

## System Requirements

- Windows, macOS, or Linux
- Python 3.10 or higher
- Internet connection (for HTTP submissions)
- Your Google Form link and field entry IDs

## Installation (One-Time Setup)

### Option 1: Using Batch File (Windows)
```bash
# Open PowerShell or Command Prompt in the project directory
run.bat install
```

### Option 2: Manual Setup
```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Configuration

### Automatic Configuration
```bash
# Interactive setup wizard
python setup_config.py
```

Or with batch file:
```bash
run.bat setup
```

### Manual Configuration

1. Open `config.json`
2. Update `form_url` with your Google Form link
3. Add entry IDs and field types for each form field

**Finding Your Form Details:**

1. Open your Google Form
2. Press F12 to open Developer Tools
3. Right-click each form field and select "Inspect"
4. Find the `name="entry.XXXXXXXX"` attribute
5. Copy the entry ID

Example:
```json
{
  "form_url": "https://docs.google.com/forms/d/1abc2def3ghi4jkl5mno/viewform",
  "fields": [
    {
      "entry_id": "entry.123456789",
      "type": "choice",
      "options": ["Yes", "No"]
    },
    {
      "entry_id": "entry.987654321",
      "type": "email"
    }
  ]
}
```

## Running Submissions

### Single Test Submission
```bash
python gform_bot.py --count 1
```

Or with batch file:
```bash
run.bat test
```

### Full Automation
```bash
# Submit 100 responses
python gform_bot.py --count 100
```

Or with batch file:
```bash
run.bat run 100
```

### Custom Configuration
```bash
python gform_bot.py --count 50 --config myform.json
```

## Monitoring Results

### View Report
```bash
python log_analyzer.py report
```

Or:
```bash
run.bat report
```

### View Recent Logs
```bash
python log_analyzer.py tail 20
```

Or:
```bash
run.bat log
```

### Raw Log File
Open `log.txt` in any text editor

## Available Field Types

| Type | Description | Example |
|------|-------------|---------|
| `choice` | Multiple choice / dropdown | `["Option A", "Option B"]` |
| `email` | Email address | Auto-generated realistic email |
| `name` | Full name | Auto-generated name |
| `phone` | Phone number | Auto-generated phone |
| `text` | Short text | Auto-generated sentence |
| `paragraph` | Long text (5 sentences) | Auto-generated paragraph |
| `number` | Integer 1-1000 | Random number |
| `date` | Random date | YYYY-MM-DD format |
| `time` | Random time | HH:MM:SS format |

## Command Reference

```bash
# Help
python gform_bot.py --help

# Configuration
python setup_config.py

# Single submission (test)
python gform_bot.py --count 1

# Multiple submissions
python gform_bot.py --count 100

# Custom config file
python gform_bot.py --count 50 --config custom_config.json

# Log analysis
python log_analyzer.py report
python log_analyzer.py tail 10
```

## Using Batch File (Windows)

```bash
run.bat install           # Install dependencies
run.bat setup             # Interactive setup
run.bat test              # Single test submission
run.bat run 100           # Submit 100 responses
run.bat report            # Show submission report
run.bat log               # Show recent logs
run.bat help              # Show help
```

## Example Workflow

### First Time Using

```bash
# 1. Install dependencies
run.bat install

# 2. Interactive setup
run.bat setup

# 3. Test with one submission
run.bat test

# 4. Check logs
run.bat log

# 5. If test succeeded, run full automation
run.bat run 100

# 6. Monitor progress
run.bat report
```

### Command Line Workflow

```bash
# 1. Setup virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure form
python setup_config.py

# 4. Test
python gform_bot.py --count 1

# 5. Run
python gform_bot.py --count 100

# 6. Analyze
python log_analyzer.py report
```

## Troubleshooting

### Python not found
- Install Python from https://www.python.org/downloads/
- Make sure to check "Add Python to PATH"

### Module not found errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Config file not found
```bash
# Use setup wizard
python setup_config.py

# Or manually create config.json
```

### Invalid form URL
Format should be: `https://docs.google.com/forms/d/FORM_ID/viewform`

### Submissions fail
1. Check `log.txt` for specific errors
2. Verify all entry IDs are correct
3. Ensure form allows responses
4. Form might have CAPTCHA or quota restrictions

### Submissions succeed but don't appear
- Form might have validation rules
- Check form settings for response acceptance
- Some forms require authentication
- Form might have quota limits

## File Descriptions

| File | Purpose |
|------|---------|
| `gform_bot.py` | Main automation script |
| `config.json` | Form configuration |
| `setup_config.py` | Interactive configuration helper |
| `log_analyzer.py` | Log analysis tool |
| `requirements.txt` | Python dependencies |
| `log.txt` | Submission results log |
| `run.bat` | Windows command shortcuts |
| `README.md` | Full documentation |
| `QUICKSTART.md` | Quick reference guide |
| `GETTING_STARTED.md` | This file |

## Important Notes

✓ **Privacy**: Only use on forms you own or have permission to test  
✓ **Fair Use**: Respect form owners and rate limits  
✓ **Testing**: Always test with --count 1 first  
✓ **Monitoring**: Check logs for any errors  
✓ **Delays**: Script includes 2-5 second delays between submissions  

## Support & Help

1. **Quick Questions**: Check `QUICKSTART.md`
2. **Issues**: Check `README.md` troubleshooting section
3. **Config Help**: Run `python setup_config.py`
4. **Log Analysis**: Run `python log_analyzer.py report`
5. **Source Code**: See `gform_bot.py` for detailed implementation

## Tips & Best Practices

1. **Always test first**: `python gform_bot.py --count 1`
2. **Monitor new forms**: Check logs after first batch
3. **Incremental runs**: Start with 10, then increase
4. **Analyze results**: Use `python log_analyzer.py report`
5. **Keep logs**: Archive `log.txt` for records

## Next Steps

1. ✓ Install dependencies: `run.bat install`
2. ✓ Configure form: `run.bat setup`
3. ✓ Test submission: `run.bat test`
4. ✓ Run automation: `run.bat run 100`
5. ✓ Monitor results: `run.bat report`

For detailed information, see:
- `README.md` - Complete documentation
- `QUICKSTART.md` - 5-minute reference
- `COPILOT_PROMPT.md` - For AI assistance

Happy automating! 🚀
