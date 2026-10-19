"""云厂商活动收集器：从华为云/阿里云/腾讯云等活动页提取代金券、免费试用、学生优惠。

策略：抓活动页的 <title> + <meta description>，这些是官方 SEO 摘要，
浓缩了活动核心内容（代金券金额、折扣、免费额度），稳定可靠。
"""
from __future__ import annotations

import hashlib
import re
import time
from datetime import timedelta

import requests

from utils import log, now_bj, safe_text

BJ = now_bj()

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,en;q=0.7,en-US;q=0.3",
    # 注意：不要手动设置 Accept-Encoding: br
    # requests 默认支持 gzip/deflate 自动解压，手动指定 br 会因缺 brotli 库导致乱码
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# 云厂商活动页清单：长期维护，发现新活动页就加进来
# (云厂商, 板块标签, URL)
CLOUD_PAGES = [
    # 华为云
    ("华为云", "免费试用", "https://activity.huaweicloud.com/free_test/index.html"),
    ("华为云", "老用户权益", "https://activity.huaweicloud.com/member.html"),
    ("华为云", "组合购", "https://activity.huaweicloud.com/group-purchase/index.html"),
    # 阿里云
    ("阿里云", "免费试用", "https://free.aliyun.com"),
    ("阿里云", "高校计划", "https://university.aliyun.com"),
    ("阿里云", "新人特惠", "https://www.aliyun.com/activity/new"),
    # 腾讯云
    ("腾讯云", "大促代金券", "https://cloud.tencent.com/act/new"),
    ("腾讯云", "校园计划", "https://cloud.tencent.com/act/campus"),
    ("腾讯云", "免费体验", "https://cloud.tencent.com/act/free"),
    ("腾讯云", "开发者", "https://cloud.tencent.com/act/developer"),
]


def _stable_id(url: str) -> str:
    """基于 URL 的稳定 ID，同一活动页永远同一个 ID。"""
    return "cloud_" + hashlib.md5(url.encode()).hexdigest()[:12]


def _get_meta(text: str) -> tuple[str, str]:
    """提取 title 和 meta description。"""
    title = re.search(r"<title[^>]*>(.*?)</title>", text, re.DOTALL)
    desc = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', text)
    if not desc:
        desc = re.search(r'<meta\s+content="([^"]*)"\s+name="description"', text)
    t = title.group(1).strip() if title else ""
    d = desc.group(1).strip() if desc else ""
    # 清理常见 SEO 后缀
    for suffix in ["-阿里云", "-华为云", "-腾讯云", "_腾讯云", "-京东云", "-百度智能云"]:
        if t.endswith(suffix):
            t = t[: -len(suffix)]
    return t, d


def fetch_page(url: str, referer: str = "") -> str | None:
    """抓取页面 HTML。"""
    headers = dict(BROWSER_HEADERS)
    if referer:
        headers["Referer"] = referer
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            log(f"抓取失败 {url}: HTTP {resp.status_code}", level="ERROR")
            return None
        return resp.text
    except Exception as e:
        log(f"抓取失败 {url}: {safe_text(e, 100)}", level="ERROR")
        return None


def collect_cloud_activities() -> list[dict]:
    """收集所有云厂商活动。

    每个活动页生成一条活动：标题=厂商+板块，描述=title+description 摘要。
    ID 基于 URL，稳定去重；活动长期有效，end_date 顺延 30 天。
    """
    activities: list[dict] = []
    today = BJ.strftime("%Y-%m-%d")
    end = (BJ + timedelta(days=30)).strftime("%Y-%m-%d")

    for vendor, section, url in CLOUD_PAGES:
        # 腾讯云对海外 IP 敏感，加 Referer 伪装国内来源
        referer = "https://cloud.tencent.com/" if "cloud.tencent.com" in url else ""
        html = fetch_page(url, referer=referer)
        if not html:
            continue

        title, desc = _get_meta(html)
        if not title and not desc:
            # 诊断：打出返回内容片段，方便排查（如海外 IP 被风控/跳转）
            snippet = re.sub(r"\s+", " ", html[:300])
            log(f"[{vendor}] {url} 无 meta，返回内容: {snippet[:150]}", level="WARN")
            continue

        # 拼活动标题和描述
        act_title = f"{vendor}·{section}"
        # description 更详细，作为主内容；title 作为补充
        detail = desc if desc else title
        supplement = title if desc and title != desc else ""

        activities.append({
            "id": _stable_id(url),
            "title": act_title,
            "url": url,
            "description": detail[:200],
            "start_date": today,
            "end_date": end,
            "category": "ai",  # 归入 ai 板块（AI 算力/额度/代金券）
            "tags": [vendor, section],
            "status": "active",
            "discovered_at": now_bj().isoformat(),
        })
        log(f"[{vendor}] {section}: {detail[:60]}")
        time.sleep(1)  # 间隔，礼貌抓取

    log(f"云厂商: 共收集 {len(activities)} 条活动")
    return activities
