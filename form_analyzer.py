import re
import json
import requests

def analyze_gform(url):
    """
    Parses a Google Form URL and extracts question types, labels, and entry IDs.
    """
    try:
        # 1. Fetch the form page
        response = requests.get(url)
        if response.status_code != 200:
            return {"error": f"Failed to fetch form. Status code: {response.status_code}"}

        # 2. Find the FB_PUBLIC_LOAD_DATA_ block using Regex
        # This contains the entire form schema in a nested list format
        match = re.search(r'var FB_PUBLIC_LOAD_DATA_ = (.*?);</script>', response.text, re.DOTALL)
        if not match:
            return {"error": "Could not find form data. Is this a valid Google Form link?"}

        data_str = match.group(1)
        data = json.loads(data_str)

        # 3. Extract relevant fields from the nested list structure
        try:
            # The structure of FB_PUBLIC_LOAD_DATA_ can vary. 
            # Usually data[1] is the main content.
            if not data or len(data) < 2 or data[1] is None:
                return {"error": "Form data structure is empty or invalid."}
            
            questions_list = data[1][1] if len(data[1]) > 1 else []
        except (IndexError, TypeError) as e:
            return {"error": f"Failed to access questions list: {str(e)}"}
        
        form_info = {
            "title": data[1][8] if len(data[1]) > 8 else "Untitled Form",
            "description": data[1][0],
            "questions": []
        }

        for q in questions_list:
            if not q or len(q) < 4: continue # Skip empty or header-only blocks
            
            # Basic question info
            label = q[1]
            q_type_code = q[3]
            
            # Map type codes to human-readable types
            type_map = {
                0: "Short Text",
                1: "Long Text",
                2: "Multiple Choice",
                3: "Dropdown",
                4: "Checkboxes",
                5: "Linear Scale",
                7: "Grid / Matrix"
            }
            type_label = type_map.get(q_type_code, f"Unknown ({q_type_code})")

            # Entry IDs are in q[4]
            entry_id = None
            required = False
            try:
                if q[4] and len(q[4]) > 0:
                    entry_id = q[4][0][0]
                    required = bool(q[4][0][2]) if len(q[4][0]) > 2 else False
            except (IndexError, TypeError):
                pass

            form_info["questions"].append({
                "label": label,
                "type": type_label,
                "entry_id": f"entry.{entry_id}" if entry_id else "No ID (Header/Info)",
                "required": required
            })

        return form_info

    except Exception as e:
        return {"error": str(e)}

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
