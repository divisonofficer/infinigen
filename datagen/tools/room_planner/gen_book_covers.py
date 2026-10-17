"""Synthetic book-cover atlases for the underground bookstore (design proposal docs/bookstore_underground_design_proposal.md).

Real covers, publishers and brands are NOT reproduced: titles are invented generic phrases, the 'publishers' are made-up imprints, the art is
geometric. One atlas = 8 x 5 cover tiles (256 x 384) on top and one band of 31 spine tiles (64 x 384, vertical title) + one plain cream tile at the
bottom, 2048 x 2304 px. proc_bookstore maps box-mesh books onto it by tile index.

    python3 gen_book_covers.py [out_dir] [n_atlases]       # default data/venue_refs/book_atlas, 4 atlases (seeded, deterministic)
    python3 gen_book_covers.py --signs                      # also the section sign images (data/venue_refs/book_signs)
Pure PIL; Korean glyphs from WenQuanYi Zen Hei when present, else Latin text only.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/jarvis/project/robomituba")
OUT = ROOT / "data/venue_refs/book_atlas"
SIGNS = ROOT / "data/venue_refs/book_signs"
CW, CH, COLS, ROWS = 256, 384, 8, 5
SW = 64
ATLAS_W, ATLAS_H = COLS * CW, ROWS * CH + CH            # 2048 x 2304
N_COVERS, N_SPINES = COLS * ROWS, 31                    # the last band slot (index 31) is the plain cream tile
CREAM = (238, 230, 214)
KO = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
LATIN_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

EN_TITLES = ["Daily Table", "English in 100 Days", "Test Practice Vol. 3", "A Quiet Forest", "Travel Notes", "Morning Run", "Small Habits",
             "The Home Kitchen", "Grammar Basics", "City Walks", "Calm Mind", "Weekend Baking", "Ten Minute Math", "Garden Year", "Reading Lab",
             "Words that Stay", "Light Lunch", "Plan Your Year", "Sound of Rain", "Pocket Atlas", "Night Train", "Paper Houses", "First Steps",
             "Salt and Fire", "Coffee Maps", "Blue Hour", "Soft Landing", "Vocabulary 2500", "Everyday Speaking", "Seasons"]
KO_TITLES = ["오늘의 식탁", "하루 한 장", "작은 습관", "여행의 기록", "조용한 숲", "맛있는 집밥", "기초 문법", "아침 달리기", "마음 챙김", "주말 베이킹",
             "도시 산책", "열 개의 문장", "한 달 영어", "계절의 맛", "느린 하루", "첫 번째 걸음"]
IMPRINTS = ["Hana Books", "Maru Press", "Dalbit", "North Leaf", "Sora House", "Bluebird", "Ink & Oak", "Nari"]
PALETTES = [((233, 88, 62), (250, 236, 220)), ((38, 70, 83), (244, 162, 97)), ((42, 157, 143), (255, 247, 230)), ((233, 196, 106), (38, 38, 54)),
            ((120, 90, 160), (245, 240, 250)), ((200, 60, 80), (252, 240, 230)), ((30, 30, 36), (230, 200, 90)), ((90, 150, 210), (255, 255, 255)),
            ((245, 235, 220), (60, 90, 70)), ((250, 190, 190), (90, 40, 60)), ((60, 120, 80), (250, 240, 200)), ((255, 213, 79), (50, 50, 50)),
            ((20, 60, 110), (240, 240, 240)), ((230, 120, 40), (30, 40, 60)), ((210, 225, 210), (40, 80, 60)), ((60, 60, 70), (250, 100, 120))]


def font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except OSError:
        return ImageFont.load_default()


def title_font(korean, size):
    return font(KO, size) if korean and Path(KO).exists() else font(LATIN_B, size)


def wrap(draw, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    if len(words) == 1 and len(text) > 6:                    # Korean phrases have spaces; single long tokens are cut
        words = [text[i:i + 6] for i in range(0, len(text), 6)]
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines


def make_cover(rng, title, korean):
    bg, fg = rng.choice(PALETTES)
    im = Image.new("RGB", (CW, CH), bg); d = ImageDraw.Draw(im)
    style = rng.randrange(5)
    if style == 0:                                          # solid + a big disc (cookbook plate)
        r = rng.randint(70, 95); cx, cy = CW // 2, rng.randint(230, 270)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fg); d.ellipse((cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2), fill=rng.choice(PALETTES)[0])
    elif style == 1:                                        # horizontal stripes
        for k in range(rng.randint(4, 8)):
            y = 170 + k * 26; d.rectangle((0, y, CW, y + 12), fill=fg)
    elif style == 2:                                        # grid of squares (workbook)
        s = 32
        for gx in range(0, CW, s):
            for gy in range(190, CH, s):
                if rng.random() < 0.55:
                    d.rectangle((gx + 2, gy + 2, gx + s - 2, gy + s - 2), fill=rng.choice((fg, rng.choice(PALETTES)[0])))
    elif style == 3:                                        # sun over hills
        d.ellipse((150, 190, 220, 260), fill=fg)
        d.polygon([(0, CH), (0, 300), (90, 250), (170, 310), (256, CH)], fill=rng.choice(PALETTES)[0])
        d.polygon([(0, CH), (80, 330), (180, 290), (256, 340), (256, CH)], fill=fg)
    else:                                                   # border frame
        d.rectangle((14, 14, CW - 14, CH - 14), outline=fg, width=5)
    f = title_font(korean, 34 if korean else 30)
    lines = wrap(d, title, f, CW - 40); y = 34
    for ln in lines[:3]:
        d.text((20, y), ln, font=f, fill=fg if style != 3 else fg); y += int(f.size * 1.2)
    d.text((20, CH - 36), rng.choice(IMPRINTS), font=font(LATIN, 14), fill=fg)
    return im


def make_spine(rng, title, bg, fg, korean):
    im = Image.new("RGB", (SW, CH), bg); d = ImageDraw.Draw(im)
    f = title_font(korean, 26 if korean else 22)
    t = Image.new("RGBA", (CH, SW), (0, 0, 0, 0)); td = ImageDraw.Draw(t)
    td.text((12, (SW - f.size) // 2 - 2), title[:22], font=f, fill=fg)
    im.paste(t.rotate(-90, expand=True), (0, 0), t.rotate(-90, expand=True))
    d.rectangle((0, CH - 46, SW, CH - 40), fill=fg)
    d.ellipse((SW // 2 - 9, CH - 30, SW // 2 + 9, CH - 12), outline=fg, width=2)
    return im


def make_atlas(seed):
    rng = random.Random(seed)
    atlas = Image.new("RGB", (ATLAS_W, ATLAS_H), CREAM)
    spines = []
    for i in range(N_COVERS):
        korean = rng.random() < 0.4
        title = rng.choice(KO_TITLES if korean else EN_TITLES)
        c = make_cover(rng, title, korean)
        atlas.paste(c, ((i % COLS) * CW, (i // COLS) * CH))
        bg = c.getpixel((6, 6)); fg = c.getpixel((CW - 8, CH - 8)) if sum(abs(a - b) for a, b in zip(bg, c.getpixel((CW - 8, CH - 8)))) > 150 else (250, 250, 250)
        if i < N_SPINES:
            atlas.paste(make_spine(rng, title, bg, fg, korean), (i * SW, ROWS * CH))
    return atlas


def make_sign(code, label, path):
    im = Image.new("RGB", (512, 400), (20, 20, 22)); d = ImageDraw.Draw(im)
    d.text((256, 150), code, font=font(LATIN_B, 150), fill=(245, 245, 245), anchor="mm")
    korean = any(ord(ch) > 0x2E80 for ch in label)
    d.text((256, 300), label, font=title_font(korean, 54), fill=(235, 235, 235), anchor="mm")
    im.save(path)


def main():
    a = sys.argv[1:]
    out = Path(next((x for x in a if not x.startswith("--") and not x.isdigit()), OUT)); n = int(next((x for x in a if x.isdigit()), 4))
    out.mkdir(parents=True, exist_ok=True)
    for k in range(n):
        make_atlas(1000 + k).save(out / f"atlas_{k}.png")
    json.dump({"atlas_w": ATLAS_W, "atlas_h": ATLAS_H, "cover": [CW, CH], "cols": COLS, "rows": ROWS, "spine_w": SW, "n_covers": N_COVERS,
               "n_spines": N_SPINES, "cream_tile": [N_SPINES * SW, ROWS * CH, SW, CH], "n_atlases": n}, open(out / "atlas_meta.json", "w"))
    if "--signs" in a:
        SIGNS.mkdir(parents=True, exist_ok=True)
        for code, label in (("A1", "New Arrivals"), ("B13", "English"), ("C1", "Cooking"), ("C3", "요리"), ("C10", "Calendars"), ("C11", "Hobby / Sports"),
                            ("D2", "Stationery"), ("E1", "Gifts")):
            make_sign(code, label, SIGNS / f"sign_{code}.png")
    print("wrote", n, "atlases to", out)


if __name__ == "__main__":
    main()
