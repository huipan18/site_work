#!/usr/bin/env python3
from pathlib import Path
from bs4 import BeautifulSoup, Comment, Doctype
import json,re,hashlib
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'translations'; OUT.mkdir(exist_ok=True)
EXCLUDE={'translations','logger_backups','.venv','venv','env','__pycache__','.git','.github','.pytest_cache','.mypy_cache','node_modules'}
PROTECTED=['Poppo Live','Poppo','Official Poppo Agency','VSHOW PTE. LTD.','WhatsApp','Google Play','App Store','73546256','LIVE']

def norm(s): return ' '.join(str(s).split())
def key(s): return 's_'+hashlib.sha1(norm(s).encode()).hexdigest()[:12]

def is_language_option(node):
    return bool(
        getattr(node, 'parent', None)
        and node.parent.name == 'option'
        and getattr(node.parent, 'parent', None)
        and node.parent.parent.get('id') == 'language-select'
    )

strings={}
for p in sorted(ROOT.rglob('*.html')):
    rel=p.relative_to(ROOT)
    if rel.parts and (rel.parts[0] in {'tl','id','vi','th','my','ms','km','lo','hi','ur','bn','te','ta','pa','ne','si','ar','tr','sw','am','fr','pt','es','ru','kk','uz','uk','zh','ja'}): continue
    if any(x in EXCLUDE for x in rel.parts): continue
    s=BeautifulSoup(p.read_text(encoding='utf-8',errors='ignore'),'html.parser')
    vals=[]
    for n in s.find_all(string=True):
        # Never treat <!DOCTYPE html> or comments as page copy.
        if isinstance(n,(Doctype,Comment)): continue
        if n.parent and n.parent.name not in {'script','style','noscript'}:
            if is_language_option(n): continue
            t=norm(n)
            if t and re.search(r'[A-Za-z]',t): vals.append(t)
    for tag in s.find_all(True):
        for a in ('placeholder','aria-label','title','alt'):
            v=tag.get(a)
            if isinstance(v,str) and re.search(r'[A-Za-z]',v): vals.append(norm(v))
    for m in s.find_all('meta'):
        k=(m.get('name') or m.get('property') or '').lower(); v=m.get('content')
        if k in {'description','og:title','og:description','twitter:title','twitter:description'} and isinstance(v,str): vals.append(norm(v))
    for v in vals: strings.setdefault(key(v),v)

# JavaScript-generated user-facing strings
js=(ROOT/'assets/js/main.js').read_text(encoding='utf-8',errors='ignore')
# The language registry contains selector display names, not translatable page copy.
js_scan=re.sub(r'const\s+POPPO_LANGUAGES\s*=\s*Object\.freeze\(\{.*?\}\);', '', js, flags=re.S)
js_vals=[]
js_vals += re.findall(r'\b(?:answer|label)\s*:\s*"([^"]*[A-Za-z][^"]*)"', js_scan)
js_vals += re.findall(r'\bt\(\s*"([^"]*[A-Za-z][^"]*)"\s*\)', js)
m=re.search(r'const greetings\s*=\s*\{.*?en\s*:\s*"([^"]+)"',js,re.S)
if m: js_vals.append(m.group(1))
for v in js_vals:
    v=norm(v)
    if v: strings.setdefault(key(v),v)

(OUT/'en.json').write_text(json.dumps({'locale':'en','protected':PROTECTED,'strings':strings},ensure_ascii=False,indent=2),encoding='utf-8')
for code in ['tl','id','vi','th','my','ms','km','lo','hi','ur','bn','te','ta','pa','ne','si','ar','tr','sw','am','fr','pt','es','ru','kk','uz','uk','zh','ja']:
    p=OUT/f'{code}.json'
    old={}
    if p.exists():
        try: old=json.loads(p.read_text(encoding='utf-8')).get('strings',{})
        except Exception: pass
    merged={k:old.get(k,'') for k in strings}
    p.write_text(json.dumps({'locale':code,'sourceLocale':'en','protected':PROTECTED,'strings':merged},ensure_ascii=False,indent=2),encoding='utf-8')
print('extracted',len(strings),'stable strings into',OUT)
