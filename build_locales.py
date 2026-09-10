#!/usr/bin/env python3
"""Build crawlable localized static pages from the existing English HTML masters.
Does not redesign templates or duplicate shared assets.
"""
from __future__ import annotations
import argparse, json, re, shutil, hashlib
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup, NavigableString, Comment, Doctype

ROOT = Path(__file__).resolve().parent
BASE_URL = "https://www.officialpoppoagency.com"
TRANSLATIONS = ROOT / "translations"
EXCLUDES = {"translations","__pycache__","logger_backups",".venv","venv","env",".git",".github",".pytest_cache",".mypy_cache","node_modules"}
LANGS = {
    "en": {"name":"English","bcp47":"en","dir":"ltr"},
    "tl": {"name":"Filipino / Tagalog","bcp47":"fil","dir":"ltr"},
    "id": {"name":"Bahasa Indonesia","bcp47":"id","dir":"ltr"},
    "vi": {"name":"Vietnamese","bcp47":"vi","dir":"ltr"},
    "th": {"name":"Thai","bcp47":"th","dir":"ltr"},
    "my": {"name":"Burmese","bcp47":"my","dir":"ltr"},
    "ms": {"name":"Malay","bcp47":"ms","dir":"ltr"},
    "km": {"name":"Khmer","bcp47":"km","dir":"ltr"},
    "lo": {"name":"Lao","bcp47":"lo","dir":"ltr"},
    "hi": {"name":"Hindi","bcp47":"hi","dir":"ltr"},
    "ur": {"name":"Urdu","bcp47":"ur","dir":"rtl"},
    "bn": {"name":"Bangla","bcp47":"bn","dir":"ltr"},
    "te": {"name":"Telugu","bcp47":"te","dir":"ltr"},
    "ta": {"name":"Tamil","bcp47":"ta","dir":"ltr"},
    "pa": {"name":"Punjabi","bcp47":"pa","dir":"ltr"},
    "ne": {"name":"Nepali","bcp47":"ne","dir":"ltr"},
    "si": {"name":"Sinhala","bcp47":"si","dir":"ltr"},
    "ar": {"name":"Arabic","bcp47":"ar","dir":"rtl"},
    "tr": {"name":"Turkish","bcp47":"tr","dir":"ltr"},
    "sw": {"name":"Swahili","bcp47":"sw","dir":"ltr"},
    "am": {"name":"Amharic","bcp47":"am","dir":"ltr"},
    "fr": {"name":"French","bcp47":"fr","dir":"ltr"},
    "pt": {"name":"Portuguese","bcp47":"pt","dir":"ltr"},
    "es": {"name":"Spanish","bcp47":"es","dir":"ltr"},
    "ru": {"name":"Russian","bcp47":"ru","dir":"ltr"},
    "kk": {"name":"Kazakh","bcp47":"kk","dir":"ltr"},
    "uz": {"name":"Uzbek","bcp47":"uz","dir":"ltr"},
    "uk": {"name":"Ukrainian","bcp47":"uk","dir":"ltr"},
    "zh": {"name":"Chinese","bcp47":"zh-Hans","dir":"ltr"},
    "ja": {"name":"Japanese","bcp47":"ja","dir":"ltr"},
}
RTL = {k for k,v in LANGS.items() if v["dir"]=="rtl"}
PROTECTED = [
    "Poppo Live","Poppo","Official Poppo Agency","VSHOW PTE. LTD.","WhatsApp",
    "Google Play","App Store","Apple App Store","Vone","73546256",
    "+91 78383 17307","+91-7838317307","invite-poppo.com/fT8SYJ"
]
FLAGS = {"en":"🇬🇧","tl":"🇵🇭","id":"🇮🇩","vi":"🇻🇳","th":"🇹🇭","my":"🇲🇲","ms":"🇲🇾","km":"🇰🇭","lo":"🇱🇦","hi":"🇮🇳","ur":"🇵🇰","bn":"🇧🇩","te":"🇮🇳","ta":"🇮🇳","pa":"🇮🇳","ne":"🇳🇵","si":"🇱🇰","ar":"🇸🇦","tr":"🇹🇷","sw":"🌍","am":"🇪🇹","fr":"🇫🇷","pt":"🇧🇷","es":"🇪🇸","ru":"🇷🇺","kk":"🇰🇿","uz":"🇺🇿","uk":"🇺🇦","zh":"🇨🇳","ja":"🇯🇵"}

TEXT_ATTRS=("placeholder","aria-label","title","alt")
META_ATTRS=("content",)


def norm(s:str)->str:
    return " ".join(str(s).split())

def key_for(s:str)->str:
    return "s_"+hashlib.sha1(norm(s).encode("utf-8")).hexdigest()[:12]

def master_pages():
    pages=[]
    for p in ROOT.rglob("*.html"):
        rel=p.relative_to(ROOT)
        if rel.parts and rel.parts[0] in LANGS and rel.parts[0] != "en": continue
        if any(part in EXCLUDES for part in rel.parts): continue
        pages.append(p)
    return sorted(pages)

def page_path(p:Path)->str:
    rel=p.relative_to(ROOT).as_posix()
    if rel=="index.html": return "/"
    if rel.endswith("/index.html"): return "/"+rel[:-10]
    return "/"+rel

def localized_path(path:str, lang:str)->str:
    if lang=="en": return path
    if path=="/": return f"/{lang}/"
    return f"/{lang}{path}"

def output_path(p:Path, lang:str)->Path:
    rel=p.relative_to(ROOT)
    if lang=="en": return p
    return ROOT/lang/rel

def load_catalog(lang:str):
    path=TRANSLATIONS/f"{lang}.json"
    if not path.exists(): return {}
    data=json.loads(path.read_text(encoding="utf-8"))
    return data.get("strings",data)

def tr(text:str,catalog:dict,allow_fallback:bool)->str:
    n=norm(text)
    if not n or not re.search(r"[A-Za-z]",n): return text
    k=key_for(n)
    val=catalog.get(k)
    if isinstance(val,str) and val.strip(): return val
    if allow_fallback: return text
    raise KeyError(f"missing translation {k}: {n[:100]}")

def is_internal(href:str)->bool:
    if not href or href.startswith(("#","mailto:","tel:","javascript:","data:")): return False
    if href.startswith("/"): return True
    try:
        u=urlparse(href)
        return u.netloc in {"officialpoppoagency.com","www.officialpoppoagency.com"}
    except: return False

def localize_href(href:str,lang:str)->str:
    if lang=="en" or not is_internal(href): return href
    u=urlparse(href)
    path=u.path or "/"
    # shared/static/backend resources are never localized
    if path.startswith(("/assets/","/api/","/manifest.webmanifest","/robots.txt","/sitemap")) or re.search(r"\.[A-Za-z0-9]{2,6}$",path):
        return href
    # strip any old locale prefix
    parts=path.split("/")
    if len(parts)>1 and parts[1] in LANGS and parts[1] != "en":
        path="/"+"/".join(parts[2:])
        if not path.endswith("/") and u.path.endswith("/"): path += "/"
    path=localized_path(path,lang)
    return urlunparse((u.scheme,u.netloc,path,u.params,u.query,u.fragment)) if u.scheme or u.netloc else path + (("?"+u.query) if u.query else "") + (("#"+u.fragment) if u.fragment else "")

def add_hreflang(soup:BeautifulSoup, src_path:str):
    for old in soup.select('link[rel="alternate"][hreflang]'): old.decompose()
    canonical=soup.find("link",rel="canonical")
    anchor=canonical or soup.head.find("meta",charset=True)
    for code,info in LANGS.items():
        tag=soup.new_tag("link",rel="alternate",hreflang=info["bcp47"],href=BASE_URL+localized_path(src_path,code))
        anchor.insert_after(tag); anchor=tag
    x=soup.new_tag("link",rel="alternate",hreflang="x-default",href=BASE_URL+src_path)
    anchor.insert_after(x)

def update_canonical_and_social(soup,src_path,lang):
    url=BASE_URL+localized_path(src_path,lang)
    can=soup.find("link",rel="canonical")
    if can: can["href"]=url
    else: soup.head.append(soup.new_tag("link",rel="canonical",href=url))
    for selector in [('meta',{'property':'og:url'}),('meta',{'name':'twitter:url'})]:
        m=soup.find(*selector)
        if m: m['content']=url

def localize_jsonld(obj,catalog,lang,allow_fallback):
    if isinstance(obj,dict):
        out={}
        for k,v in obj.items():
            if k=="inLanguage": out[k]=LANGS[lang]["bcp47"]
            elif k in {"url","@id","sameAs","image","logo","contentUrl","embedUrl"}: out[k]=v
            else: out[k]=localize_jsonld(v,catalog,lang,allow_fallback)
        if obj.get("@type") in {"WebPage","Article","FAQPage","WebSite"} and "inLanguage" not in out:
            out["inLanguage"]=LANGS[lang]["bcp47"]
        return out
    if isinstance(obj,list): return [localize_jsonld(v,catalog,lang,allow_fallback) for v in obj]
    if isinstance(obj,str) and re.search(r"[A-Za-z]",obj) and not obj.startswith(("http://","https://")):
        return tr(obj,catalog,allow_fallback)
    return obj

def language_options(soup,lang):
    for select in soup.select("select#language-select, select[data-language-select]"):
        select.clear()
        for code,info in LANGS.items():
            o=soup.new_tag("option",value=code)
            if code==lang: o["selected"]="selected"
            o.string=f"{FLAGS.get(code,'🌐')} {info['name']}"
            select.append(o)

def process(p,lang,catalog,allow_fallback):
    src=p.read_text(encoding="utf-8",errors="ignore")
    soup=BeautifulSoup(src,"html.parser")
    src_path=page_path(p)
    if soup.html:
        soup.html["lang"]=LANGS[lang]["bcp47"]
        soup.html["dir"]=LANGS[lang]["dir"]
    if soup.body: soup.body["data-page-locale"]=lang

    # translate visible text preserving exact markup structure
    for node in list(soup.find_all(string=True)):
        if isinstance(node,(Doctype,Comment)): continue
        if not node.parent or node.parent.name in {"script","style","noscript"}: continue
        raw=str(node); n=norm(raw)
        if not n or not re.search(r"[A-Za-z]",n): continue
        # selector language labels are rebuilt below
        if node.parent.name=="option" and node.parent.parent and node.parent.parent.get("id")=="language-select": continue
        translated=tr(n,catalog,allow_fallback)
        if translated!=n:
            lead=raw[:len(raw)-len(raw.lstrip())]; tail=raw[len(raw.rstrip()):]
            node.replace_with(NavigableString(lead+translated+tail))

    # language-dependent attributes
    for tag in soup.find_all(True):
        for attr in TEXT_ATTRS:
            if tag.has_attr(attr):
                v=tag.get(attr)
                if isinstance(v,str) and re.search(r"[A-Za-z]",v): tag[attr]=tr(v,catalog,allow_fallback)
        for attr in ("href",):
            if tag.has_attr(attr): tag[attr]=localize_href(tag[attr],lang)

    # translate metadata text
    for m in soup.find_all("meta"):
        key=(m.get("name") or m.get("property") or "").lower()
        if key in {"description","og:title","og:description","twitter:title","twitter:description"} and m.get("content"):
            m["content"]=tr(m["content"],catalog,allow_fallback)

    # JSON-LD
    for s in soup.find_all("script",attrs={"type":"application/ld+json"}):
        try:
            obj=json.loads(s.string or s.get_text())
            obj=localize_jsonld(obj,catalog,lang,allow_fallback)
            # fix internal URLs inside localized schema recursively
            def fix_urls(x):
                if isinstance(x,dict):
                    for k,v in list(x.items()):
                        if k in {"url","@id"} and isinstance(v,str) and v.startswith(BASE_URL):
                            u=urlparse(v); x[k]=BASE_URL+localize_href(u.path+(('#'+u.fragment) if u.fragment else ''),lang)
                        else: fix_urls(v)
                elif isinstance(x,list):
                    for v in x: fix_urls(v)
            fix_urls(obj)
            s.string=json.dumps(obj,ensure_ascii=False,separators=(",",":"))
        except Exception:
            pass

    language_options(soup,lang)
    update_canonical_and_social(soup,src_path,lang)
    add_hreflang(soup,src_path)

    # RTL is separate; main CSS untouched
    if lang in RTL and not soup.find("link",href="/assets/css/rtl.css"):
        core=soup.find("link",rel="stylesheet",href=re.compile(r"/assets/css/style\.css"))
        rtl=soup.new_tag("link",rel="stylesheet",href="/assets/css/rtl.css")
        if core: core.insert_after(rtl)
        else: soup.head.append(rtl)

    # runtime dictionary: generator translates JS messages by keyed lookup
    en_source = load_catalog("en")
    runtime = {}
    for k, english in en_source.items():
        if isinstance(english,str):
            val = catalog.get(k, english) if lang != "en" else english
            runtime[english] = val if isinstance(val,str) and val.strip() else english
    data=soup.new_tag("script")
    data["id"]="poppo-i18n-runtime"; data["type"]="application/json"
    data.string=json.dumps({"locale":lang,"strings":runtime},ensure_ascii=False).replace("</","<\\/")
    main=soup.find("script",src=re.compile(r"/assets/js/main\.js"))
    if main: main.insert_before(data)
    else: soup.body.append(data)

    out=output_path(p,lang)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(str(soup),encoding="utf-8")


def write_sitemaps(pages):
    # index + one sitemap per locale
    sm=[]
    for lang in LANGS:
        urls=[]
        for p in pages:
            if p.name=="404.html": continue
            loc=BASE_URL+localized_path(page_path(p),lang)
            urls.append(f"  <url><loc>{loc}</loc></url>")
        body='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+"\n".join(urls)+"\n</urlset>\n"
        name=f"sitemap-{lang}.xml"
        (ROOT/name).write_text(body,encoding="utf-8")
        sm.append(f"  <sitemap><loc>{BASE_URL}/{name}</loc></sitemap>")
    idx='<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+"\n".join(sm)+"\n</sitemapindex>\n"
    (ROOT/"sitemap-index.xml").write_text(idx,encoding="utf-8")
    # compatibility sitemap.xml as sitemap index
    (ROOT/"sitemap.xml").write_text(idx,encoding="utf-8")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--allow-fallback",action="store_true",help="allow missing translations to remain English (for development only)")
    ap.add_argument("--locale",action="append",help="build only selected locale(s)")
    args=ap.parse_args()
    pages=master_pages()
    chosen=args.locale or [x for x in LANGS if x!="en"]
    for lang in chosen:
        if lang=="en": continue
        if lang not in LANGS: raise SystemExit(f"Unknown locale {lang}")
        # idempotent rebuild
        shutil.rmtree(ROOT/lang,ignore_errors=True)
        cat=load_catalog(lang)
        for p in pages: process(p,lang,cat,args.allow_fallback)
        print(f"built {lang}: {len(pages)} pages")
    # ensure English masters get hreflang + full selector but content/design remain same
    en=load_catalog("en")
    for p in pages: process(p,"en",en,True)
    write_sitemaps(pages)
    print(f"done: {len(pages)} master pages, {len(LANGS)} locales")
if __name__=="__main__": main()
