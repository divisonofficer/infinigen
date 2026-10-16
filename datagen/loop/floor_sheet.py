"""python floor_sheet.py OUT.jpg TAG -- a multi-room floor: one row per room (its wide shots), then a row of close-ups."""
import os, sys, collections
from PIL import Image, ImageDraw
O = "/tmp/claude-0/objreal"; out, tag = sys.argv[1], sys.argv[2]
W, H = 300, 225
names = sorted(f for f in os.listdir(f"{O}/rv_{tag}") if f.endswith(".png"))
rooms = collections.OrderedDict()
for n in names:
    if "_wide" in n:
        rooms.setdefault(n.split("_wide")[0], []).append(n)
rows = [(r, ns[:4]) for r, ns in rooms.items()] + [("close-ups", [n for n in names if n.startswith("c")][:4])]
rows += [(r + " (clay)", [n for n in ns if os.path.exists(f"{O}/rv_{tag}_clay/{n}")]) for r, ns in rows[:-1]][:0]
sheet = Image.new("RGB", (W * 4, (H + 18) * len(rows)), "white"); d = ImageDraw.Draw(sheet)
for r, (lab, ns) in enumerate(rows):
    for i, n in enumerate(ns):
        x, y = i * W, r * (H + 18)
        sheet.paste(Image.open(f"{O}/rv_{tag}/{n}").convert("RGB").resize((W, H)), (x, y + 18)); d.text((x + 4, y + 3), f"{lab} | {n[:-4][:30]}", fill="black")
sheet.save(out, quality=85); print(out, len(rows), "rows")
