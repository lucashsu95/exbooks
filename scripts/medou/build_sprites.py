"""米豆 MeDou 精靈圖建置腳本。

把 docs/assets/medou/s0.png … s7.png（業主核可的參考圖，放大過的像素畫）
還原成真正的像素格、去背、補出眨眼／閉嘴兩張衍生影格，輸出一張水平
排列的索引色 PNG：static/img/medou/medou-sheet.png。

用法（在 repo 根目錄）：

    uv run python scripts/medou/build_sprites.py            # 產生精靈圖
    uv run python scripts/medou/build_sprites.py --preview  # 另存 10× 預覽到 /tmp

影格順序（pixel-pet.js 的 FRAMES 依此索引，改動時兩邊要一起改）：

    0 idle        s0 正面坐姿
    1 idle-blink  s0 衍生：閉眼
    2 thinking    s1 歪頭、手托下巴、「?」
    3 talking     s2 側身張嘴、「…」對話框
    4 talking-shut s2 衍生：嘴巴闔上
    5 error       s3 >< 眼、紅色「!」、汗滴
    6 sleep       s4 趴睡、Zzz
    7 hover       s5 眨眼、游標箭頭（點我）
    8 notify      s6 側眼、黃色閃光
    9 cheer       s7 ^^ 眼、舉手、星星

只依賴 Pillow（專案已有），不需要 numpy。
"""

from __future__ import annotations

import argparse
import math
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "docs" / "assets" / "medou"
OUT = ROOT / "static" / "img" / "medou" / "medou-sheet.png"

# 參考圖的有限色盤（代號 → RGB）。取樣後一律量化到最接近的一色。
PALETTE = {
    "K": (0, 38, 46),  # 最深：眼睛、外框
    "d": (0, 96, 92),  # 深青描邊
    "m": (0, 152, 142),  # 中青陰影
    "o": (24, 204, 186),  # 身體
    "l": (72, 216, 198),  # 亮青高光
    "c": (104, 216, 248),  # 青色腮紅
    "w": (255, 255, 255),  # 白：口鼻、胸毛、背景
    "g": (222, 238, 238),  # 淺灰：外緣暈邊、地面陰影
    "y": (248, 198, 80),  # 黃：星星、閃光
    "r": (248, 96, 96),  # 紅：舌頭、驚嘆號
}
# 與畫面邊緣連通的這些顏色視為背景（含暈邊與地面陰影），轉成透明
BACKGROUND = {"w", "g"}
TRANSPARENT = "."

# 來源檔 → 狀態；衍生影格在 build() 裡處理
SOURCES = ["s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7"]
FRAME_ORDER = [
    ("idle", "s0", None),
    ("idle-blink", "s0", "blink"),
    ("thinking", "s1", None),
    ("talking", "s2", None),
    ("talking-shut", "s2", "shut"),
    ("error", "s3", None),
    ("sleep", "s4", None),
    ("hover", "s5", None),
    ("notify", "s6", None),
    ("cheer", "s7", None),
]


def detect_pitch(img: Image.Image) -> tuple[int, int, int]:
    """偵測放大倍率（一個像素畫格子幾 px）與格線起點。

    逐列／逐行找顏色變化的位置，相鄰變化的間距取最大公因數就是格寬；
    起點取變化位置對格寬的餘數眾數。
    """
    w, h = img.size
    px = img.load()

    def runs(length, get):
        edges = [i for i in range(1, length) if get(i) != get(i - 1)]
        return edges

    gaps: Counter[int] = Counter()
    offsets: Counter[int] = Counter()
    for y in range(0, h, max(1, h // 64)):
        edges = runs(w, lambda x, y=y: px[x, y])
        for a, b in zip(edges, edges[1:], strict=False):
            gaps[b - a] += 1
        offsets.update(edges)
    for x in range(0, w, max(1, w // 64)):
        edges = runs(h, lambda y, x=x: px[x, y])
        for a, b in zip(edges, edges[1:], strict=False):
            gaps[b - a] += 1
        offsets.update(edges)

    # 只看常見的間距，避免偶發雜訊把 gcd 拉成 1
    common = [g for g, n in gaps.most_common(8) if g > 1]
    pitch = 0
    for g in common:
        pitch = math.gcd(pitch, g)
    if pitch < 2:
        raise SystemExit("偵測不到像素格，來源圖可能不是整數倍放大")
    off = Counter({k: 0 for k in range(pitch)})
    for e, n in offsets.items():
        off[e % pitch] += n
    origin = off.most_common(1)[0][0]
    return pitch, origin, origin


def nearest(rgb: tuple[int, int, int]) -> str:
    return min(PALETTE, key=lambda k: sum((a - b) ** 2 for a, b in zip(PALETTE[k], rgb, strict=True)))


def downsample(path: Path) -> list[list[str]]:
    img = Image.open(path).convert("RGB")
    pitch, ox, oy = detect_pitch(img)
    px = img.load()
    w, h = img.size
    cols = (w - ox) // pitch
    rows = (h - oy) // pitch
    half = pitch // 2
    grid = [[nearest(px[ox + x * pitch + half, oy + y * pitch + half]) for x in range(cols)] for y in range(rows)]
    print(f"  {path.name}: {w}×{h}px，格寬 {pitch}px → {cols}×{rows}")
    return grid


def remove_background(grid: list[list[str]]) -> list[list[str]]:
    """從邊緣做 4 連通 flood fill，把連到外面的白／淺灰變透明。

    被描邊包住的白（口鼻、胸毛、對話框內部）不會被碰到。
    """
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if not (0 <= x < w and 0 <= y < h) or out[y][x] not in BACKGROUND:
            continue
        out[y][x] = TRANSPARENT
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return out


def paint(grid: list[list[str]], rows: dict[int, str], x0: int) -> None:
    """以字串覆寫某幾列：字元 '_' 表示保留原像素。"""
    for y, s in rows.items():
        for i, ch in enumerate(s):
            if ch != "_":
                grid[y][x0 + i] = ch


def blink(grid: list[list[str]]) -> list[list[str]]:
    """s0 → 閉眼：眼睛連同眼窩陰影（第 16–22 列）抹成身體色，
    畫一條跟 s4 睡姿同風格的下彎眼線。"""
    g = [row[:] for row in grid]
    closed = {
        16: "_ooo__",
        17: "oooooo",
        18: "oooooo",
        19: "oooooo",
        20: "odoodo",
        21: "_KKKK_",
        22: "_oooo_",
    }
    paint(g, closed, 14)  # 左眼 x 15–18（含兩側眼窩 14、19）
    paint(g, closed, 30)  # 右眼 x 31–34（含兩側眼窩 30、35）
    return g


def shut_mouth(grid: list[list[str]]) -> list[list[str]]:
    """s2 → 閉嘴：保留上唇線（第 29 列），舌頭與口腔（30–32 列）補回白色口鼻。"""
    g = [row[:] for row in grid]
    paint(
        g,
        {
            30: "wwwww",
            31: "wwwww",
            32: "_www_",
        },
        17,
    )
    return g


def bbox(grid: list[list[str]]) -> tuple[int, int, int, int]:
    xs = [x for row in grid for x, c in enumerate(row) if c != TRANSPARENT]
    ys = [y for y, row in enumerate(grid) for c in row if c != TRANSPARENT]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def build(preview: bool = False) -> None:
    print("讀取來源圖…")
    base = {name: remove_background(downsample(SRC_DIR / f"{name}.png")) for name in SOURCES}
    derive = {None: lambda g: g, "blink": blink, "shut": shut_mouth}
    frames = [(state, derive[op](base[src])) for state, src, op in FRAME_ORDER]

    # 共用正方形畫布：水平保留原圖相對位置（取所有影格的聯集），垂直以底部（腳）對齊
    boxes = [bbox(g) for _, g in frames]
    ux0 = min(b[0] for b in boxes)
    ux1 = max(b[2] for b in boxes)
    tallest = max(b[3] - b[1] for b in boxes)
    size = max(ux1 - ux0, tallest)
    size += size % 2  # 取偶數，方便 CSS 以整數倍縮放時置中
    pad_x = (size - (ux1 - ux0)) // 2

    keys = [TRANSPARENT, *PALETTE]
    sheet = Image.new("P", (size * len(frames), size), 0)
    flat = [0, 0, 0]
    for k in keys[1:]:
        flat.extend(PALETTE[k])
    sheet.putpalette(flat)
    spx = sheet.load()
    for i, (state, g) in enumerate(frames):
        x0, y0, x1, y1 = boxes[i]
        dx = i * size + pad_x - ux0
        dy = size - y1  # 底部對齊
        for y in range(y0, y1):
            for x in range(x0, x1):
                c = g[y][x]
                if c != TRANSPARENT:
                    spx[x + dx, y + dy] = keys.index(c)
        print(f"  影格 {i}: {state}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT, transparency=0, optimize=True)
    print(f"輸出 {OUT.relative_to(ROOT)}：{len(frames)} 影格 × {size}×{size}px，{OUT.stat().st_size} bytes")

    if preview:
        scale = 10
        sheet.info["transparency"] = 0
        rgba = sheet.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (236, 72, 153, 255))  # 洋紅底，方便看出殘留暈邊
        bg.alpha_composite(rgba)
        big = bg.resize((rgba.width * scale, rgba.height * scale), Image.NEAREST)
        dst = Path("/tmp/medou-sheet-preview.png")
        big.save(dst)
        dark = Image.new("RGBA", rgba.size, (15, 23, 42, 255))
        dark.alpha_composite(rgba)
        dark.resize((rgba.width * 4, rgba.height * 4), Image.NEAREST).save("/tmp/medou-sheet-dark.png")
        print(f"預覽 {dst}、/tmp/medou-sheet-dark.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preview", action="store_true", help="另存放大預覽到 /tmp")
    build(preview=ap.parse_args().preview)
