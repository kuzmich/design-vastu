# design-vastu.ru — статическая версия

> Это старый вариант: статическая копия сайта с конструктора Megagroup. Актуальный сайт (Hugo + Pages CMS) лежит в корне репозитория, см. `../README.md`.

Копия сайта http://design-vastu.ru/ (конструктор Megagroup), собранная в обычные статические файлы.
Готовый сайт лежит в `site/`, его и нужно публиковать.

## Локальный просмотр

```sh
cd site
python3 -m http.server 8000
```

Открыть http://localhost:8000/

## Пересборка

```sh
python3 tools/build.py   # скачивает сайт (кеш в raw/) и собирает site/
python3 tools/check.py   # проверяет, что все локальные ссылки ведут на существующие файлы
```

Чтобы скачать всё заново, удалите `raw/`.

## Скриншоты

В `screenshots/original/{desktop,mobile}/` лежат снимки страниц оригинального сайта целиком
(ширина 1440 и 390 px). Переснять (нужен Firefox и Pillow):

```sh
tools/screenshots.sh                                            # оригинал -> screenshots/original
tools/screenshots.sh http://localhost:8000 screenshots/static   # локальная копия (сервер запущен из site/)
```

## Что изменено по сравнению с оригиналом

- Страницы лежат плоско: `index.html`, `obo-mne.html`, `uslugi.html`, `services.html`, `galereya.html`,
  `poleznye-stati.html`, `contacts.html`, а также `policy.html` и `agreement.html` (политика и пользовательское
  соглашение, `/user/policy` и `/user/agreement`; ссылок на них со страниц сейчас нет). Все ссылки относительные, поэтому сайт работает и в корне домена,
  и в подпапке (например, `username.github.io/repo/`).
- Формы заявок (без сервера Megagroup они не работают) заменены кнопками Telegram / WhatsApp / E-mail.
  Контакты задаются в `CONTACTS` в `tools/build.py`.
- Удалены счётчик и служебные скрипты Megagroup (`main.min.js`, `defender.min.js`, `megacounter`, `$ite.start`)
  и ссылка «сделать сайт в megagroup.ru» в подвале. Ссылки на `/user/agreement` ведут на `agreement.html`,
  а хлебная крошка на служебный раздел `/user` оставлена обычным текстом.
- На внутренних страницах в шапке и подвале были контакты-заглушки шаблона (`+7 (000) 000-00-00`, `mail@company.ru`,
  «г. Москва, Ленинский пр.» и пустые ссылки на телефон, почту и мессенджеры) — они заменены настоящими,
  как на главной (`PLACEHOLDERS` в `tools/build.py`; ссылки берутся у элемента с тем же id на главной).
- Модули, которые скрипты подгружают динамически (`do.*.js`, `g/basestyle/.../__modules`, lightgallery),
  скачаны заранее, а пути к ним сделаны относительными.

## Публикация на GitHub Pages

Опубликовать содержимое `site/`, например через GitHub Actions (`actions/upload-pages-artifact` с `path: site`)
или скопировав `site/` в ветку `gh-pages`. Файл `.nojekyll` уже лежит в `site/`.
Для своего домена добавьте `site/CNAME` с текстом `design-vastu.ru` и настройте DNS.
