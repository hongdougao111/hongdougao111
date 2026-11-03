# -*- coding: utf-8 -*-
"""生成 GitHub Profile README 用的横幅 PNG（纯本地绘制，不依赖网络）。

设计意图：极简深色渐变 + 柔光 + 同心圆环 + 底部细波纹，左上文字区。
"""
import math
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 360
SS = 2

BG_TOP = (12, 16, 34)
BG_MID = (18, 30, 56)
BG_BOTTOM = (13, 42, 62)
ACCENT = (255, 138, 168)   # 红豆粉
ACCENT2 = (125, 211, 252)  # 浅海蓝


def gradient(w, h, stops):
    """stops: [(pos0..1, (r,g,b)), ...] 已排序。"""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                k = (t - p0) / max(p1 - p0, 1e-6)
                col = tuple(round(c0[j] + (c1[j] - c0[j]) * k) for j in range(3))
                d.line([(0, y), (w, y)], fill=col)
                break
    return img


def radial_glow(w, h, cx, cy, radius, color, strength=1.0):
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 34
    for i in range(steps, 0, -1):
        r = radius * i / steps
        a = int(80 * strength * (1 - i / steps) ** 1.7)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (a,))
    return layer.filter(ImageFilter.GaussianBlur(radius / 12))


def load_font(size, bold=False):
    for path in ([r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\segoeuib.ttf"]
                 if bold else
                 [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\segoeui.ttf"]):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def main():
    w, h = W * SS, H * SS
    img = gradient(w, h, [(0.0, BG_TOP), (0.55, BG_MID), (1.0, BG_BOTTOM)]).convert("RGBA")

    # 两团柔光：右上浅海蓝，左下红豆粉
    img = Image.alpha_composite(img, radial_glow(w, h, w * 0.86, h * 0.06, w * 0.46, ACCENT2, 0.75))
    img = Image.alpha_composite(img, radial_glow(w, h, w * 0.06, h * 1.02, w * 0.34, ACCENT, 0.42))

    d = ImageDraw.Draw(img, "RGBA")

    # 右下角：两枚很淡的大圆，纯氛围，不做同心圆
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    cx, cy = w * 0.88, h * 0.86
    for rr, al in [(250, 26), (345, 13)]:
        r = rr * SS
        od.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACCENT2 + (al,), width=2 * SS)
    img = Image.alpha_composite(img, overlay)
    d = ImageDraw.Draw(img, "RGBA")

    # 漂浮的小光点
    for bx, by, br, al in [(0.72, 0.26, 3.2, 120), (0.81, 0.60, 2.2, 90),
                           (0.665, 0.70, 2.0, 70), (0.94, 0.28, 2.6, 100)]:
        x, y, rr = bx * w, by * h, br * SS
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=ACCENT2 + (al,))

    # —— 底部：两层细波纹 ——
    for k, (yy, alpha, amp) in enumerate([(0.905, 26, 8), (0.965, 15, 11)]):
        pts = []
        for i in range(0, int(w), 6):
            pts.append((i, h * yy + math.sin(i / (128 * SS) + k * 2.1) * amp * SS))
        d.line(pts, fill=ACCENT2 + (alpha,), width=2 * SS)

    # 底边强调条（渐隐）
    for x in range(w):
        t = x / w
        a = int(210 * (0.25 + 0.75 * math.sin(math.pi * t) ** 0.6))
        d.line([(x, h - 4 * SS), (x, h - 1)], fill=ACCENT + (a,))

    # —— 左侧文字 ——
    f_name = load_font(68 * SS, bold=True)
    f_en = load_font(27 * SS)
    f_sub = load_font(24 * SS)
    f_tag = load_font(19 * SS)

    left = 84 * SS

    d.text((left + 3 * SS, 70 * SS + 4 * SS), "红豆糕", font=f_name, fill=(0, 0, 0, 120))
    d.text((left, 70 * SS), "红豆糕", font=f_name, fill=(255, 255, 255, 255))

    d.text((left, 165 * SS), "hongdougao111", font=f_en, fill=ACCENT + (255,))
    en_w = d.textlength("hongdougao111", font=f_en)
    d.line([(left + en_w + 15 * SS, 181 * SS), (left + en_w + 78 * SS, 181 * SS)],
           fill=(255, 255, 255, 66), width=2 * SS)

    d.text((left, 212 * SS), "给 AI 宿主写插件 · DSH & AstrBot", font=f_sub,
           fill=(206, 227, 246, 255))

    tx, ty = left, 262 * SS
    for t in ["JavaScript", "Python", "Node.js", "Astro"]:
        tw = d.textlength(t, font=f_tag)
        pad = 11 * SS
        d.rounded_rectangle([tx, ty, tx + tw + pad * 2, ty + 33 * SS],
                            radius=16 * SS, outline=(255, 255, 255, 54), width=2 * SS)
        d.text((tx + pad, ty + 6 * SS), t, font=f_tag, fill=(192, 214, 236, 225))
        tx += tw + pad * 2 + 9 * SS

    img = img.convert("RGB").resize((W, H), Image.LANCZOS)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "banner.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print("saved:", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
