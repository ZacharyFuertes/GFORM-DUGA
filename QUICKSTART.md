# Quick Start Guide

## 5-Minute Setup

### Step 1: Install Python (if not already installed)
- Download from https://www.python.org/downloads/
- Make sure to check "Add Python to PATH" during installation
- Python 3.10+ required

### Step 2: Navigate to project folder
```bash
cd path/to/gform-automation
```

### Step 3: Create virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 4: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Configure your form
Open `config.json` and update:
- `form_url`: Your Google Form URL
- `entry_id`: Your form field entry IDs  
- `type`: Field type (choice, email, name, phone, text, etc.)

**Need help finding these?**
Run: `python setup_config.py` for interactive setup

### Step 6: Test with one submission
```bash
python gform_bot.py --count 1
```

Check `log.txt` for results.

### Step 7: Run full automation
```bash
python gform_bot.py --count 100
```

## Finding Form Details

### Google Form URL
- Open your form in the browser
- Copy the URL from address bar
- Format: `https://docs.google.com/forms/d/FORM_ID/viewform`

### Entry IDs
1. Open the form
2. Press F12 (Open Developer Tools)
3. Right-click a form field → Inspect
4. Look for: `name="entry.1234567890"`
5. Copy the entry ID

### Field Types
- **choice**: Multiple choice / dropdown
- **email**: Email address
- **name**: Person's name
- **phone**: Phone number  
- **text**: Short text response
- **paragraph**: Long text (multiple sentences)
- **number**: Numeric value
- **date**: Date field
- **time**: Time field

## Example: Complete Setup

### 1. config.json
```json
{
  "form_url": "https://docs.google.com/forms/d/1aBcD2EfGhI3jKlM4nOpQrStUvWxYz5/viewform",
  "fields": [
    {
      "entry_id": "entry.123456789",
      "type": "choice",
      "options": ["Yes", "No", "Maybe"]
    },
    {
      "entry_id": "entry.987654321",
      "type": "email"
    },
    {
      "entry_id": "entry.555555555",
      "type": "name"
    }
  ]
}
```

### 2. Run automation
```bash
# Single submission test
python gform_bot.py --count 1

# Full run: 100 submissions
python gform_bot.py --count 100

# With custom config
python gform_bot.py --count 50 --config my_form_config.json
```

### 3. Check results
Open `log.txt` to see:
- Success/failure status
- Error messages
- Submission timestamps
- Summary statistics

## Common Commands

```bash
# Show help
python gform_bot.py --help

# 10 submissions
python gform_bot.py --count 10

# 50 submissions with different config
python gform_bot.py --count 50 --config other_form.json

# Interactive config setup
python setup_config.py
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'requests'` | Run: `pip install -r requirements.txt` |
| `FileNotFoundError: 'config.json'` | Create config.json or use: `python setup_config.py` |
| `Invalid Google Form URL` | Check URL format: `/forms/d/FORM_ID/viewform` |
| `All submissions fail` | Check entry IDs are correct, form allows responses |
| `Submissions succeed but don't appear` | Form might have response validation, CAPTCHA, or quota limit |

## What the script does

1. **Reads** config.json with form details
2. **Generates** realistic random data for each field
3. **Submits** to Google Forms via HTTP POST
4. **Logs** success/failure to console and log.txt
5. **Waits** 2-5 seconds between submissions
6. **Retries** up to 3 times on network errors
7. **Summarizes** results

## Data Generation Examples

- Names: "John Smith", "Maria Garcia"
- Emails: "john.doe@example.com"
- Phone: "+1-555-123-4567"
- Text: Random sentences
- Numbers: 1-1000
- Dates: Random past/future dates

All data is completely random and realistic using the Faker library.

## Important Notes

✓ **Fast**: Typically 1-2 seconds per submission  
✓ **Reliable**: Automatic retries on network errors  
✓ **Safe**: Only uses HTTP POST, no browser needed  
✗ **Not detection-proof**: Use responsibly, respect form owners

## Next Steps

1. Run the setup wizard: `python setup_config.py`
2. Or manually create config.json with your form details
3. Test with 1 submission: `python gform_bot.py --count 1`
4. Review log.txt for any issues
5. Run full automation: `python gform_bot.py --count N`

Questions? Check README.md for detailed documentation.
