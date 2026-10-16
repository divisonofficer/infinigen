"""python floor_sheet.py OUT.jpg TAG -- a multi-room floor: one row per room (its wide shots), then a row of close-ups."""
import os, re, sys, collections
from PIL import Image, ImageDraw
O = "/tmp/claude-0/objreal"; out, tag = sys.argv[1], sys.argv[2]
W, H = 300, 225
names = sorted(f for f in os.listdir(f"{O}/rv_{tag}") if f.endswith(".png"))
rooms = collections.OrderedDict()
for n in names:
    if "_wide" in n:
        rooms.setdefault(n.split("_wide")[0], []).append(n)
close = [n for n in names if re.match(r"c\d+_", n)]      # not "closet_0-0_wide0" (floor F3 r1)               # two rows: a floor has a hero per room (floor I r2: the till was close-up 5,
rows = [(r, ns[:4]) for r, ns in rooms.items()] + [("close-ups", close[:4]), ("close-ups", close[4:8])]   # off the sheet; 3/3 'no checkout')
rows = [(l, ns) for l, ns in rows if ns]
rows += [(r + " (clay)", [n for n in ns if os.path.exists(f"{O}/rv_{tag}_clay/{n}")]) for r, ns in rows[:-1]][:0]
sheet = Image.new("RGB", (W * 4, (H + 18) * len(rows)), "white"); d = ImageDraw.Draw(sheet)
for r, (lab, ns) in enumerate(rows):
    for i, n in enumerate(ns):
        x, y = i * W, r * (H + 18)
        sheet.paste(Image.open(f"{O}/rv_{tag}/{n}").convert("RGB").resize((W, H)), (x, y + 18)); d.text((x + 4, y + 3), f"{lab} | {n[:-4][:30]}", fill="black")
sheet.save(out, quality=85); print(out, len(rows), "rows")
# pages of 4 rows at 400x300: a 9-11 row floor sheet is downscaled twice before a critic sees it, and wall posters, dispensers and
# desk props vanish -- 'no signage, nothing on the walls' about rooms that have five wall items (floor D3 r4, 3 of 3)
PW, PH = 400, 300
for p_, k0 in enumerate(range(0, len(rows), 4), 1):
    chunk = rows[k0:k0 + 4]
    pg = Image.new("RGB", (PW * 4, (PH + 20) * len(chunk)), "white"); dp = ImageDraw.Draw(pg)
    for r, (lab, ns) in enumerate(chunk):
        for i, n in enumerate(ns):
            x, y = i * PW, r * (PH + 20)
            pg.paste(Image.open(f"{O}/rv_{tag}/{n}").convert("RGB").resize((PW, PH)), (x, y + 20)); dp.text((x + 4, y + 4), f"{lab} | {n[:-4][:34]}", fill="black")
    pp = out[:-4] + f"_p{p_}.jpg"; pg.save(pp, quality=88); print(pp)
