# -*- coding: utf-8 -*-
"""从 GitHub 拉取真实数据，生成风格统一的统计卡片 SVG。

不依赖任何第三方图片服务（github-readme-stats 主站当前返回 503）。
数据源走本机已登录的 gh CLI，避开未认证 API 的限流；
生成的 SVG 直接提交进仓库，由 GitHub 原生渲染。
"""
import json
import os
import subprocess

USER = "hongdougao111"
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

GH = os.environ.get("GH_BIN", r"E:\Apps\GitHub CLI\bin\gh.exe")
GH_HOME = os.environ.get("GH_HOME", r"C:\Users\褚富兴")

# 与 banner 一致的配色
BG_TOP = "#0C1022"
BG_BOT = "#152E4A"
ACCENT = "#FF8AA8"
ACCENT2 = "#7DD3FC"
TEXT = "#C6DEF5"
MUTED = "#7A8CA6"

OUT_FILE = os.path.join(HERE, "_gh_out.txt")
ERR_FILE = os.path.join(HERE, "_gh_err.txt")


def gh_json(args):
    """调用 gh，用临时文件接管输出（沙箱不允许建管道）。"""
    env = dict(os.environ)
    env["HOME"] = GH_HOME
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    with open(OUT_FILE, "w+", encoding="utf-8", errors="replace") as fo, \
         open(ERR_FILE, "w+", encoding="utf-8", errors="replace") as fe:
        proc = subprocess.run([GH] + args, stdout=fo, stderr=fe, text=True, env=env)
        fo.seek(0)
        out = fo.read()
        fe.seek(0)
        err = fe.read()
    if proc.returncode != 0:
        raise RuntimeError("gh failed: %s\n%s" % (" ".join(args[:3]), (out + err)[:400]))
    return json.loads(out) if out.strip() else None


def search_count(q):
    """统计搜索命中数。q 里的空格必须编码成 %20，否则 GitHub 返回 422。"""
    try:
        data = gh_json(["api", "search/issues?q=%s&per_page=1" % q.replace(" ", "%20")])
        return data.get("total_count", 0)
    except Exception as exc:
        print("warn: search_count(%r) failed: %s" % (q, str(exc)[:120]))
        return 0


def fetch():
    user = gh_json(["api", "users/" + USER])
    repos = gh_json(["api", "users/%s/repos?per_page=100&sort=pushed" % USER]) or []
    own = [r for r in repos if not r["fork"] and not r.get("archived")]
    total_stars = sum(r["stargazers_count"] for r in repos)

    # 按语言字节权重近似语言占比，只统计自有仓库
    lang_bytes = {}
    for r in own:
        if not r.get("language"):
            continue
        try:
            langs = gh_json(["api", "repos/%s/%s/languages" % (USER, r["name"])])
        except Exception:
            continue
        for k, v in (langs or {}).items():
            lang_bytes[k] = lang_bytes.get(k, 0) + v

    total_bytes = sum(lang_bytes.values()) or 1
    top_langs = sorted(lang_bytes.items(), key=lambda kv: -kv[1])[:5]

    from datetime import datetime, timezone
    return {
        "name": user.get("name") or USER,
        "login": user["login"],
        "public_repos": user["public_repos"],
        "followers": user["followers"],
        "stars": total_stars,
        "prs": search_count("author:%s type:pr" % USER),
        "issues": search_count("author:%s type:issue" % USER),
        "langs": [(k, v / total_bytes * 100) for k, v in top_langs],
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "own_repos": len(own),
    }


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def defs(w, h):
    return """  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{bg_top}"/>
      <stop offset="100%" stop-color="{bg_bot}"/>
    </linearGradient>
    <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{acc2}"/>
      <stop offset="100%" stop-color="{acc}"/>
    </linearGradient>
    <clipPath id="card"><rect x="0.5" y="0.5" width="{w}" height="{h}" rx="14"/></clipPath>
  </defs>""".format(bg_top=BG_TOP, bg_bot=BG_BOT, acc2=ACCENT2, acc=ACCENT, w=w - 1, h=h - 1)


def frame(w, h, title):
    """卡片外壳：渐变底 + 底部强调条 + 描边 + 标题。"""
    return [
        '<g clip-path="url(#card)">',
        '  <rect x="0.5" y="0.5" width="%d" height="%d" rx="14" fill="url(#bg)"/>' % (w - 1, h - 1),
        '  <rect x="0" y="%d" width="%d" height="3" fill="url(#bar)" opacity="0.85"/>' % (h - 3, w),
        '</g>',
        '<rect x="0.5" y="0.5" width="%d" height="%d" rx="14" fill="none" '
        'stroke="#FFFFFF" stroke-opacity="0.10"/>' % (w - 1, h - 1),
        '<text x="26" y="42" font-family="Segoe UI,Microsoft YaHei,sans-serif" '
        'font-size="16" font-weight="700" fill="#FFFFFF">%s</text>' % esc(title),
    ]


def stats_svg(d):
    w, h = 460, 210
    nums = [("Stars", d["stars"]), ("Repos", d["public_repos"]),
            ("PRs", d["prs"]), ("Issues", d["issues"]), ("Followers", d["followers"])]
    p = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
         'role="img" aria-label="%s 的 GitHub 统计">' % (w, h, w, h, esc(d["name"])),
         defs(w, h)]
    p += frame(w, h, "%s 的 GitHub 统计" % d["name"])
    p.append('<text x="26" y="64" font-family="Segoe UI,sans-serif" font-size="12" '
             'fill="%s">@%s</text>' % (MUTED, esc(d["login"])))
    for i, (label, val) in enumerate(nums):
        x = 26 + (i % 3) * 145
        y = 108 + (i // 3) * 54
        p.append('<text x="%d" y="%d" font-family="Segoe UI,Microsoft YaHei,sans-serif" '
                 'font-size="25" font-weight="700" fill="%s">%s</text>' % (x, y, ACCENT2, val))
        p.append('<text x="%d" y="%d" font-family="Segoe UI,Microsoft YaHei,sans-serif" '
                 'font-size="11" fill="%s" opacity="0.82">%s</text>' % (x, y + 17, TEXT, esc(label)))
    p.append('<text x="%d" y="%d" text-anchor="end" font-family="Segoe UI,sans-serif" '
             'font-size="10" fill="%s">updated %s</text>' % (w - 26, h - 14, MUTED, d["generated"]))
    p.append('</svg>')
    return "\n".join(p)


def langs_svg(d):
    w, h = 460, 210
    p = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
         'role="img" aria-label="常用语言">' % (w, h, w, h),
         defs(w, h)]
    p += frame(w, h, "常用语言")
    bar_x, bar_w = 26, w - 52
    y = 76
    for i, (name, pct) in enumerate(d["langs"]):
        p.append('<text x="%d" y="%d" font-family="Segoe UI,Microsoft YaHei,sans-serif" '
                 'font-size="12" fill="%s">%s</text>' % (bar_x, y, TEXT, esc(name)))
        p.append('<text x="%d" y="%d" text-anchor="end" font-family="Segoe UI,sans-serif" '
                 'font-size="12" fill="%s">%.1f%%</text>' % (bar_x + bar_w, y, MUTED, pct))
        p.append('<rect x="%d" y="%d" width="%d" height="5" rx="2.5" fill="#FFFFFF" '
                 'fill-opacity="0.08"/>' % (bar_x, y + 8, bar_w))
        p.append('<rect x="%d" y="%d" width="%.1f" height="5" rx="2.5" fill="%s" '
                 'fill-opacity="0.92"/>' % (bar_x, y + 8, max(bar_w * pct / 100.0, 3),
                                            ACCENT2 if i % 2 == 0 else ACCENT))
        y += 31
    p.append('</svg>')
    return "\n".join(p)


def main():
    data = fetch()
    os.makedirs(ASSETS, exist_ok=True)
    for fname, svg in (("stats.svg", stats_svg(data)), ("langs.svg", langs_svg(data))):
        path = os.path.join(ASSETS, fname)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        print("wrote", fname, len(svg), "bytes")
    for tmp in (OUT_FILE, ERR_FILE):
        if os.path.exists(tmp):
            os.remove(tmp)
    print(json.dumps({k: v for k, v in data.items() if k != "langs"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
