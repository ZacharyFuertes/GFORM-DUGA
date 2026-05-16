import requests
from gform_bot import build_payload, FORM_URL

session = requests.Session()
payload = build_payload()
if 'partialResponse' in payload:
    del payload['partialResponse']

r = session.post(FORM_URL, data=payload)
print("Status:", r.status_code)
html = r.text

if "tugon" in html.lower() or "recorded" in html.lower() or "thanks" in html.lower() or "salamat" in html.lower():
    print("SUCCESS INDICATOR FOUND IN HTML")
else:
    print("NO SUCCESS INDICATOR")
    
# Let's see if we see "The response has been recorded" or its tag
if "freebirdFormviewerViewResponseConfirmationMessage" in html:
    print("CONFIRMATION MESSAGE CLASS FOUND!")

with open("test2.html", "w", encoding="utf-8") as f:
    f.write(html)
