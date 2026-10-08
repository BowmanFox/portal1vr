# usage: sqlint.py director.nut -> lines where a statement follows a closing brace on the same line without ';'
# (Squirrel's compiler rejects `}if(...)` / `}local x` with "end of statement expected (; or lf)")
import re, sys
bad = 0
for n, line in enumerate(open(sys.argv[1], encoding='utf-8', errors='replace'), 1):
    code = re.sub(r'"(\\.|[^"\\])*"', '""', line.split('//')[0])
    for m in re.finditer(r'\}\s*([A-Za-z_]\w*)', code):
        if m.group(1) in ('else', 'catch'): continue
        print(f'{n}:{m.start()}: {code.strip()[:160]}'); bad += 1
print('suspicious', bad)
