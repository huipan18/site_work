#!/usr/bin/env python3
"""Populate locale catalogs with resumable build-time machine translations.

Default provider: local-commercial
  * facebook/m2m100_418M (MIT) for all requested non-English locales except Telugu
  * Helsinki-NLP/opus-mt-en-dra (Apache-2.0) for Telugu

This avoids the HTTP 429 problem from the unofficial Google endpoint and avoids
non-commercial-only translation models. The deployed website never loads these
models; they are build-time dependencies only.
"""
from __future__ import annotations

import argparse
import gc
import json
import random
import re
import time
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
TDIR = ROOT / "translations"

M2M_MODEL = "facebook/m2m100_418M"
TELUGU_MODEL = "Helsinki-NLP/opus-mt-en-dra"
M2M_LOCALES = {
    "tl", "id", "vi", "th", "my", "ms", "km", "lo", "hi", "ur", "bn",
    "ta", "pa", "ne", "si", "ar", "tr", "sw", "am", "fr", "pt", "es",
    "ru", "kk", "uz", "uk", "zh", "ja",
}
SUPPORTED_LOCALES = M2M_LOCALES | {"te"}

GOOGLE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
GOOGLE_TARGET_MAP = {"tl": "tl", "zh": "zh-CN"}

PROTECTED = [
    "Official Poppo Agency", "VSHOW PTE. LTD.", "Apple App Store", "Google Play",
    "App Store", "Poppo Live", "WhatsApp", "Poppo", "Vone", "LIVE", "HTML",
    "CSS", "JavaScript", "73546256", "+91 78383 17307", "+91-7838317307",
    "invite-poppo.com/fT8SYJ",
]

SELECTOR_LABELS = {
    "English", "Filipino / Tagalog", "Bahasa Indonesia", "Vietnamese", "Thai",
    "Burmese", "Malay", "Khmer", "Lao", "Hindi", "Urdu", "Bangla", "Telugu",
    "Tamil", "Punjabi", "Nepali", "Sinhala", "Arabic", "Turkish", "Swahili",
    "Amharic", "French", "Portuguese", "Spanish", "Russian", "Kazakh", "Uzbek",
    "Ukrainian", "Chinese", "Japanese",
}

URL_EMAIL_RE = re.compile(r"https?://\S+|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")


def protect(text: str, namespace: str = ""):
    stash: list[tuple[str, str]] = []

    def add(term: str) -> str:
        token = f"ZXQP{namespace}{len(stash):03d}PZXQ"
        stash.append((token, term))
        return token

    for term in sorted(PROTECTED, key=len, reverse=True):
        if term in text:
            text = text.replace(term, add(term))
    text = URL_EMAIL_RE.sub(lambda m: add(m.group(0)), text)
    return text, stash


def restore(text: str, stash: list[tuple[str, str]]) -> str:
    for token, term in stash:
        if token in text:
            text = text.replace(token, term)
            continue
        # MT may add separators/spaces inside an opaque placeholder. Match loosely.
        pattern = r"\W*".join(map(re.escape, token))
        text = re.sub(pattern, lambda _m, t=term: t, text, flags=re.I)
    return text.strip()


def is_passthrough(source: str) -> bool:
    if source in PROTECTED or source in SELECTOR_LABELS:
        return True
    if not re.search(r"[A-Za-z]", source):
        return True
    if re.fullmatch(r"(?:html|css|js|url|api|id|otp|live)", source, re.I):
        return True
    if re.fullmatch(r"[A-Z0-9_.:/+\- ]{1,40}", source):
        return True
    return False


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def make_batches(keys: list[str], english: dict[str, str], max_items: int, max_chars: int) -> Iterable[list[str]]:
    batch: list[str] = []
    chars = 0
    for key in keys:
        source = english[key]
        projected = chars + len(source)
        if batch and (len(batch) >= max_items or projected > max_chars):
            yield batch
            batch = []
            chars = 0
        batch.append(key)
        chars += len(source)
    if batch:
        yield batch


class LocalCommercialProvider:
    """Local quota-free translation using commercially permissive model licenses."""
    def __init__(self, device: str, max_new_tokens: int, m2m_model: str, telugu_model: str):
        try:
            import torch
            from transformers import (
                AutoModelForSeq2SeqLM,
                AutoTokenizer,
                M2M100ForConditionalGeneration,
                M2M100Tokenizer,
            )
        except ImportError as exc:
            raise SystemExit(
                "Local translation dependencies are missing.\n\n"
                "Run:\n"
                "  python -m pip install -r requirements-local-translation.txt\n\n"
                "Then run prepare_multilingual.py again."
            ) from exc

        self.torch = torch
        self.AutoModel = AutoModelForSeq2SeqLM
        self.AutoTokenizer = AutoTokenizer
        self.M2MModel = M2M100ForConditionalGeneration
        self.M2MTokenizer = M2M100Tokenizer
        self.max_new_tokens = max_new_tokens
        self.m2m_model_name = m2m_model
        self.telugu_model_name = telugu_model

        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        self.device = device
        self.active = None
        self.tokenizer = None
        self.model = None
        print(f"Local translation device: {self.device}")

    def _unload(self):
        self.tokenizer = None
        self.model = None
        self.active = None
        gc.collect()
        if self.device == "cuda":
            self.torch.cuda.empty_cache()

    def _load_m2m(self):
        if self.active == "m2m":
            return
        self._unload()
        print(f"Loading {self.m2m_model_name} (MIT) ...")
        print("First run downloads the model once; later runs use the Hugging Face cache.")
        self.tokenizer = self.M2MTokenizer.from_pretrained(self.m2m_model_name)
        self.tokenizer.src_lang = "en"
        kwargs = {}
        if self.device == "cuda":
            kwargs["torch_dtype"] = self.torch.float16
        self.model = self.M2MModel.from_pretrained(self.m2m_model_name, **kwargs)
        self.model.to(self.device)
        self.model.eval()
        self.active = "m2m"

    def _load_telugu(self):
        if self.active == "te":
            return
        self._unload()
        print(f"Loading {self.telugu_model_name} (Apache-2.0) for Telugu ...")
        self.tokenizer = self.AutoTokenizer.from_pretrained(self.telugu_model_name)
        kwargs = {}
        if self.device == "cuda":
            kwargs["torch_dtype"] = self.torch.float16
        self.model = self.AutoModel.from_pretrained(self.telugu_model_name, **kwargs)
        self.model.to(self.device)
        self.model.eval()
        self.active = "te"

    def _prepare(self, texts: list[str], namespace: str):
        protected_texts, stashes = [], []
        for i, text in enumerate(texts):
            p, stash = protect(text, f"{namespace}{i:03d}")
            protected_texts.append(p)
            stashes.append(stash)
        return protected_texts, stashes

    def translate(self, texts: list[str], target_locale: str) -> list[str]:
        if target_locale not in SUPPORTED_LOCALES:
            raise RuntimeError(f"Local provider has no mapping for {target_locale}")

        if target_locale == "te":
            self._load_telugu()
            protected, stashes = self._prepare(texts, "T")
            # This multilingual OPUS model requires the sentence-initial target token.
            inputs = [">>tel<< " + x for x in protected]
            encoded = self.tokenizer(
                inputs, return_tensors="pt", padding=True, truncation=True, max_length=512
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}
            with self.torch.inference_mode():
                generated = self.model.generate(
                    **encoded, max_new_tokens=self.max_new_tokens, num_beams=2
                )
        else:
            self._load_m2m()
            protected, stashes = self._prepare(texts, "M")
            self.tokenizer.src_lang = "en"
            encoded = self.tokenizer(
                protected, return_tensors="pt", padding=True, truncation=True, max_length=512
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}
            target_id = self.tokenizer.get_lang_id(target_locale)
            with self.torch.inference_mode():
                generated = self.model.generate(
                    **encoded,
                    forced_bos_token_id=target_id,
                    max_new_tokens=self.max_new_tokens,
                    num_beams=2,
                )

        outputs = self.tokenizer.batch_decode(generated, skip_special_tokens=True)
        return [restore(value, stashes[i]) for i, value in enumerate(outputs)]


class GoogleProvider:
    """Legacy optional provider. Kept only for explicit use; public endpoint may 429."""
    def __init__(self, retries: int, backoff_base: float, backoff_cap: float):
        try:
            import requests
        except ImportError as exc:
            raise SystemExit("requests is required for --provider google") from exc
        self.requests = requests
        self.retries = retries
        self.backoff_base = backoff_base
        self.backoff_cap = backoff_cap
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 Chrome/152", "Accept-Language": "en-US,en;q=0.9"})

    def _one(self, text: str, target: str) -> str:
        p, stash = protect(text, "G")
        params = {"client": "gtx", "sl": "en", "tl": GOOGLE_TARGET_MAP.get(target, target), "dt": "t", "q": p}
        for attempt in range(self.retries + 1):
            r = self.session.get(GOOGLE_ENDPOINT, params=params, timeout=45)
            if r.status_code == 429:
                if attempt >= self.retries:
                    raise RuntimeError("Google public endpoint is still returning HTTP 429. Use the default local-commercial provider.")
                pause = min(self.backoff_cap, self.backoff_base * (2 ** attempt)) + random.uniform(.25, 1.25)
                print(f"  rate limited (429); backing off {pause:.1f}s, retry {attempt+1}/{self.retries}")
                time.sleep(pause)
                continue
            r.raise_for_status()
            data = r.json()
            translated = "".join(x[0] or "" for x in data[0] if x and x[0] is not None)
            return restore(translated, stash)
        raise RuntimeError("Google translation request failed")

    def translate(self, texts: list[str], target_locale: str) -> list[str]:
        return [self._one(text, target_locale) for text in texts]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--locale", action="append", help="locale code; repeatable")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--provider", choices=["local-commercial", "google"], default="local-commercial")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-chars", type=int, default=2200)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--retries", type=int, default=6)
    parser.add_argument("--backoff-base", type=float, default=8.0)
    parser.add_argument("--backoff-cap", type=float, default=120.0)
    parser.add_argument("--m2m-model", default=M2M_MODEL)
    parser.add_argument("--telugu-model", default=TELUGU_MODEL)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    en_path = TDIR / "en.json"
    if not en_path.exists():
        raise SystemExit("translations/en.json is missing; run extract_translations.py first")
    english = json.loads(en_path.read_text(encoding="utf-8"))["strings"]

    locales = args.locale or ([p.stem for p in sorted(TDIR.glob("*.json")) if p.stem != "en"] if args.all else [])
    if not locales:
        raise SystemExit("Use --all or --locale hi --locale fr")

    if args.provider == "local-commercial":
        missing = [x for x in locales if x not in SUPPORTED_LOCALES]
        if missing:
            raise SystemExit(f"Unsupported local translation locale(s): {', '.join(missing)}")
        # Keep Telugu last so the 418M multilingual model is loaded once, then swapped
        # for the smaller Telugu model only after all M2M languages are finished.
        locales = [x for x in locales if x != "te"] + (["te"] if "te" in locales else [])
        provider = LocalCommercialProvider(args.device, args.max_new_tokens, args.m2m_model, args.telugu_model)
    else:
        print("WARNING: Google public endpoint can return HTTP 429. Local-commercial is recommended.")
        provider = GoogleProvider(args.retries, args.backoff_base, args.backoff_cap)

    for loc in locales:
        path = TDIR / f"{loc}.json"
        if not path.exists():
            raise SystemExit(f"Missing translation catalog: {path.name}")
        data = json.loads(path.read_text(encoding="utf-8"))
        strings = data["strings"]

        candidates: list[str] = []
        for key, source in english.items():
            current = str(strings.get(key, "")).strip()
            if args.overwrite or not current:
                if is_passthrough(source):
                    strings[key] = source
                else:
                    candidates.append(key)
        save(path, data)

        print(f"{loc}: {len(candidates)} strings to translate")
        if not candidates:
            print(f"{loc}: complete")
            continue

        batches = list(make_batches(candidates, english, max(1, args.batch_size), max(250, args.max_chars)))
        completed = 0
        for batch_no, keys in enumerate(batches, 1):
            sources = [english[k] for k in keys]
            try:
                values = provider.translate(sources, loc)
            except Exception as exc:
                save(path, data)
                print(f"\n{loc}: stopped after saving {completed}/{len(candidates)} translated strings")
                print(f"Reason: {exc}")
                print("Re-run the same command; completed strings are checkpointed and skipped.")
                raise SystemExit(2) from exc

            if len(values) != len(keys):
                raise SystemExit(f"Internal error: translation batch length mismatch for {loc}")
            for key, value in zip(keys, values):
                strings[key] = value
            completed += len(keys)
            save(path, data)
            print(f"  {completed}/{len(candidates)} (batch {batch_no}/{len(batches)})")
            if args.delay > 0 and batch_no < len(batches):
                time.sleep(args.delay)
        print(f"{loc}: complete")


if __name__ == "__main__":
    main()
