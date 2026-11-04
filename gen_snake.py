# -*- coding: utf-8 -*-
"""本地生成「贪吃蛇吃贡献格」动画 SVG（对标 Platane/snk 的产物）。

为什么要自己写：Platane/snk 需要 GitHub Actions 跑，而当前环境的 token
缺 workflow scope，推不上 .github/workflows/。所以直接本地生成 SVG 提交，
GitHub 对 <img> 里的 SMIL 动画是支持渲染的。

用法: python gen_snake.py
数据源: gh CLI 的 GraphQL contributionCalendar
"""
import json
import os
import subprocess
import tempfile

USER = "hongdougao111"
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

GH = os.environ.get("GH_BIN") or ("gh" if os.name != "nt" else r"E:\Apps\GitHub CLI\bin\gh.exe")
GH_HOME = os.environ.get("GH_HOME", os.path.expanduser("~"))

# GitHub 原生贡献色阶（深色主题下也协调）
LEVELS_LIGHT = ["#EBEDF0", "#9BE9A8", "#40C463", "#30A14E", "#216E39"]
LEVELS_DARK = ["#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"]

CELL = 11          # 格子边长
GAP = 3            # 间隔
STEP = CELL + GAP  # 14
LEFT_PAD = 0
TOP_PAD = 0


def gh_json(args):
    env = dict(os.environ)
    env["HOME"] = GH_HOME
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    fd, out_path = tempfile.mkstemp(suffix=".out", dir=HERE)
    os.close(fd)
    fd, err_path = tempfile.mkstemp(suffix=".err", dir=HERE)
    os.close(fd)
    try:
        with open(out_path, "w+", encoding="utf-8", errors="replace") as fo, \
             open(err_path, "w+", encoding="utf-8", errors="replace") as fe:
            proc = subprocess.run([GH] + args, stdout=fo, stderr=fe, text=True, env=env)
            fo.seek(0)
            out = fo.read()
            fe.seek(0)
            err = fe.read()
    finally:
        for p in (out_path, err_path):
            try:
                os.remove(p)
            except OSError:
                pass
    if proc.returncode != 0:
        raise RuntimeError("gh failed: %s\n%s" % (" ".join(args[:3]), (out + err)[:400]))
    return json.loads(out)


def fetch_calendar():
    q = ('query{user(login:"%s"){contributionsCollection{'
         'contributionCalendar{totalContributions weeks{'
         'contributionDays{contributionCount date weekday}}}}}}' % USER)
    data = gh_json(["api", "graphql", "-f", "query=" + q])
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level_of(count):
    """把贡献次数映射到 0..4 五档。"""
    if count <= 0:
        return 0
    if count <= 3:
        return 1
    if count <= 6:
        return 2
    if count <= 9:
        return 3
    return 4


def build_grid(cal):
    """返回 weeks[col][row] = (count, level)，补齐到 7 行。"""
    weeks = []
    for wk in cal["weeks"]:
        col = [None] * 7
        for day in wk["contributionDays"]:
            col[day["weekday"]] = (day["contributionCount"], level_of(day["contributionCount"]))
        weeks.append([c if c else (0, 0) for c in col])
    return weeks


def snake_path(weeks):
    """蛇形路径：逐列往返扫过所有格子，从左侧进入、右侧穿出。

    只走「有贡献」的列会显得跳跃，所以整片网格都走，像真的在吃。
    """
    ncol = len(weeks)
    pts = []
    mid = 3 * STEP + CELL / 2.0
    # 从左侧外部进入
    pts.append((-STEP * 2, mid))
    for c in range(ncol):
        rows = range(6, -1, -1) if c % 2 == 0 else range(0, 7)
        for r in rows:
            pts.append((c * STEP + CELL / 2.0, r * STEP + CELL / 2.0))
    # 从右侧穿出
    pts.append((ncol * STEP + STEP * 2, mid))
    return pts


def path_d(pts):
    return "M " + " L ".join("%.1f,%.1f" % (x, y) for x, y in pts)


def render(weeks, palette, dark=False, snake_color="#40C463", snake_head="#216E39"):
    ncol = len(weeks)
    w = ncol * STEP - GAP
    h = 7 * STEP - GAP
    pad = CELL * 2
    total_w = w + pad * 2
    total_h = h + pad * 2

    d = path_d(snake_path(weeks))
    DUR = 18  # 秒

    parts = []
    parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
                 'viewBox="0 0 %d %d" role="img" aria-label="贡献记录动画">'
                 % (total_w, total_h, total_w, total_h))
    parts.append('<rect width="100%%" height="100%%" fill="%s"/>'
                 % ("#0D1117" if dark else "#FFFFFF"))

    # 整条路径只写一次，所有元素用 <use> 复用，避免体积爆炸
    parts.append('<defs><path id="snakePath" d="%s"/></defs>' % d)

    parts.append('<g transform="translate(%d,%d)">' % (pad, pad))

    # 贡献格：按档位分组，减少重复属性
    by_level = {}
    for c, col in enumerate(weeks):
        for r, (count, lv) in enumerate(col):
            by_level.setdefault(lv, []).append((c * STEP, r * STEP))
    for lv, cells in sorted(by_level.items()):
        rects = "".join('<rect x="%d" y="%d" width="%d" height="%d" rx="2"/>'
                        % (x, y, CELL, CELL) for x, y in cells)
        parts.append('<g fill="%s">%s</g>' % (palette[lv], rects))

    # 蛇身：用 <use> 引用同一路径，靠负 begin 形成跟随
    body_len = 10
    for i in range(body_len):
        t = i / float(body_len - 1)          # 0 = 尾, 1 = 头
        r = 2.9 + 1.4 * t
        opacity = 0.35 + 0.6 * t
        offset = -0.06 * (body_len - 1 - i)
        parts.append('<circle r="%.2f" fill="%s" opacity="%.2f">'
                     '<animateMotion dur="%ds" repeatCount="indefinite" begin="%.2fs">'
                     '<mpath href="#snakePath"/></animateMotion></circle>'
                     % (r, snake_color, opacity, DUR, offset))

    # 蛇头：带两只眼睛，方向由路径决定
    parts.append('<g><animateMotion dur="%ds" repeatCount="indefinite" '
                 'rotate="auto"><mpath href="#snakePath"/></animateMotion>' % DUR)
    parts.append('<circle r="4.8" fill="%s"/>' % snake_head)
    parts.append('<circle cx="-1.7" cy="-1.5" r="1.1" fill="#FFFFFF"/>')
    parts.append('<circle cx="1.7" cy="-1.5" r="1.1" fill="#FFFFFF"/>')
    parts.append('</g>')

    parts.append('</g>')
    parts.append('</svg>')
    return "\n".join(parts)


def main():
    cal = fetch_calendar()
    weeks = build_grid(cal)
    os.makedirs(ASSETS, exist_ok=True)

    light = render(weeks, LEVELS_LIGHT, dark=False)
    dark = render(weeks, LEVELS_DARK, dark=True,
                  snake_color="#39D353", snake_head="#26A641")

    for name, svg in (("snake.svg", light), ("snake-dark.svg", dark)):
        p = os.path.join(ASSETS, name)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        print("wrote", name, len(svg), "bytes")

    print("total contributions:", cal["totalContributions"], "| weeks:", len(weeks))


if __name__ == "__main__":
    main()
