# 游戏平台介绍

> 本文档介绍薅羊毛情报站收录的所有游戏喜加一平台。
> 每个平台的特点、抓取方式、当前是否启用。

---

## 当前启用的游戏源（6 个，每天 15:00/16:53 自动抓取）

这 6 个源是项目实际在抓的，分成两类：

### 官方 API 直连（`direct_collector.py`，准确可靠）

| 平台 | 官网 | 抓取方式 | 说明 |
|------|------|---------|------|
| **Epic Games Store** | https://store.epicgames.com/free-games | GraphQL API | 每周四更新免费游戏，用 Epic 官方 GraphQL 接口 `freeGamesPromotions` 拿结构化数据，最准确 |
| **Steam** | https://store.steampowered.com | Steam Web API | 抓免费周末（Free Weekend）和免费游戏，用 `featuredcategories` 接口 |
| **GOG** | https://www.gog.com | embed API | 用 GOG 的 `embed.gog.com/games/ajax/filtered` 接口抓免费游戏 |

### 社区 / 聚合源（`blog_collector.py`，覆盖广）

| 平台 | 官网 | 抓取方式 | 说明 |
|------|------|---------|------|
| **IsThereAnyDeal** | https://isthereanydeal.com | 网页解析 | 游戏价格聚合站，跨多个商店比价。只提取 -100%（完全免费）的限免游戏，标注 shop 名（Epic/Steam 等） |
| **itch.io** | https://itch.io/games/free | 网页解析 | 独立游戏平台，大量小众免费/限免游戏。服务端渲染，抓 `game_cell` 块 |
| **Reddit r/FreeGameFindings** | https://www.reddit.com/r/FreeGameFindings | RSS | 社区分享免费游戏线报，信息快、覆盖广。用 RSS 抓最新 15 条 |

---

## sources.json 里配置的其他平台（可扩展启用）

以下平台已在 `data/sources.json` 里登记，但当前 `blog_collector.py` 没启用抓取。
想启用的话，在 `blog_collector.SOURCES["games"]` 里加一条即可。

| 平台 | 官网 | 类型 | 说明 |
|------|------|------|------|
| **SteamDB** | https://steamdb.info/upcoming/free/ | 限免追踪 | Steam 限免数据库，比 Steam 官方 API 更全 |
| **Humble Bundle** | https://www.humblebundle.com/store | 游戏商店 | 有时有限免/慈善包 |
| **Amazon Prime Gaming** | https://gaming.amazon.com/home | 会员免费 | Prime 会员每月免费游戏，需 Prime 订阅 |
| **Fanatical** | https://www.fanatical.com | 游戏商店 | 常有低价包/限免 |
| **IndieGala** | https://www.indiegala.com | 独立游戏 | 独立游戏商店，有时免费 |
| **Green Man Gaming** | https://www.greenmangaming.com | 游戏商店 | 官方授权 key 商店 |
| **Ubisoft** | https://www.ubisoft.com/en-us/games | 主机平台 | 育碧，偶尔免费周末 |
| **EA** | https://www.ea.com/games | 主机平台 | EA Play，偶尔免费试玩 |
| **Nintendo** | https://www.nintendo.com | 主机平台 | 任天堂，很少限免 |
| **Xbox** | https://www.xbox.com/en-US/games | 主机平台 | Xbox Game Pass，偶尔免费 |
| **PlayStation** | https://store.playstation.com | 主机平台 | PS Store，偶尔免费 |
| **TapTap** | https://www.taptap.io | 手游平台 | 手游，偶尔限免 |
| **SteamGifts** | https://www.steamgifts.com | 社区抽奖 | 社区送 Steam key，需抽奖 |
| **Reddit r/GameDeals** | https://www.reddit.com/r/GameDeals | 社区分享 | 游戏打折/优惠线报（非免费） |
| **Reddit r/FreeGamesOnSteam** | https://www.reddit.com/r/FreeGamesOnSteam | 社区分享 | Steam 上免费游戏线报 |

---

## 各平台特点对比

### 免费游戏类型

| 类型 | 说明 | 哪些平台有 |
|------|------|-----------|
| **永久免费** | 一直免费，不是限时 | Steam Free to Play、itch.io 免费区 |
| **限免（喜加一）** | 限时免费领取，过了时间恢复收费，领了永久拥有 | Epic 每周免费、Steam 免费周末、GOG 限免 |
| **giveaway** | 社区/平台赠送，可能需抽奖或条件 | Reddit FreeGameFindings、SteamGifts |
| **会员免费** | 需要订阅会员才能领 | Amazon Prime Gaming、Xbox Game Pass |

### 抓取可靠性

| 可靠性 | 平台 | 原因 |
|--------|------|------|
| **高**（官方 API） | Epic GraphQL、Steam API、GOG embed | 官方结构化接口，不依赖页面解析 |
| **中**（网页解析） | itch.io、IsThereAnyDeal | 服务端渲染，页面结构稳定时可靠 |
| **中**（RSS） | Reddit FreeGameFindings | RSS 标准格式，但 Reddit 可能限流 |
| **低**（SPA/反爬） | Amazon Prime、主机平台 | JS 渲染或反爬，需浏览器或特殊处理 |

---

## 如何启用一个新平台

以启用 **SteamDB 限免** 为例：

1. 在 `scripts/blog_collector.py` 的 `SOURCES["games"]` 里加一条：
```python
{"name": "SteamDB-限免", "url": "https://steamdb.info/upcoming/free/", "parser": "steamdb"},
```

2. 写一个 `parse_steamdb(html)` 解析函数（参考 `parse_itchio` 的写法）

3. 在 `collect_blog_activities` 的 parser 分支里加：
```python
elif parser == "steamdb":
    acts = parse_steamdb(text)
```

4. 本地测试：`python scripts/collect.py games-blog`

5. 推送，等下次 16:53 自动跑

---

## 数据字段

每条游戏活动在 `data/games/activities.json` 里的关键字段：

```json
{
  "id": "稳定ID",
  "title": "游戏标题（含平台前缀如 'Epic 免费游戏: xxx'）",
  "category": "games",
  "source_url": "来源页",
  "claim_url": "领取页",
  "start_date": "免费开始日期",
  "end_date": "免费结束日期",
  "value": "福利（如 '免费领取'）",
  "tags": ["来源标签"],
  "status": "active/upcoming/ended"
}
```

---

## 相关文件

| 文件 | 作用 |
|------|------|
| `scripts/direct_collector.py` | Epic/Steam/GOG 官方 API 抓取 |
| `scripts/blog_collector.py` | ITAD/itch.io/Reddit 网页/RSS 抓取 |
| `data/sources.json` | 所有游戏源登记（含未启用的） |
| `data/games/activities.json` | 游戏活动数据（脚本生成） |
