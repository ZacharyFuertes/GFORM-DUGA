"""Standalone inspection helper for Google Form schemas.

Delegates to form_schema.analyze() so the GUI, the CLI bot, and this script
all parse FB_PUBLIC_LOAD_DATA_ the same way.
"""

from form_schema import analyze as _analyze


def analyze_gform(url):
    """Parses a Google Form URL and extracts question types, labels, and entry IDs."""
    return _analyze(url)


if __name__ == "__main__":
    # Test with your actual working form
    test_url = "https://docs.google.com/forms/d/e/1FAIpQLSeXyKpROVhz6hnbLiNWpiSStdk-mGtFUnx9IG-juDXVCzovAg/viewform"
    
    print(f"--- Analyzing: {test_url} ---\n")
    result = analyze_gform(test_url)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Form Title: {result['title']}")
        print(f"Description: {result['description']}")
        print("-" * 40)
        for i, q in enumerate(result['questions'], 1):
            print(f"Q{i}: {q['label']}")
            print(f"   Type:  {q['type']}")
            print(f"   ID:    {q['entry_id']}")
            print(f"   Required: {q['required']}")
            print()
