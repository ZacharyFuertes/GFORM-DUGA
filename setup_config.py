#!/usr/bin/env python3
"""
Helper script to extract Google Form details
Helps you find the Form ID and Entry IDs for configuration
"""

import re
import json
from pathlib import Path


def extract_form_id(url: str) -> str:
    """Extract Form ID from Google Form URL"""
    match = re.search(r'/forms/d/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    raise ValueError("Invalid Google Form URL format")


def create_config_template(form_url: str, entries: dict = None) -> dict:
    """Create a config template"""
    config = {
        "form_url": form_url,
        "fields": []
    }
    
    if entries:
        for entry_id, field_info in entries.items():
            config["fields"].append({
                "entry_id": entry_id,
                "type": field_info.get("type", "text"),
                "options": field_info.get("options", [])
            })
    
    return config


def main():
    """Main helper function"""
    print("=" * 60)
    print("Google Form Automation - Configuration Helper")
    print("=" * 60)
    
    # Get Form URL
    print("\n1. Enter your Google Form URL:")
    print("   Format: https://docs.google.com/forms/d/FORM_ID/viewform")
    form_url = input("   URL: ").strip()
    
    try:
        form_id = extract_form_id(form_url)
        print(f"\n✓ Form ID extracted: {form_id}")
    except ValueError as e:
        print(f"✗ Error: {e}")
        return
    
    # Manual entry ID input
    print("\n2. Enter form field entry IDs (or skip to use empty config):")
    print("   To find entry IDs, inspect form fields and look for name='entry.XXXXXXXX'")
    print("   Enter 'done' when finished, or leave blank to use example\n")
    
    fields = []
    field_types = ['choice', 'email', 'name', 'phone', 'text', 'paragraph', 'number', 'date', 'time']
    
    field_num = 1
    while True:
        entry_id = input(f"   Field {field_num} - Entry ID (or 'done'): ").strip()
        
        if entry_id.lower() == 'done':
            if fields:
                break
            else:
                print("   Using example configuration...")
                break
        
        if not entry_id:
            continue
        
        print(f"      Type ({', '.join(field_types)}): ", end='')
        field_type = input().strip().lower()
        
        if field_type not in field_types:
            field_type = 'text'
        
        field = {
            "entry_id": entry_id,
            "type": field_type
        }
        
        if field_type == 'choice':
            options = input("      Options (comma-separated): ").strip()
            field["options"] = [opt.strip() for opt in options.split(',')]
        
        fields.append(field)
        field_num += 1
    
    # Create config
    config = {
        "form_url": form_url,
        "fields": fields if fields else [
            {
                "entry_id": "entry.1234567890",
                "type": "choice",
                "options": ["Option A", "Option B", "Option C"]
            },
            {
                "entry_id": "entry.1234567891",
                "type": "name"
            },
            {
                "entry_id": "entry.1234567892",
                "type": "email"
            }
        ]
    }
    
    # Save configuration
    config_path = "config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✓ Configuration saved to {config_path}")
    print("\nConfiguration:")
    print(json.dumps(config, indent=2))
    
    print("\n" + "=" * 60)
    print("Next steps:")
    print("1. Review config.json and update entry IDs if needed")
    print("2. Run: python gform_bot.py --count 1")
    print("3. Check log.txt for results")
    print("=" * 60)


if __name__ == '__main__':
    main()
