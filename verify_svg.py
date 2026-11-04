# -*- coding: utf-8 -*-
"""校验 stats.svg / langs.svg 的几何合法性，并用同一套坐标画一份 PNG 预览。

沙箱禁止启动浏览器，cairosvg 也不可用；这里改用：
1) 解析 SVG 里所有 rect/text 的坐标，断言不越界；
2) 按相同坐标用 Pillow 重绘一张近似预览，肉眼检查布局与配色。
预览只验证排版，不验证 SVG 解析本身。
"""
import math
import os
import re
import sys
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
NS = "{http://www.w3.org/2000/svg}"

BG_TOP = (0x0C, 0x10, 0x22)
BG_BOT = (0x15, 0x2E, 0x4A)
ACCENT = (0xFF, 0x8A, 0xA8)
ACCENT2 = (0x7D, 0xD3, 0xFC)
TEXT = (0xC6, 0xDE, 0xF5)
MUTED = (0x7A, 0x8C, 0xA6)


def load_font(size, bold=False):
    """按平台挑字体：Windows 用雅黑/微软雅黑，Linux CI 用 Noto/DejaVu。"""
    win = ([r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\segoeuib.ttf"]
           if bold else [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\segoeui.ttf"])
    nix = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold
        else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in win + nix:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def check(svg_path):
    tree = ET.parse(svg_path)
    root = tree.getroot()
    w = int(float(root.get("width")))
    h = int(float(root.get("height")))
    problems = []

    for el in root.iter():
        tag = el.tag.replace(NS, "")
        if tag == "rect":
            x = float(el.get("x", 0)); y = float(el.get("y", 0))
            rw = float(el.get("width", 0)); rh = float(el.get("height", 0))
            if x < -0.01 or y < -0.01:
                problems.append("rect 起点越界: %s" % el.attrib)
            if x + rw > w + 0.01:
                problems.append("rect 右侧溢出 %.1f>%d (x=%.1f w=%.1f)" % (x + rw, w, x, rw))
            if y + rh > h + 0.01:
                problems.append("rect 底部溢出 %.1f>%d (y=%.1f h=%.1f)" % (y + rh, h, y, rh))
        elif tag == "text":
            x = float(el.get("x", 0)); y = float(el.get("y", 0))
            fs = float(el.get("font-size", 12))
            content = "".join(el.itertext())
            # 粗略估算宽度：中文按 1 个字宽，英文按 0.55
            est = sum(fs * (1.0 if ord(c) > 127 else 0.55) for c in content)
            anchor = el.get("text-anchor", "start")
            x0 = x - est if anchor == "end" else x
            if y > h:
                problems.append("text 纵向越界 y=%.1f>%d: %r" % (y, h, content))
            if x0 < -1:
                problems.append("text 左侧溢出 x0=%.1f: %r" % (x0, content))
            if x0 + est > w + 1:
                problems.append("text 右侧溢出 %.1f>%d: %r" % (x0 + est, w, content))
    return w, h, problems


def preview(svg_path, out_path):
    """按 SVG 里的真实坐标，用 Pillow 重绘近似图。"""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    w = int(float(root.get("width")))
    h = int(float(root.get("height")))
    SS = 2
    img = Image.new("RGB", (w * SS, h * SS))
    d = ImageDraw.Draw(img)

    # 背景对角渐变
    for y in range(h * SS):
        for_stop = y / (h * SS - 1)
        col = tuple(round(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * for_stop) for i in range(3))
        d.line([(0, y), (w * SS, y)], fill=col)

    # 底边强调条
    for x in range(w * SS):
        t = x / (w * SS - 1)
        col = tuple(round(ACCENT2[i] + (ACCENT[i] - ACCENT2[i]) * t) for i in range(3))
        d.line([(x, (h - 3) * SS), (x, h * SS)], fill=col)

    # 描边
    d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=14 * SS,
                        outline=(255, 255, 255, 26), width=2)

    for el in root.iter():
        tag = el.tag.replace(NS, "")
        if tag == "rect":
            x = float(el.get("x", 0)) * SS
            y = float(el.get("y", 0)) * SS
            rw = float(el.get("width", 0)) * SS
            rh = float(el.get("height", 0)) * SS
            rx = float(el.get("rx", 0)) * SS
            fill = el.get("fill", "none")
            if fill.startswith("#") and len(fill) == 7:
                rgb = tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
                op = float(el.get("fill-opacity", 1))
                base = img.getpixel((int(x), int(y + rh / 2)))
                rgb = tuple(round(base[i] + (rgb[i] - base[i]) * op) for i in range(3))
                if rw > 0 and rh > 0:
                    d.rounded_rectangle([x, y, x + rw - 1, y + rh - 1], radius=rx, fill=rgb)
        if tag != "text":
            continue
        x = float(el.get("x", 0)) * SS
        y = float(el.get("y", 0)) * SS
        fs = float(el.get("font-size", 12)) * SS
        bold = el.get("font-weight") == "700"
        fill = el.get("fill", "#FFFFFF")
        if fill.startswith("#") and len(fill) == 7:
            rgb = tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
        else:
            rgb = (255, 255, 255)
        content = "".join(el.itertext())
        font = load_font(int(fs), bold=bold)
        anchor = "rm" if el.get("text-anchor") == "end" else "lm"
        try:
            d.text((x, y - fs * 0.36), content, font=font, fill=rgb, anchor=anchor)
        except Exception:
            try:
                d.text((x, y - fs * 0.36), content.encode("ascii", "replace").decode(),
                       font=font, fill=rgb)
            except Exception:
                pass

    img = img.resize((w, h), Image.LANCZOS)
    img.save(out_path)
    return out_path


def main():
    ok = True
    for name in ("stats.svg", "langs.svg"):
        path = os.path.join(ASSETS, name)
        w, h, problems = check(path)
        print("== %s (%dx%d) ==" % (name, w, h))
        if problems:
            ok = False
            for p in problems:
                print("   ! " + p)
        else:
            print("   几何检查通过，无越界")
        out = os.path.join(HERE, "_preview_" + name.replace(".svg", ".png"))
        preview(path, out)
        print("   预览: " + os.path.basename(out))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
