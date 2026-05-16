import re
html = open('response_output.html', encoding='utf-8').read()
m = re.search(r'\[1778839630,\"(.*?)\"', html)
print(m.group(1) if m else 'Not found 1778839630')
m2 = re.search(r'\[1329148115,\"(.*?)\"', html)
print(m2.group(1) if m2 else 'Not found 1329148115')

# Lets also check if pageHistory should just be "0" for the first part and what Google Forms requires!
