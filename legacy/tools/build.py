#!/usr/bin/env python3
"""Собирает статическую копию design-vastu.ru в папку site/.

Скачанные файлы кешируются в raw/ (удалите её, чтобы скачать заново).
Запуск: python3 tools/build.py
"""
import base64
import mimetypes
import os
import posixpath
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
SITE = os.path.join(ROOT, "site")
BASE = "http://design-vastu.ru"
HOST = "design-vastu.ru"

# путь на сайте -> имя файла в site/
PAGES = {
    "/": "index.html",
    "/obo-mne": "obo-mne.html",
    "/uslugi": "uslugi.html",
    "/services": "services.html",
    "/galereya": "galereya.html",
    "/poleznye-stati": "poleznye-stati.html",
    "/contacts": "contacts.html",
    "/user/policy": "policy.html",
    "/user/agreement": "agreement.html",
}

CONTACTS = [
    ("Telegram", "https://t.me/+79500507815"),
    ("WhatsApp", "https://wa.me/79500507815"),
    ("E-mail", "mailto:nutas1@yandex.ru"),
]

# Префиксы путей, которые считаем ресурсами сайта
ASSET_PREFIXES = ("g", "t", "d", "f", "thumb", "assets", "shared")
ASSET_RE = re.compile(
    r"(?:https?:)?(?://(?:www\.)?design-vastu\.ru)?"
    r"(/(?:%s)/[^'\"()\s<>\\]+)" % "|".join(ASSET_PREFIXES)
)
CSS_URL_RE = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)|@import\s+(['"])([^'"]+)\3""")

missing = set()  # ресурсы, на которые есть ссылки, но которых нет на сайте
absent = set()  # необязательные файлы, которых нет (probe)


def log(*a):
    print(*a, file=sys.stderr)


def fetch(path, probe=False):
    """Скачивает путь сайта (без query) с кешем в raw/. Возвращает bytes или None.
    probe=True — файла может и не быть, это не ошибка."""
    path = path.split("#")[0].split("?")[0]
    local = os.path.join(RAW, urllib.parse.unquote(path).lstrip("/") or "index")
    if path in PAGES:
        local = os.path.join(RAW, "_pages", PAGES[path])
    if os.path.isfile(local):
        with open(local, "rb") as f:
            return f.read()
    if path in missing or path in absent:
        return None
    url = BASE + urllib.parse.quote(urllib.parse.unquote(path), safe="/%:@!$&'()*+,;=-._~")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (static-mirror)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as e:
            if probe and e.code == 404:
                absent.add(path)
                return None
            log(f"  ! {e.code} {path}")
            missing.add(path)
            return None
        except Exception as e:  # сеть: пробуем ещё раз
            log(f"  ! {e} {path} (попытка {attempt + 1})")
            time.sleep(2)
    else:
        missing.add(path)
        return None
    os.makedirs(os.path.dirname(local), exist_ok=True)
    with open(local, "wb") as f:
        f.write(data)
    log(f"  + {path}")
    return data


def local_name(path):
    """Путь сайта -> путь файла относительно site/ (без query, раскодированный)."""
    return urllib.parse.unquote(path.split("#")[0].split("?")[0]).lstrip("/")


def write(rel, data):
    dst = os.path.join(SITE, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    with open(dst, "wb") as f:
        f.write(data)


done_assets = set()


def process_asset(path):
    """Скачивает ресурс в site/; CSS и JS дополнительно разбирает на вложенные ресурсы."""
    path = path.split("#")[0].split("?")[0]
    if path in done_assets:
        return
    done_assets.add(path)
    data = fetch(path)
    if data is None:
        return
    rel = local_name(path)
    if rel.endswith(".css"):
        data = rewrite_css(data.decode("utf-8", "replace"), path).encode("utf-8")
    elif rel.endswith(".js"):
        js = data.decode("utf-8", "replace")
        for m in ASSET_RE.finditer(js):
            p = m.group(1)
            if re.search(r"\.(js|css|png|jpe?g|gif|svg|webp|woff2?|ttf|eot)$", p.split("?")[0]):
                process_asset(p)
        # lightgallery.proxy.to.hs.js подгружает lightgallery по абсолютному пути без расширения:
        # качаем эти файлы и делаем путь относительным к странице (все страницы лежат в корне site/)
        def import_file(m):
            process_asset(f"{m.group(2)}.{m.group(4)}")
            return m.group(0).replace(m.group(1) + m.group(2), m.group(1) + m.group(2).lstrip("/"), 1)

        js = re.sub(r"import_file\((['\"])(/[^'\"]+)\1(,\s*['\"])(js|css)['\"]", import_file, js)
        js = fix_webpack_public_path(js)
        data = js.encode("utf-8")
    write(rel, data)


def fix_webpack_public_path(js):
    """Сборки /g/basestyle/... грузят модули от абсолютного publicPath ("/g/basestyle/1.0.1/").
    Делаем его относительным к странице и заранее качаем все модули и их CSS."""
    m = re.search(r'\b(\w)\.p="(/[^"]+/)"', js)
    if not m or '"./__modules/"' not in js:
        return js
    base = m.group(2)
    queue, seen = re.findall(r"\.e\((\d+)\)", js), set()
    while queue:
        cid = queue.pop()
        if cid in seen:
            continue
        seen.add(cid)
        chunk = base + f"__modules/{cid}-{cid}.js"
        process_asset(chunk)
        css = base + f"__assets/css/{cid}.css"
        if fetch(css, probe=True):
            process_asset(css)
        data = fetch(chunk)
        if data:
            queue += re.findall(r"\.e\((\d+)\)", data.decode("utf-8", "replace"))
    return js[: m.start(2)] + base.lstrip("/") + js[m.end(2) :]


def rewrite_css(css, css_path):
    """Делает ссылки в CSS относительными к самому CSS-файлу и докачивает их."""
    css_dir = posixpath.dirname(css_path)

    def repl(m):
        quote, ref = (m.group(1), m.group(2)) if m.group(2) is not None else (m.group(3), m.group(4))
        ref = ref.strip()
        if ref.startswith(("data:", "#")) or not ref:
            return m.group(0)
        u = urllib.parse.urlsplit(ref)
        if u.netloc and u.netloc.replace("www.", "") != HOST:
            return m.group(0)
        target = u.path if u.path.startswith("/") else posixpath.normpath(posixpath.join(css_dir, u.path))
        process_asset(target)
        new = posixpath.relpath(target, css_dir) + (("#" + u.fragment) if u.fragment else "")
        if m.group(2) is not None:
            return f"url({quote}{new}{quote})"
        return f"@import {quote}{new}{quote}"

    return CSS_URL_RE.sub(repl, css)


# --- HTML ---------------------------------------------------------------------

FORM_RE = re.compile(r"<form\b[^>]*class=\"mosaic-form__form[^\"]*\"[^>]*>.*?</form>", re.S)


def replace_form(m):
    form = m.group(0)
    cls = re.search(r'class="([^"]*)"', form).group(1)
    title = re.search(r'<div id="[^"]*" class="mosaic-form__title[^"]*">.*?</div>', form, re.S)
    btn = re.search(r'<button id="[^"]*" class="(mosaic-form__button[^"]*)"><span id="[^"]*" class="([^"]*)">', form)
    btn_cls, text_cls = (btn.group(1), btn.group(2)) if btn else ("mosaic-form__button", "button__text")
    links = "".join(
        f'<a class="{btn_cls} static-contacts__btn" href="{href}" target="_blank" rel="noopener">'
        f'<span class="{text_cls}"><span class="text-block-wrap-div">{name}</span></span></a>'
        for name, href in CONTACTS
    )
    return (
        f'<div class="{cls} static-contacts">'
        + (title.group(0) if title else "")
        + f'<div class="static-contacts__list">{links}</div></div>'
    )


# Формы из блоков-лендингов (lpc4), например попап «Заказать» на странице услуг
LP_FORM_RE = re.compile(r'<div class="lp-form-tpl" data-lpc-api-url="[^"]*"[^>]*><form\b.*?</form></div>', re.S)


def replace_lp_form(m):
    btn = re.search(r'<button class="([^"]*)"', m.group(0))
    btn_cls = btn.group(1) if btn else "lp-button"
    links = "".join(
        f'<a class="{btn_cls} static-contacts__btn" href="{href}" target="_blank" rel="noopener">{name}</a>'
        for name, href in CONTACTS
    )
    return f'<div class="lp-form-tpl static-contacts"><div class="static-contacts__list">{links}</div></div>'


STATIC_CSS = """<style>
.static-contacts__list{display:flex;flex-wrap:wrap;gap:12px;margin-top:20px}
.static-contacts__btn{display:inline-flex!important;align-items:center;justify-content:center;box-sizing:border-box;
  width:auto!important;min-width:160px;height:auto!important;min-height:48px;margin:0!important;padding:12px 24px!important;
  text-decoration:none!important;position:static!important}
.static-contacts__btn .button__text{position:static!important;margin:0!important}
</style>
"""

MEGAGROUP_SCRIPTS = [
    re.compile(r"<script[^>]*src=\"/assets/site/main(?:/defender)?\.min\.js[^\"]*\"[^>]*>\s*</script>\n?"),
    re.compile(r"<script[^>]*>/\*<!\[CDATA\[\*/\s*var megacounter_key.*?</script>\n?", re.S),
    re.compile(r"<script[^>]*>/\*<!\[CDATA\[\*/\s*\$ite\.start.*?</script>\n?", re.S),
]


# На внутренних страницах шапка и подвал — устаревшая копия шаблона с контактами-заглушками
PLACEHOLDERS = {
    "+7 (000) 000-00-00": "+7 (950) 050-78-15",
    "mail@company.ru": "nutas1@yandex.ru",
    "г. Москва, Ленинский пр., д. 123": "г. Иркутск",
    # незаполненное название сайта в политике и соглашении (/user/policy, /user/agreement)
    "Интернет-сайта ____ ": "Интернет-сайта design-vastu.ru ",
    "Интернет сайте ____ ": "Интернет сайте design-vastu.ru ",
    "Гергиевна": "Георгиевна",  # опечатка в отчестве
}
LINK_RE = re.compile(r"(<a\b[^>]*?href=')([^']*)('[^>]*?id=')([^']+)'")
home_links = {}  # id элемента -> href на главной


def fix_placeholders(html):
    for old, new in PLACEHOLDERS.items():
        html = html.replace(old, new)

    # пустые/заглушечные ссылки берём у элемента с тем же id на главной
    def link(m):
        href = home_links.get(m.group(4))
        if href and m.group(2) in ("", "/", "mailto:"):
            return m.group(1) + href + m.group(3) + m.group(4) + "'"
        return m.group(0)

    return LINK_RE.sub(link, html)


def rewrite_html(html):
    html = fix_placeholders(html)
    # ссылка «сделать сайт в megagroup.ru» в подвале
    html = re.sub(r"<div class='mosaic-mega-copyright[^']*'[^>]*>.*?</div>\n?", "", html, flags=re.S)

    # формы -> кнопки с контактами
    html = FORM_RE.sub(replace_form, html)
    html = LP_FORM_RE.sub(replace_lp_form, html)
    html = html.replace("Введите данные для заказа обратного звонка", "Напишите мне удобным способом")
    html = re.sub(r"\s*data-do-form='[^']*'", "", html)
    html = re.sub(r"<!--noindex--><div id=\"[^\"]*\" class=\"mosaic-form__success.*?<!--/noindex-->", "", html, flags=re.S)
    html = re.sub(r'<script src="/g/s3/misc/form/[^"]*"></script>\n?', "", html)
    for r in MEGAGROUP_SCRIPTS:
        html = r.sub("", html)
    html = html.replace("</head>", STATIC_CSS + "</head>", 1)

    # ссылки на страницы
    def page_link(m):
        attr, q, path, frag = m.group(1), m.group(2), m.group(3), m.group(4) or ""
        target = PAGES.get(path.rstrip("/") or "/")
        if target is None:
            return m.group(0)
        return f"{attr}={q}{target}{frag}{q}"

    html = re.sub(
        r"""(href|data-url)=(['"])(?:https?://(?:www\.)?design-vastu\.ru)?(/[a-z0-9/-]*)(#[^'"]*)?\2""",
        page_link,
        html,
    )
    # страницы Megagroup, которых не будет на статике
    html = re.sub(r"""(href|data-url)=(['"])/demo\2""", r"\1=\2#\2", html)
    # хлебная крошка на раздел /user (на страницах policy/agreement) — оставляем текстом
    html = re.sub(r'<a href="/user"( class="[^"]*")>(.*?)</a>', r"<span\1>\2</span>", html, flags=re.S)

    # url() в CSS-переменных браузер считает относительно CSS-файла, где переменная используется,
    # а не страницы — поэтому такие картинки встраиваем как data: URI
    def css_var_url(m):
        p = m.group(2).strip("'\"")
        data = fetch(p)
        if data is None:
            return m.group(0)
        mime = mimetypes.guess_type(p)[0] or "application/octet-stream"
        return f"{m.group(1)}url(data:{mime};base64,{base64.b64encode(data).decode()})"

    html = re.sub(r"(--[\w-]+:\s*)url\(\s*(['\"]?/[^'\")]+['\"]?)\s*\)", css_var_url, html)

    # ресурсы
    def asset(m):
        p = m.group(1)
        process_asset(p)
        return local_name(p).replace(" ", "%20")

    return ASSET_RE.sub(asset, html)


def main():
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)

    # do.js грузит свои модули сам, относительно своего адреса — качаем их все заранее
    dojs = fetch("/g/s3/mosaic/js/do/do.js")
    if dojs:
        chunk_map = re.search(r'o\.u=n=>"([^"]+)"\+\(\{(.*?)\}\[n\]\|\|n\)\+"([^"]+)"', dojs.decode())
        prefix, names, suffix = chunk_map.groups()
        named = dict(re.findall(r'(\d+):"([^"]+)"', names))
        queue, seen = list(named) + re.findall(r"\.e\((\d+)\)", dojs.decode()), set()
        while queue:
            cid = queue.pop()
            if cid in seen:
                continue
            seen.add(cid)
            path = "/" + prefix + named.get(cid, cid) + suffix
            process_asset(path)
            # модуль может требовать другие модули: t.e(1234)
            chunk = fetch(path)
            if chunk:
                queue += re.findall(r"\.e\((\d+)\)", chunk.decode("utf-8", "replace"))

    home = fetch("/").decode("utf-8")
    home_links.update((m.group(4), m.group(2)) for m in LINK_RE.finditer(home))
    for path, name in PAGES.items():
        log(f"Страница {path} -> {name}")
        html = fetch(path).decode("utf-8")
        write(name, rewrite_html(html))

    shutil.copy(os.path.join(SITE, "index.html"), os.path.join(SITE, "404.html"))
    write(".nojekyll", "")

    with open(os.path.join(RAW, "_missing.txt"), "w") as f:
        f.write("".join(local_name(p) + "\n" for p in sorted(missing)))
    if missing:
        log("\nНет на исходном сайте (%d):" % len(missing))
        for p in sorted(missing):
            log("  " + p)


if __name__ == "__main__":
    main()
