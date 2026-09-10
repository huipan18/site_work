#!/usr/bin/env python3
from __future__ import annotations
import json,re,sys
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parent
BASE='https://www.officialpoppoagency.com'
LANGS=['en','tl','id','vi','th','my','ms','km','lo','hi','ur','bn','te','ta','pa','ne','si','ar','tr','sw','am','fr','pt','es','ru','kk','uz','uk','zh','ja']
RTL={'ar','ur'}
EXCLUDES={'translations','logger_backups','.venv','venv','env','__pycache__','.git','.github','.pytest_cache','.mypy_cache','node_modules'}
PROTECTED=['Poppo Live','Poppo','Official Poppo Agency','VSHOW PTE. LTD.','WhatsApp','Google Play','App Store','Apple App Store','Vone','73546256']
errors=[]; warnings=[]

def err(x): errors.append(x)
def warn(x): warnings.append(x)

def master_pages():
    out=[]
    for p in ROOT.rglob('*.html'):
        rel=p.relative_to(ROOT)
        if rel.parts and rel.parts[0] in LANGS and rel.parts[0]!='en': continue
        if any(part in EXCLUDES for part in rel.parts): continue
        out.append(p)
    return sorted(out)

def route(p):
    rel=p.relative_to(ROOT).as_posix()
    if rel=='index.html': return '/'
    if rel.endswith('/index.html'): return '/'+rel[:-10]
    return '/'+rel

def expected_file(p,lang): return p if lang=='en' else ROOT/lang/p.relative_to(ROOT)

def expected_url(path,lang): return BASE+(path if lang=='en' else '/'+lang+('/' if path=='/' else path))

# Translation catalogs must be complete and meaningfully non-English.
enp=ROOT/'translations/en.json'
if not enp.exists(): err('missing translations/en.json')
else:
    en=json.loads(enp.read_text(encoding='utf-8'))['strings']
    for lang in LANGS[1:]:
        p=ROOT/'translations'/f'{lang}.json'
        if not p.exists(): err(f'missing translation catalog {lang}'); continue
        d=json.loads(p.read_text(encoding='utf-8')).get('strings',{})
        missing=[k for k in en if not str(d.get(k,'')).strip()]
        if missing: err(f'{lang}: {len(missing)} missing translation strings')
        same=[]
        for k,v in d.items():
            src=en.get(k,'')
            if v==src and re.search(r'[A-Za-z]{4}',src) and not any(term in src for term in PROTECTED): same.append(src)
        if len(same)>20: warn(f'{lang}: {len(same)} strings equal English; review leakage')

pages=master_pages()
for master in pages:
    srcroute=route(master)
    for lang in LANGS:
        f=expected_file(master,lang)
        if not f.exists(): err(f'missing page {f.relative_to(ROOT)}'); continue
        soup=BeautifulSoup(f.read_text(encoding='utf-8',errors='ignore'),'html.parser')
        if not soup.html: err(f'{f.relative_to(ROOT)}: missing html element'); continue
        if not soup.html.get('lang'): err(f'{f.relative_to(ROOT)}: missing lang')
        wantdir='rtl' if lang in RTL else 'ltr'
        if soup.html.get('dir')!=wantdir: err(f'{f.relative_to(ROOT)}: dir should be {wantdir}')
        if not soup.title or not soup.title.get_text(strip=True): err(f'{f.relative_to(ROOT)}: missing title')
        md=soup.find('meta',attrs={'name':'description'})
        if master.name!='404.html' and (not md or not md.get('content','').strip()): err(f'{f.relative_to(ROOT)}: missing meta description')
        can=soup.find('link',rel='canonical')
        want=expected_url(srcroute,lang)
        if not can: err(f'{f.relative_to(ROOT)}: missing canonical')
        elif can.get('href')!=want: err(f'{f.relative_to(ROOT)}: canonical {can.get("href")} != {want}')
        hrefs={x.get('hreflang'):x.get('href') for x in soup.select('link[rel="alternate"][hreflang]')}
        for code in LANGS:
            bcp={'tl':'fil','zh':'zh-Hans'}.get(code,code)
            if bcp not in hrefs: err(f'{f.relative_to(ROOT)}: missing hreflang {bcp}')
        if hrefs.get('x-default')!=BASE+srcroute: err(f'{f.relative_to(ROOT)}: bad/missing x-default')
        if lang in RTL and not soup.find('link',href='/assets/css/rtl.css'): err(f'{f.relative_to(ROOT)}: rtl.css not loaded')
        # JSON-LD syntax
        for ld in soup.find_all('script',attrs={'type':'application/ld+json'}):
            try: json.loads(ld.string or ld.get_text())
            except Exception as e: err(f'{f.relative_to(ROOT)}: malformed JSON-LD: {e}')
        # local internal links and assets should resolve in package where applicable
        for tag,attr in [('a','href'),('link','href'),('script','src'),('img','src')]:
            for n in soup.find_all(tag):
                v=n.get(attr)
                if not v or not v.startswith('/') or v.startswith('//') or v.startswith('/api/'): continue
                path=urlparse(v).path
                if path.endswith('/'):
                    cand=ROOT/path.lstrip('/')/'index.html'
                else:
                    cand=ROOT/path.lstrip('/')
                # sitemap endpoints and backend can be external-generated
                if not cand.exists() and not path.startswith('/sitemap'):
                    err(f'{f.relative_to(ROOT)}: broken internal {attr} {v}')

for name in ['sitemap-index.xml','sitemap.xml','robots.txt','assets/css/style.css','assets/css/rtl.css','assets/js/main.js']:
    if not (ROOT/name).exists(): err(f'missing {name}')

print(f'Validation: {len(errors)} errors, {len(warnings)} warnings')
for x in errors[:250]: print('ERROR:',x)
if len(errors)>250: print(f'... {len(errors)-250} more errors')
for x in warnings[:100]: print('WARN:',x)
sys.exit(1 if errors else 0)
