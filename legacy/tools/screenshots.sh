#!/usr/bin/env bash
# Скриншоты страниц целиком через headless Firefox: на десктопе (1440px) и мобильном (390px).
# Headless Firefox снимает только окно, поэтому окно делаем очень высоким, а пустой низ обрезаем.
# Использование: tools/screenshots.sh [базовый URL] [папка] [страницы...]
#   tools/screenshots.sh                                         # оригинал -> screenshots/original
#   tools/screenshots.sh http://localhost:8000 screenshots/static  # локальная копия
set -euo pipefail
cd "$(dirname "$0")/.."
BASE=${1:-http://design-vastu.ru}
OUT=$(realpath -m "${2:-screenshots/original}")
PAGES=(index obo-mne uslugi services galereya poleznye-stati contacts)
PROFILE=$(mktemp -d)
trap 'rm -rf "$PROFILE"' EXIT
[[ $# -gt 2 ]] && PAGES=("${@:3}")
for page in "${PAGES[@]}"; do
  if [[ $BASE == *design-vastu.ru* ]]; then
    url=$BASE/; [[ $page != index ]] && url=$BASE/$page
  else
    url=$BASE/$page.html
  fi
  for size in desktop:1440,9000 mobile:390,16000; do
    name=${size%%:*}
    mkdir -p "$OUT/$name"
    rm -rf "${PROFILE:?}"/*
    timeout 240 firefox --headless --no-remote --profile "$PROFILE" \
      --window-size="${size#*:}" --screenshot "$OUT/$name/$page.png" "$url" >/dev/null 2>&1 \
      && [[ -s "$OUT/$name/$page.png" ]] && python3 tools/trim_screenshot.py "$OUT/$name/$page.png" && echo "$OUT/$name/$page.png" || echo "не удалось: $url ($name)" >&2
  done
done
