import requests
import random

from gform_bot import FIELDS, WEIGHTS, build_payload, FORM_URL

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

payload = build_payload()
print("Payload:", payload)

r = session.post(FORM_URL, data=payload)
print("Status:", r.status_code)

with open("response_output.html", "w", encoding="utf-8") as f:
    f.write(r.text)

print("Saved HTML to response_output.html")
