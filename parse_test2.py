import re
html = open('test2.html', encoding='utf-8').read()
if "Maaaring hindi makita o mairekord ang mga pagbabagong ginawa mo" in html:
    print("Page returned: changes won't be saved warning")
alerts = re.findall(r'<div[^>]*role="alert"[^>]*>(.*?)</div>', html, re.IGNORECASE)
alerts = [a for a in alerts if a.strip()]
print('Alerts:', alerts)
print('Is there freebirdFormviewerViewResponseConfirmationMessage:', 'freebirdFormviewerViewResponseConfirmationMessage' in html)
