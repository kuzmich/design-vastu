#!/usr/bin/env python3
"""Обрезает однотонную полосу внизу скриншота (окно браузера выше самой страницы).
Края по ширине не учитываются: там бывают элементы, закреплённые внизу окна (кнопка «наверх» и т.п.)."""
import sys
from PIL import Image, ImageChops

for path in sys.argv[1:]:
    im = Image.open(path).convert("RGB")
    margin = im.width // 5
    mid = im.crop((margin, 0, im.width - margin, im.height))
    bg = Image.new("RGB", mid.size, mid.getpixel((0, mid.height - 1)))
    # допуск: почти фоновые пиксели (тени, полупрозрачные закреплённые панели) считаем фоном
    box = ImageChops.difference(mid, bg).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
    if box:
        im.crop((0, 0, im.width, min(im.height, box[3] + 20))).save(path)
