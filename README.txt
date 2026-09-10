OFFICIAL POPPO AGENCY — MULTILINGUAL STATIC BUILD
=================================================

WHAT STAYS UNCHANGED
- English pages remain the master source.
- /assets/css/style.css is shared and is not redesigned.
- Images and other shared assets are not duplicated per language.
- Existing English URL paths remain unchanged.
- Arabic and Urdu load only /assets/css/rtl.css in addition to the main stylesheet.

SUPPORTED LOCALES
English plus: tl, id, vi, th, my, ms, km, lo, hi, ur, bn, te, ta, pa, ne, si,
ar, tr, sw, am, fr, pt, es, ru, kk, uz, uk, zh, ja.
Filipino/Tagalog intentionally uses one SEO locale: /tl/.

FIRST-TIME SETUP
python -m pip install -r requirements-build.txt

ONE-COMMAND FULL PREPARATION
python prepare_multilingual.py

This does, in order:
1. Extracts stable translation keys from the English HTML and JavaScript UI text.
2. Fills missing translation strings on a network-connected development machine.
3. Generates every localized static HTML page.
4. Generates self-canonicals, reciprocal hreflang, x-default, localized links and sitemaps.
5. Runs validation and stops with a non-zero exit code if required items are missing.

HOW TO BUILD (after translations already exist)
python build_locales.py

HOW TO VALIDATE
python validate_locales.py

HOW TO UPDATE ENGLISH CONTENT AND REBUILD
1. Edit only the existing English master HTML page(s).
2. Run: python extract_translations.py
3. Run: python translate_missing.py --all
4. Review important translations, especially titles/descriptions/legal/safety/payment wording.
5. Run: python build_locales.py
6. Run: python validate_locales.py

HOW TO ADD / CHANGE A TRANSLATION
1. Open translations/<language-code>.json.
2. Find the stable key whose English source is in translations/en.json.
3. Change only the translated value.
4. Run: python build_locales.py
5. Run: python validate_locales.py

HOW TO ADD A NEW LANGUAGE
1. Add the locale once in LANGS inside build_locales.py and in the validator locale list.
2. Run: python extract_translations.py and create/copy translations/<code>.json.
3. Populate its values.
4. Run the build and validator.

WHICH FOLDER TO UPLOAD TO HOSTINGER
Upload the CONTENTS of this project folder to public_html after a successful build/validation.
The deployed website does not need Python, Node.js, a database, SSR, or a development server.
Python scripts and /translations/ are build-time files; robots.txt prevents them from being crawled.

LANGUAGE URL BEHAVIOR
/agency/ -> English
/hi/agency/ -> Hindi
/ar/agency/ -> Arabic
/ja/agency/ -> Japanese
The language selector stays on the equivalent current page whenever possible.

TRANSLATION QUALITY
translate_missing.py is a bootstrap to fill missing strings. For production publishing, review important
SEO, legal, safety, money, account and onboarding wording with a fluent/native reviewer. Protected
brand names, codes, URLs, email addresses and important identifiers are intentionally preserved.

RATE-LIMIT / HTTP 429 HANDLING
If the translation service returns HTTP 429, the patched translator now:
- sends multiple independent strings per request instead of one request per string
- automatically retries with exponential backoff and jitter
- honours Retry-After when the service provides it
- writes each successful batch to translations/<locale>.json immediately
- safely resumes from the last saved batch if the process is interrupted

Normal command:
python prepare_multilingual.py

More conservative request settings if your network is heavily rate-limited:
python prepare_multilingual.py --delay 2.5 --batch-size 12 --max-chars 1400

To continue translation dictionaries directly without re-running the whole pipeline:
python translate_missing.py --all --delay 2.5 --batch-size 12 --max-chars 1400

After all dictionaries are populated:
python prepare_multilingual.py --skip-translate

IMPORTANT FIX IN THIS PATCH
The extractor/build system now explicitly ignores the HTML doctype. The previous build incorrectly
extracted the word "html" from <!DOCTYPE html> as if it were page copy. That could have damaged a
localized document doctype if it were translated. Language-selector display names are also excluded
from the translation queue because the selector already renders each language from the canonical
language registry.

LOCAL COMMERCIAL-PERMISSIVE TRANSLATION
=======================================
Install once:

  python -m pip install -r requirements-build.txt
  python -m pip install -r requirements-local-translation.txt

Then build:

  python prepare_multilingual.py

This no longer uses the public Google translation endpoint by default. It uses
facebook/m2m100_418M (MIT) locally for supported locales and Helsinki-NLP/opus-mt-en-dra
(Apache-2.0) for Telugu. Model files download once and are cached on the build PC.
Translation JSON files checkpoint after every batch, so rerunning safely resumes.
