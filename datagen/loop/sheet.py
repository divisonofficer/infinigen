"""python sheet.py OUT.jpg TAG[:LABEL] ...  -- per scene one row: 3 wide + 3 close views, then the same 6 in clay (if rendered)."""
import os, sys
from PIL import Image, ImageDraw
O = "/tmp/claude-0/objreal"; out = sys.argv[1]; specs = [a.split(":") for a in sys.argv[2:]]
W, H = 300, 225
rows = []
for spec in specs:
    tag, lab = spec[0], (spec[1] if len(spec) > 1 else spec[0])
    names = sorted(f for f in os.listdir(f"{O}/rv_{tag}") if f.endswith(".png"))
    pick = [n for n in names if "wide" in n][:3] + [n for n in names if "wide" not in n][:3]
    rows.append((tag, lab, pick, ""))
    if os.path.isdir(f"{O}/rv_{tag}_clay"):
        rows.append((tag + "_clay", lab + " (clay)", [n for n in pick if os.path.exists(f"{O}/rv_{tag}_clay/{n}")], "_clay"))
sheet = Image.new("RGB", (W * 6, (H + 18) * len(rows)), "white"); d = ImageDraw.Draw(sheet)
for r, (tag, lab, pick, _) in enumerate(rows):
    for i, n in enumerate(pick):
        x, y = i * W, r * (H + 18)
        sheet.paste(Image.open(f"{O}/rv_{tag}/{n}").convert("RGB").resize((W, H)), (x, y + 18)); d.text((x + 4, y + 3), f"{lab} | {n[:-4][:22]}", fill="black")
sheet.save(out, quality=85); print(out)
