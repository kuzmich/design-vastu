#!/usr/bin/env python3
"""Проверяет собранный сайт (public/): все локальные ссылки, картинки (включая srcset), стили и якоря
ведут на существующие файлы и id. Запуск после `hugo`: python3 tools/check.py [папка]"""
import os, re, sys, urllib.parse
from html.parser import HTMLParser

PUBLIC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "public")


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        for k in ("href", "src"):
            if a.get(k):
                self.refs.append(a[k])
        for part in (a.get("srcset") or "").split(","):
            if part.strip():
                self.refs.append(part.split()[0])


def target(base_dir, ref):
    path = urllib.parse.unquote(ref.split("#")[0].split("?")[0])
    full = os.path.join(PUBLIC, path.lstrip("/")) if path.startswith("/") else os.path.join(base_dir, path)
    full = os.path.normpath(full)
    return os.path.join(full, "index.html") if os.path.isdir(full) else full


pages, problems = {}, []
for dp, _, fs in os.walk(PUBLIC):
    for fn in fs:
        if fn.endswith(".html"):
            p = Page()
            p.feed(open(os.path.join(dp, fn), encoding="utf-8").read())
            pages[os.path.join(dp, fn)] = p

for path, page in pages.items():
    rel = os.path.relpath(path, PUBLIC)
    for ref in page.refs:
        if ref.startswith(("mailto:", "tel:", "http:", "https:", "//", "data:")):
            continue
        file = path if ref.startswith("#") else target(os.path.dirname(path), ref)
        if not os.path.isfile(file):
            problems.append(f"{rel}: нет файла {ref}")
            continue
        anchor = ref.partition("#")[2]
        if anchor and file.endswith(".html") and anchor not in pages[file].ids:
            problems.append(f"{rel}: нет якоря {ref}")

for dp, _, fs in os.walk(PUBLIC):
    for fn in fs:
        if fn.endswith(".css"):
            css = os.path.join(dp, fn)
            for ref in re.findall(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", open(css, encoding="utf-8").read()):
                if not ref.startswith("data:") and not os.path.isfile(target(dp, ref)):
                    problems.append(f"{os.path.relpath(css, PUBLIC)}: нет файла {ref}")

print(f"Страниц: {len(pages)}, проблем: {len(problems)}")
for p in sorted(set(problems)):
    print("  ", p)
sys.exit(1 if problems else 0)
