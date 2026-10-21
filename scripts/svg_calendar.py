"""生成 SVG 甘特图日历，嵌入 README 顶部。

GitHub README 原生渲染 <img> 引用的 SVG，所以把日历做成 SVG，
README 里写 ![活动日历](docs/calendar.svg) 就能直接显示，不依赖 GitHub Pages。

设计：
- 顶部时间刻度轴
- 每个活动一行横条，长度 = 持续时间占比
- 横条上叠半透明进度填充表示当前完成度
- 红色竖线标记"今天"
- 已结束活动半透明，未开始活动虚线边框
- 左侧活动名，右侧横条
- 底部图例
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import DOCS_DIR, log, parse_date, today_bj, is_long_term


# 画布参数
WIDTH = 940
LEFT_LABEL_W = 240          # 左侧活动名宽度
TRACK_X = LEFT_LABEL_W + 10  # 时间轴起点 x
TRACK_W = WIDTH - TRACK_X - 20  # 时间轴宽度
ROW_H = 28                   # 每行高度
BAR_H = 18                   # 横条高度
TOP_PAD = 70                 # 顶部留给标题+刻度
BOTTOM_PAD = 50              # 底部留给图例
LABEL_TEXT_X = 24            # 活动名文字起点
LABEL_MAX_PX = TRACK_X - LABEL_TEXT_X - 6  # 活动名最大像素宽（超长强制压缩）

# 颜色
COLOR_AI = "#f97316"
COLOR_OPEN_SOURCE = "#16a34a"
COLOR_DRIVE = "#14b8a6"
COLOR_GAMES = "#22c55e"
COLOR_SHOPPING = "#eab308"
COLOR_VIDEO_VIP = "#ec4899"
COLOR_NETDISK_VIP = "#f43f5e"
COLOR_GAME_DISCOUNT = "#8b5cf6"
COLOR_TODAY = "#ef4444"
COLOR_TEXT = "#24292f"
COLOR_TEXT_DIM = "#6e7681"
COLOR_GRID = "#d0d7de"
COLOR_BG = "#ffffff"


def _cat_color(cat: str) -> str:
    return {
        "ai": COLOR_AI,
        "open-source": COLOR_OPEN_SOURCE,
        "drive": COLOR_DRIVE,
        "games": COLOR_GAMES,
        "shopping": COLOR_SHOPPING,
        "video-vip": COLOR_VIDEO_VIP,
        "netdisk-vip": COLOR_NETDISK_VIP,
        "game-discount": COLOR_GAME_DISCOUNT,
    }.get(cat, COLOR_AI)


def _visual_width(s: str) -> float:
    """估算字符串显示宽度（单位 = 全角字符宽）。

    全角（CJK）=1，emoji（U+1F000 起）=1.6，半角 =0.55。
    emoji 实际渲染约 1.5-1.8 个 em，按 1.6 估算更准确。
    """
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o >= 0x1F000:
            w += 1.6
        elif o > 0x2E80:
            w += 1.0
        else:
            w += 0.55
    return w


def _truncate_label(s: str, max_units: float = 16.0) -> str:
    """按显示宽度截断活动名（权重与 _visual_width 一致），超限加省略号。"""
    out: list[str] = []
    w = 0.0
    for ch in s:
        o = ord(ch)
        cw = 1.6 if o >= 0x1F000 else (1.0 if o > 0x2E80 else 0.55)
        if w + cw > max_units - 1.0:  # 留 1 个单位给省略号
            break
        out.append(ch)
        w += cw
    if len(out) < len(s):
        out.append("…")
    return "".join(out)


def _esc(s: str) -> str:
    # 先按显示宽度截断再转义，避免转义实体（&amp; 等）被截断破坏
    return escape(_truncate_label(s))


def _date_to_x(d: date, min_d: date, max_d: date) -> float:
    total = (max_d - min_d).days or 1
    return TRACK_X + ((d - min_d).days / total) * TRACK_W


def generate_svg(activities: list[dict], output_path: Path | None = None) -> Path:
    """生成 SVG 日历并写入文件。返回文件路径。"""
    if output_path is None:
        output_path = DOCS_DIR / "calendar.svg"

    today = today_bj()
    # 当月范围
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)

    # 只排除 open-source（无 end_date，永久免费），显示所有有时间限制的活动
    excluded = [a for a in activities if a.get("category") == "open-source"]
    chart_acts = [a for a in activities if a not in excluded]
    # 有日期的活动（有 start_date 和 end_date）
    dated = [a for a in chart_acts if parse_date(a.get("start_date")) and parse_date(a.get("end_date"))]
    undated = [a for a in chart_acts if a not in dated]

    if not dated:
        # 空状态 SVG
        svg = _empty_svg(today)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(svg, encoding="utf-8")
        log(f"已生成空状态 SVG 日历 ({output_path.name})，当月无限时活动")
        return output_path

    # 时间范围固定为当月（前后各留 1 天边距）
    min_d = month_start - timedelta(days=1)
    max_d = month_end + timedelta(days=1)

    # 按分区分组，分区内按 end_date 升序（快结束的在上）
    CAT_ORDER_SVG = ["ai", "shopping", "video-vip", "netdisk-vip", "drive", "games", "game-discount"]
    CAT_LABEL_SVG = {
        "ai": "AI / 云服务", "shopping": "购物优惠", "video-vip": "视频会员",
        "netdisk-vip": "网盘会员", "drive": "开车线报", "games": "游戏喜加一",
        "game-discount": "游戏打折",
    }
    groups = []
    for cat in CAT_ORDER_SVG:
        cat_acts = [a for a in dated if a.get("category") == cat]
        if not cat_acts:
            continue
        cat_acts.sort(key=lambda a: (
            parse_date(a.get("end_date")) or date(9999, 12, 31),
            parse_date(a.get("start_date")) or date(9999, 12, 31),
        ))
        groups.append((cat, cat_acts))

    SECTION_H = 26  # 分区标题行高度
    total_act_rows = sum(len(acts) for _, acts in groups)
    total_headers = len(groups)
    chart_bottom = TOP_PAD + total_act_rows * ROW_H + total_headers * SECTION_H
    height = chart_bottom + BOTTOM_PAD + (20 if undated else 0)

    # 生成刻度（6 等分）
    total_days = (max_d - min_d).days
    ticks = []
    for i in range(7):
        t = min_d + timedelta(days=total_days * i // 6)
        ticks.append((t, _date_to_x(t, min_d, max_d)))

    today_x = _date_to_x(today, min_d, max_d)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" font-family="-apple-system,Segoe UI,PingFang SC,Microsoft YaHei,sans-serif">',
        f'<rect width="{WIDTH}" height="{height}" fill="{COLOR_BG}"/>',
    ]

    # 标题
    parts.append(
        f'<text x="20" y="28" font-size="16" font-weight="600" fill="{COLOR_TEXT}">'
        f'📅 活动时间轴（{today.year}年{today.month}月）</text>'
    )
    parts.append(
        f'<text x="20" y="48" font-size="11" fill="{COLOR_TEXT_DIM}">'
        f'更新于 {today.isoformat()} · 有时间限制活动 {len(dated)} 条'
        f'，开源工具 {len(excluded)} 条不显示 · 红线 = 今天 · 超一个月顶满</text>'
    )

    # 时间刻度轴
    axis_y = TOP_PAD - 8
    parts.append(f'<line x1="{TRACK_X}" y1="{axis_y}" x2="{TRACK_X + TRACK_W}" y2="{axis_y}" stroke="{COLOR_GRID}" stroke-width="1"/>')
    for t, x in ticks:
        parts.append(f'<line x1="{x}" y1="{axis_y - 4}" x2="{x}" y2="{axis_y}" stroke="{COLOR_GRID}" stroke-width="1"/>')
        label = t.strftime("%m-%d")
        parts.append(
            f'<text x="{x}" y="{axis_y - 8}" font-size="9" fill="{COLOR_TEXT_DIM}" text-anchor="middle">{label}</text>'
        )

    # 今天竖线（贯穿整个图表区域）
    chart_top = TOP_PAD
    parts.append(
        f'<line x1="{today_x}" y1="{chart_top - 10}" x2="{today_x}" y2="{chart_bottom + 4}" '
        f'stroke="{COLOR_TODAY}" stroke-width="1.5" stroke-dasharray="3,2"/>'
    )
    parts.append(
        f'<text x="{today_x}" y="{chart_top - 14}" font-size="9" fill="{COLOR_TODAY}" '
        f'text-anchor="middle" font-weight="600">今天</text>'
    )

    # 按分区绘制：每个分区一个标题行 + 活动行
    y = TOP_PAD
    track_left = TRACK_X
    track_right = TRACK_X + TRACK_W
    for cat, cat_acts in groups:
        color = _cat_color(cat)
        # 分区标题行
        parts.append(
            f'<rect x="10" y="{y}" width="{WIDTH - 20}" height="{SECTION_H - 6}" rx="4" '
            f'fill="{color}" opacity="0.12"/>'
        )
        parts.append(
            f'<text x="20" y="{y + SECTION_H - 12}" font-size="13" font-weight="600" fill="{color}">'
            f'{CAT_LABEL_SVG[cat]}（{len(cat_acts)} 条）</text>'
        )
        y += SECTION_H

        # 活动行
        for a in cat_acts:
            s = parse_date(a["start_date"])
            e = parse_date(a["end_date"])
            x1 = _date_to_x(s, min_d, max_d)
            x2 = _date_to_x(e, min_d, max_d)
            # clamp 到时间轴范围（超过一个月的顶满，不在当月的贴边）
            x1 = max(track_left, min(x1, track_right))
            x2 = max(track_left, min(x2, track_right))
            bar_w = max(2, x2 - x1)
            status = a.get("status", "active")
            cy = y + (ROW_H - BAR_H) // 2

            # 行底分隔线（淡）
            parts.append(
                f'<line x1="10" y1="{y + ROW_H}" x2="{WIDTH - 10}" y2="{y + ROW_H}" '
                f'stroke="{COLOR_GRID}" stroke-width="0.5" opacity="0.5"/>'
            )

            # 左侧活动名
            title = _esc(a.get("title", ""))
            parts.append(
                f'<circle cx="14" cy="{y + ROW_H // 2}" r="3" fill="{color}"/>'
            )
            status_icon = {"active": "🟢", "upcoming": "🟡", "ended": "⚫"}.get(status, "⚪")
            label_text = f"{status_icon} {title}"
            label_px = _visual_width(label_text) * 12
            tl_attr = ""
            if label_px > LABEL_MAX_PX:
                tl_attr = f' textLength="{int(LABEL_MAX_PX)}" lengthAdjust="spacingAndGlyphs"'
            parts.append(
                f'<text x="24" y="{y + ROW_H // 2 + 4}" font-size="12" fill="{COLOR_TEXT}"{tl_attr}>{label_text}</text>'
            )

            # 横条
            opacity = 1.0
            if status == "ended":
                opacity = 0.35
            elif status == "upcoming":
                opacity = 0.6

            if status == "upcoming":
                parts.append(
                    f'<rect x="{x1}" y="{cy}" width="{bar_w}" height="{BAR_H}" '
                    f'rx="4" fill="none" stroke="{color}" stroke-width="1.5" '
                    f'stroke-dasharray="4,2" opacity="{opacity}"/>'
                )
            else:
                parts.append(
                    f'<rect x="{x1}" y="{cy}" width="{bar_w}" height="{BAR_H}" '
                    f'rx="4" fill="{color}" opacity="{opacity * 0.85}"/>'
                )
                if status == "active":
                    progress_pct = a.get("progress_pct", 0) or 0
                    progress_w = bar_w * progress_pct / 100
                    if progress_w > 1:
                        parts.append(
                            f'<rect x="{x1}" y="{cy}" width="{progress_w}" height="{BAR_H}" '
                            f'rx="4" fill="#ffffff" opacity="0.35"/>'
                        )

            # 剩余天数标签
            if status == "active" and bar_w > 60:
                dl = a.get("days_left")
                if dl is not None:
                    parts.append(
                        f'<text x="{x1 + bar_w / 2}" y="{cy + BAR_H / 2 + 3}" font-size="9" '
                        f'fill="#ffffff" text-anchor="middle" font-weight="600">剩 {dl} 天</text>'
                    )

            y += ROW_H

    # 底部图例
    legend_y = chart_bottom + 22
    legend_items = [
        (0, COLOR_AI, "AI / 云服务"),
        (95, COLOR_SHOPPING, "购物"),
        (155, COLOR_VIDEO_VIP, "视频会员"),
        (230, COLOR_NETDISK_VIP, "网盘"),
        (290, COLOR_DRIVE, "开车"),
        (350, COLOR_GAMES, "游戏"),
    ]
    for xoff, color, label in legend_items:
        parts.append(
            f'<rect x="{TRACK_X + xoff}" y="{legend_y - 10}" width="14" height="10" rx="2" fill="{color}"/>'
            f'<text x="{TRACK_X + xoff + 20}" y="{legend_y - 1}" font-size="10" fill="{COLOR_TEXT}">{label}</text>'
        )
    parts.append(
        f'<rect x="{TRACK_X + 285}" y="{legend_y - 10}" width="14" height="10" rx="2" fill="#888" opacity="0.35"/>'
        f'<text x="{TRACK_X + 305}" y="{legend_y - 1}" font-size="10" fill="{COLOR_TEXT}">已结束</text>'
    )
    parts.append(
        f'<rect x="{TRACK_X + 375}" y="{legend_y - 10}" width="14" height="10" rx="2" '
        f'fill="none" stroke="#888" stroke-dasharray="3,2"/>'
        f'<text x="{TRACK_X + 395}" y="{legend_y - 1}" font-size="10" fill="{COLOR_TEXT}">未开始</text>'
    )
    parts.append(
        f'<line x1="{TRACK_X + 465}" y1="{legend_y - 12}" x2="{TRACK_X + 465}" y2="{legend_y + 2}" '
        f'stroke="{COLOR_TODAY}" stroke-width="1.5" stroke-dasharray="3,2"/>'
        f'<text x="{TRACK_X + 473}" y="{legend_y - 1}" font-size="10" fill="{COLOR_TEXT}">今天</text>'
    )

    # 无日期活动提示
    if undated:
        note_y = legend_y + 22
        parts.append(
            f'<text x="20" y="{note_y}" font-size="10" fill="{COLOR_TEXT_DIM}">'
            f'另有 {len(undated)} 条活动缺少明确日期，未在时间轴显示（见下方表格）</text>'
        )

    parts.append("</svg>")
    svg = "\n".join(parts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")
    log(f"已生成 SVG 日历 {output_path.name}"
        f"（有时间限制 {len(dated)} 条，{len(undated)} 条无日期，"
        f"开源工具 {len(excluded)} 条不显示）")
    return output_path


def _empty_svg(today: date) -> str:
    """没有活动时的空状态 SVG。"""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="120" viewBox="0 0 {WIDTH} 120" font-family="-apple-system,Segoe UI,sans-serif">
<rect width="{WIDTH}" height="120" fill="{COLOR_BG}"/>
<text x="20" y="32" font-size="16" font-weight="600" fill="{COLOR_TEXT}">📅 活动时间轴</text>
<text x="20" y="56" font-size="12" fill="{COLOR_TEXT_DIM}">更新于 {today.isoformat()} · 暂无活动数据</text>
<text x="20" y="80" font-size="11" fill="{COLOR_TEXT_DIM}">当月无限时活动。长期免费活动见下方表格，其他月份活动不在此显示。</text>
<text x="20" y="98" font-size="11" fill="{COLOR_TEXT_DIM}">每条横条代表一个活动的持续时间，红色虚线标记今天，进度填充表示当前完成度。</text>
</svg>'''


if __name__ == "__main__":
    import json
    from utils import DATA_DIR
    acts = []
    for cat in ("ai", "open-source", "drive", "games", "shopping", "video-vip", "netdisk-vip"):
        p = DATA_DIR / cat / "activities.json"
        if p.exists():
            acts.extend(json.loads(p.read_text(encoding="utf-8")))
    generate_svg(acts)
