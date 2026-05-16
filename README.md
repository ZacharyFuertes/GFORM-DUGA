# Google Form Automation Bot

Automates Google Form submissions with realistic random data using HTTP requests (no browser automation).

## Features

✓ **HTTP-only**: Pure requests library, no Selenium or browser automation  
✓ **Realistic Data**: Uses Faker library to generate realistic answers  
✓ **Configurable**: JSON-based form configuration  
✓ **Retry Logic**: Automatic retries (max 3 attempts) on network errors  
✓ **Logging**: Comprehensive logging to console and `log.txt`  
✓ **CLI Interface**: Easy command-line arguments  
✓ **Random Delays**: 2-5 second delays between submissions to avoid detection  

## Requirements

- Python 3.10+
- requests
- faker
- python-dotenv (optional)

## Setup

### 1. Clone or download this project

```bash
cd gform-automation
```

### 2. Create virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your Google Form

Open `config.json` and update:

```json
{
  "form_url": "https://docs.google.com/forms/d/YOUR_FORM_ID_HERE/viewform",
  "fields": [
    {
      "entry_id": "entry.XXXXXXXX",
      "type": "choice",
      "options": ["A", "B", "C"]
    },
    {
      "entry_id": "entry.YYYYYYYY",
      "type": "email"
    }
  ]
}
```

## Getting Form Configuration

### Find Form ID
The form ID is in the URL: `https://docs.google.com/forms/d/**FORM_ID**/viewform`

### Find Entry IDs
1. Open the form in your browser
2. Open Developer Tools (F12)
3. Inspect a form field
4. Look for the `name` attribute: `entry.1234567890`

Or:
1. Right-click → Inspect Element on each form field
2. Find input/select elements with `name="entry.XXXXXXXX"`

## Field Types

| Type | Description | Example |
|------|-------------|---------|
| `choice` | Multiple choice or dropdown | `options: ["A", "B", "C"]` |
| `email` | Email address | Generates: `john.doe@example.com` |
| `name` | Full name | Generates: `Jane Smith` |
| `phone` | Phone number | Generates: `+1-555-123-4567` |
| `text` | Short text | Generates: random sentence |
| `paragraph` | Long text | Generates: 5-sentence paragraph |
| `number` | Integer | Generates: 1-1000 |
| `date` | Date | Generates: random date |
| `time` | Time | Generates: random time |

## Usage

### Basic submission (single)
```bash
python gform_bot.py
```

### Submit 10 responses
```bash
python gform_bot.py --count 10
```

### Submit 50 responses with custom config
```bash
python gform_bot.py --count 50 --config config.json
```

### Help
```bash
python gform_bot.py --help
```

## Example Output

```
2025-01-15 14:23:45,123 - INFO - Config loaded from config.json
2025-01-15 14:23:45,124 - INFO - Starting 3 form submission(s)
2025-01-15 14:23:45,124 - INFO - Form URL: https://docs.google.com/forms/d/1234abcd/viewform
2025-01-15 14:23:45,124 - INFO - Fields: 5

--- Submission 1/3 ---
2025-01-15 14:23:46,321 - INFO - ✓ Submission successful (Status: 200)
2025-01-15 14:23:48,456 - INFO - Waiting 3.2 seconds before next submission...

--- Submission 2/3 ---
2025-01-15 14:23:51,789 - INFO - ✓ Submission successful (Status: 200)
2025-01-15 14:23:54,012 - INFO - Waiting 2.8 seconds before next submission...

--- Submission 3/3 ---
2025-01-15 14:23:56,345 - INFO - ✓ Submission successful (Status: 200)

==================================================
Submission Summary:
  Total: 3
  Successful: 3
  Failed: 0
==================================================
```

## Logging

Logs are saved to `log.txt` and displayed in the console.

Each submission logs:
- Request status
- Any errors or retries
- Timing information
- Final summary statistics

## Environment Variables (Optional)

Create a `.env` file for optional configuration:

```
FORM_CONFIG=config.json
MAX_RETRIES=3
TIMEOUT=10
```

## Error Handling

The script handles:
- **Connection errors**: Automatic retry (max 3 attempts)
- **Timeouts**: Retry with 2-second delay
- **Invalid config**: Clear error message and exit
- **HTTP errors**: Logged and counted as failed
- **Keyboard interrupt**: Graceful shutdown (Ctrl+C)

## Rate Limiting

The script includes:
- **2-5 second random delay** between submissions
- **10 second timeout** per request
- **3 retry attempts** on failure

This helps avoid detection by Google's anti-bot systems.

## Common Issues

### "Config file not found"
- Make sure `config.json` is in the same directory as `gform_bot.py`
- Or use `--config /path/to/config.json`

### "Invalid Google Form URL"
- URL must contain `/forms/d/FORM_ID/viewform`
- Example: `https://docs.google.com/forms/d/1abc2def3ghi4jkl5mno6pqr7stu8vwx/viewform`

### Form submissions not showing up
- Check that entry IDs are correct
- Verify form is not closed/restricted
- Check Google Forms for response limits
- Forms may require authentication on some domains

### Submissions marked as spam
- Increase delay times in the script
- Use more varied data (Faker helps)
- Space out submissions over time
- Check bot detection settings on the form

## Legal & Ethical Notes

⚠️ **Important**: Only use this tool for:
- Your own forms
- Testing and development
- Authorized testing only

Do not use to:
- Spam other people's forms
- Circumvent form restrictions
- Violate Google's Terms of Service

## License

MIT License - Use freely for personal/educational purposes.

## Support

For issues or questions, check:
1. `log.txt` for detailed error messages
2. Config file format and entry IDs
3. Form URL and accessibility
4. Python version (3.10+)

