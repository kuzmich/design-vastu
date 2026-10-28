#!/usr/bin/env python3
"""Проверяет site/: все локальные ссылки в HTML/CSS ведут на существующие файлы."""
import os, re, sys, urllib.parse
SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site")
ROOT = os.path.dirname(SITE)
try:  # файлы, которых нет и на исходном сайте (их записывает build.py)
    upstream_missing = set(open(os.path.join(ROOT, "raw", "_missing.txt")).read().split())
except OSError:
    upstream_missing = set()
bad, absolute = [], []
for dp, _, fs in os.walk(SITE):
    for fn in fs:
        if not fn.endswith((".html", ".css")):
            continue
        p = os.path.join(dp, fn)
        text = open(p, encoding="utf-8", errors="replace").read()
        if fn.endswith(".html"):
            refs = re.findall(r"""(?:src|href|data-origin-src)=['"]([^'"]*)['"]""", text)
        else:
            refs = [a or b for a, b in re.findall(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)|@import\s+['"]([^'"]+)['"]""", text)]
        for r in refs:
            if not r or r.startswith(("#", "data:", "mailto:", "tel:", "http:", "https:", "//", "javascript:", "popup:")):
                if "design-vastu.ru" in r:
                    absolute.append((p, r))
                continue
            if r.startswith("/"):
                absolute.append((p, r))
                continue
            t = os.path.normpath(os.path.join(dp, urllib.parse.unquote(r.split("#")[0].split("?")[0])))
            if not os.path.isfile(t) and os.path.relpath(t, SITE) not in upstream_missing:
                bad.append((os.path.relpath(p, SITE), r))
for kind, lst in (("Битые ссылки", bad), ("Абсолютные ссылки", absolute)):
    uniq = sorted(set(lst))
    print(f"{kind}: {len(uniq)}")
    for x in uniq[:40]:
        print("  ", *x)
sys.exit(1 if bad or absolute else 0)
