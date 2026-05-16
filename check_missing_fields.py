import re
import gform_bot

html = open('response_output.html', encoding='utf-8').read()

# Find all arrays defining a field: `[1234567,` with `true` as required somewhere inside.
# `K1cgmc` holds the schema.
match = re.search(r'\"K1cgmc\":\"%\.@\.(.*?)\"', html)
if match:
    data_str = match.group(1).encode().decode('unicode_escape')
    
    # regex to find [ENTRY_ID,...] ... true
    # A safer way: just extract all entry IDs. 
    entry_ids = set(re.findall(r'\[(\d{9,11})', data_str))
    
    bot_fields = [k.replace("entry.", "") for k in gform_bot.FIELDS.keys()]
    bot_fields.append("2133561483") # Gender is hardcoded
    
    print("Found Entry IDs in HTML:", len(entry_ids))
    print("Bot Payload Entry IDs:", len(bot_fields))
    
    missing_in_bot = []
    for eid in entry_ids:
        if eid not in bot_fields:
            missing_in_bot.append(eid)
            
    # Some IDs might be section headers. We can check if they are in the HTML with their titles.
    if missing_in_bot:
        print("IDS IN HTML BUT NOT IN BOT:")
        for eid in missing_in_bot:
            name_match = re.search(r'\[' + eid + r',"(.*?)"', data_str)
            title = name_match.group(1) if name_match else "Unknown"
            print(f"- {eid}: {title}")
