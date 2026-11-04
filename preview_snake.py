# -*- coding: utf-8 -*-
"""把 snake.svg 渲染成 PNG 静态预览，用于肉眼检查网格与蛇的位置。

沙箱里无法启动浏览器、cairosvg 也装不上，所以直接按几何数据重绘。
只为检查布局，不追求与 SVG 逐像素一致。
"""
import os
import re

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
CELL, GAP = 11, 3
STEP = CELL + GAP


def load_svg(path):
    s = open(path, encoding="utf-8").read()

    # 贡献格现在按 <g fill="..."> 分组，每格里是一串 <rect>
    grid = []
    for m in re.finditer(r'<g fill="(#[0-9A-Fa-f]{6})">(.*?)</g>', s, re.S):
        fill, body = m.group(1), m.group(2)
        for rm in re.finditer(r'<rect x="(\d+)" y="(\d+)"', body):
            grid.append((int(rm.group(1)), int(rm.group(2)), fill))

    # 路径定义在 <defs><path id="snakePath" d="..."/>
    pts = []
    pm = re.search(r'<path id="snakePath" d="(M [^"]+)"', s)
    if pm:
        pts = [(float(a), float(b)) for a, b in
               re.findall(r'([\d.]+),([\d.]+)', pm.group(1))]

    return grid, pts, s


def preview(path, out, bg, scale=2):
    grid, pts, s = load_svg(path)
    if not grid:
        print("!! %s 没解析到贡献格" % os.path.basename(path))
        return
    xs = [g[0] for g in grid]
    ys = [g[1] for g in grid]
    gw, gh = max(xs) + CELL, max(ys) + CELL
    pad = CELL * 2
    W, H = gw + pad * 2, gh + pad * 2

    img = Image.new("RGB", (W * scale, H * scale), bg)
    d = ImageDraw.Draw(img)

    for x, y, fill in grid:
        px = (pad + x) * scale
        py = (pad + y) * scale
        d.rounded_rectangle([px, py, px + CELL * scale - 1, py + CELL * scale - 1],
                            radius=2 * scale, fill=fill)

    # 蛇：取路径 42% 处作为代表位置
    if pts:
        idx = int(len(pts) * 0.42)
        for k in range(10):
            j = max(0, min(len(pts) - 1, idx - k))
            t = (9 - k) / 9.0
            px = (pad + pts[j][0]) * scale
            py = (pad + pts[j][1]) * scale
            r = (2.9 + 1.4 * t) * scale
            d.ellipse([px - r, py - r, px + r, py + r], fill="#40C463")
        hx = (pad + pts[idx][0]) * scale
        hy = (pad + pts[idx][1]) * scale
        r = 4.8 * scale
        d.ellipse([hx - r, hy - r, hx + r, hy + r], fill="#216E39")
        for dx in (-1.7, 1.7):
            ex, ey = hx + dx * scale, hy - 1.5 * scale
            er = 1.1 * scale
            d.ellipse([ex - er, ey - er, ex + er, ey + er], fill="#FFFFFF")

    img.save(out)
    animated = "<animateMotion" in s and "<mpath" in s
    print("%s: %dx%d, %d 格, %d 路径点, 动画=%s"
          % (os.path.basename(out), W, H, len(grid), len(pts), animated))


def main():
    preview(os.path.join(HERE, "assets", "snake.svg"),
            os.path.join(HERE, "_preview_snake_light.png"), (255, 255, 255))
    preview(os.path.join(HERE, "assets", "snake-dark.svg"),
            os.path.join(HERE, "_preview_snake_dark.png"), (13, 17, 23))


if __name__ == "__main__":
    main()
