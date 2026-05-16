import re

html = open('response_output.html', encoding='utf-8').read()
# The questions data is usually array like [1234567, "Question title", null, 0, [[8765432, ...], true, ...] 
# Actually, the quickest way to find ALL required entry IDs from the page is to parse K1cgmc or FB_PUBLIC_LOAD_DATA_
# Let's just find all matches of: `[number,[[...]],true,` or `[number,null,true,`
# More generally, the field schema is:
# [[entry_id, ...], true, ...] where true indicates required.
# Actually, let's just use re to find `[<entry_id>,...,true,` 
# Wait, let's find the exact data for fields.

# Let's extract FB_PUBLIC_LOAD_DATA
match = re.search(r'var FB_PUBLIC_LOAD_DATA_ = (.*?);</script>', html)
if not match:
    # search in window.WIZ_global_data
    match = re.search(r'\]\]\,\"([a-zA-Z0-9_-]+)\":\"%\.@\.(.*?)\"', html)

print("Look for required entry IDs in the html")
pattern = r'\[(\d+),\[(.*?)\]\],(true|false),'
for m in re.findall(pattern, html):
    entry_id = m[0]
    required = m[2]
    if required == 'true':
        print("REQUIRED:", entry_id)
        
pattern2 = r'\[\[(\d+),.+?\],(true|false),'
for m in re.findall(pattern2, html):
    entry_id = m[0]
    required = m[1]
    if required == 'true':
        print("REQUIRED 2:", entry_id)
