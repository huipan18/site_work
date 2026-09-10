#!/usr/bin/env python3
"""One-command localization pipeline: extract -> translate -> build -> validate."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--provider', choices=['local-commercial','google'], default='local-commercial')
    ap.add_argument('--device', choices=['auto','cpu','cuda','mps'], default='auto')
    ap.add_argument('--batch-size', type=int, default=8)
    ap.add_argument('--max-chars', type=int, default=2200)
    ap.add_argument('--max-new-tokens', type=int, default=384)
    ap.add_argument('--delay', type=float, default=0.0)
    ap.add_argument('--retries', type=int, default=6)
    ap.add_argument('--skip-translate', action='store_true')
    args = ap.parse_args()

    run(ROOT/'extract_translations.py')
    if not args.skip_translate:
        run(
            ROOT/'translate_missing.py', '--all', '--provider', args.provider,
            '--device', args.device, '--batch-size', str(args.batch_size),
            '--max-chars', str(args.max_chars), '--max-new-tokens', str(args.max_new_tokens),
            '--delay', str(args.delay), '--retries', str(args.retries),
        )
    run(ROOT/'build_locales.py')
    run(ROOT/'validate_locales.py')
    print('Multilingual production build complete.')

if __name__ == '__main__':
    main()
