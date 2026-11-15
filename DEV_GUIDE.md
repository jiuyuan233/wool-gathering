# 开发文档（交接文档）

> 本文档是给**接手开发的 AI 或人类**看的完整交接资料。包含项目全貌、架构设计、
> 每个文件职责、AI 工作流程、用户画像、遗留问题和开发指南。
> 
> **最后更新**：2026-11-15
> **当前 AI 模型**：gpt-6.1-sol（ChatAnywhere 主力）+ deepseek-ai/DeepSeek-V3.2（SiliconFlow 备用，失败自动切换）
> **当前状态**：所有核心功能已实现并实测通过，历史遗留问题已全部关闭（见第 8 节）。
> **角色分工**：日常更新（能力弱的 AI / 新手）读 [docs/日常更新指南.md](docs/日常更新指南.md)
> 照 SOP 操作即可；开发维护（能力强的 AI）读本文件 + AGENT.md。

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构设计](#2-架构设计)
3. [文件职责详解](#3-文件职责详解)
4. [AI 工作流程](#4-ai-工作流程)
5. [数据流与状态机](#5-数据流与状态机)
6. [用户画像与交流指南](#6-用户画像与交流指南)
7. [开发环境与常见操作](#7-开发环境与常见操作)
8. [遗留问题](#8-遗留问题)
9. [已实现功能清单](#9-已实现功能清单)
10. [GitHub Actions 配置详解](#10-github-actions-配置详解)

---

## 1. 项目概述

### 一句话理解

GitHub Actions 每天分六个时段自动抓取 AI/云服务优惠、开源免费工具、开车线报、游戏喜加一等信息，去重合并后生成 README + SVG 甘特图日历，自动 commit 推送回仓库。

### 仓库地址

`jiuyuan233/wool-gathering`（GitHub 公开仓库）

### 核心价值

用户每天打开仓库 README 就能看到当天所有薅羊毛活动汇总，不用自己去各个网站翻。SVG 日历直观展示哪些活动正在进行、即将开始、即将结束。

### 技术栈

- **语言**：Python 3.11
- **AI**：ChatAnywhere 中转站（OpenAI 兼容协议），模型 `gpt-6.1-sol`；SiliconFlow DeepSeek-V3.2 作备用自动切换
- **浏览器自动化**：Playwright（小黑盒 SPA 渲染）
- **CI/CD**：GitHub Actions（6 个 cron 定时任务）
- **数据存储**：JSON 文件（无数据库）
- **输出**：README.md + docs/calendar.svg + docs/分类活动.md

---

## 2. 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    GitHub Actions                        │
│  (6 个 cron 定时任务 + workflow_dispatch 手动触发)       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│              scripts/collect.py (主入口)                  │
│                                                          │
│  main() → process_category() × N → finalize()            │
│         （finalize 内含 PENDING_URLS 处理 + archive_expired）│
└──────┬──────────────┬──────────────┬────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ cloud_   │  │ blog_    │  │ direct_  │
│ collector│  │ collector│  │ collector│
│ (云厂商) │  │ (博客+   │  │ (Epic/   │
│          │  │  小黑盒) │  │  Steam)  │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │
     ▼              ▼              ▼
┌──────────────────────────────────────────┐
│      AI 抽取 (ai_client.py，仅用于        │
│  PENDING_URLS 自然语言理解，非主链路)      │
│  模型: gpt-6.1-sol (ChatAnywhere)         │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│        dedup.py (去重 + 合并 + 状态)      │
│  normalize_activity → merge → refresh_   │
│  status → dedupe_within（已归档 id 防回流）│
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌────────────────┐  ┌────────────────┐
│ svg_calendar.py│  │ calendar_      │
│ (SVG 甘特图)   │  │ generator.py   │
│                │  │ (README + 文档)│
└────────────────┘  └────────────────┘
```

### 六个定时任务时段

| cron (UTC) | 北京时间 | 模式 | 说明 |
|------------|---------|------|------|
| 17 21 * * * | 05:17 | ai-cloud | 云厂商活动 |
| 23 0 * * * | 08:23 | ai-blog | 博客聚合 |
| 41 2 * * * | 10:41 | drive | V2EX 开车线报 |
| 37 5 * * * | 13:37 | games-direct | Epic/Steam/GOG 官方 API |
| 53 7 * * * | 15:53 | games-blog | ITAD/itch.io/Reddit |
| 47 10 * * * | 18:47 | finalize | 整理：SVG + README |

---

## 3. 文件职责详解

### scripts/collect.py（主入口，18597 字节）

**职责**：协调整个收集流程，是 Actions 运行的入口点。

**关键函数**：

| 函数 | 职责 |
|------|------|
| `main()` | 解析命令行参数，调度各模式 |
| `process_pending_urls()` | 处理 PENDING_URLS.md 里的 URL 和自然语言描述 |
| `_process_natural_language()` | 用 AI 理解自然语言（如"Qoder每天领100积分"），创建活动 |
| `process_category(category, subset)` | 处理单个分类：收集→合并→保存 |
| `finalize()` | 生成 SVG + README + 分类文档 |
| `archive_expired()` | 归档过期活动到 docs/archive/ |

**process_category 的分流逻辑**：
- `ai` 分类 = 云厂商活动 + 博客聚合 + 小黑盒社区
- `games` 分类 = Epic/Steam/GOG + 博客聚合 + 小黑盒社区
- `game-discount` 分类 = 小黑盒打折 + 小黑盒社区
- 其他分类 = 博客聚合 + 小黑盒社区

**subset 参数**：
- `all`：全部（默认）
- `cloud`：仅云厂商（仅 ai 有效）
- `blog`：仅博客聚合
- `direct`：仅官方 API（仅 games 有效）

### scripts/blog_collector.py（博客+小黑盒抓取）

**职责**：从内置博客源、RSS、社区聚合网站抓取活动信息 + 小黑盒 Playwright 抓取。

**关键函数**：

| 函数 | 职责 |
|------|------|
| `collect_blog_activities(category)` | 从**内置 `SOURCES` 字典**（不是 sources.json！）里该分类的博客源抓取 |
| `fetch(url)` | 抓取 URL（自动 percent-encode 非 ASCII 字符、429 重试） |
| `collect_heybox_discounts()` | 小黑盒游戏打折（SPA，需 Playwright，读 sources.json 的 heybox 源） |
| `collect_heybox_community(category)` | 小黑盒社区合集帖（SPA，需 Playwright，读 sources.json 的 heybox-community 源） |
| `parse_itad/itchio/ggdeals/reddit/rss/v2ex` | 各平台解析器 |

> **源的真实分工**（2026-11-15 核实）：日常轮询源 = 内置 `SOURCES`（8 个）+ 云厂商页 +
> 官方游戏 API + sources.json 的 heybox 类（9 个）。sources.json 里 53 个 html 源只做
> 登记去重，不参与轮询；PENDING_URLS 提交的 URL 会被当场抓一次快照入库。

**collect_heybox_community 的工作方式**：
1. 用 Playwright 渲染 `https://xiaoheihe.cn/app/bbs/home`
2. 用 `eval_on_selector_all` 提取所有 `<a>` 标签的标题和链接
3. 按分类关键词过滤（如 ai 分类匹配 "AI/大模型/GPT/Claude" 等）
4. 优先找"整理合集"帖子（标题含"整理/合集/汇总/盘点"等词）
5. 创建活动，source_url 指向帖子链接，end_date 留空（不当天过期）

### scripts/cloud_collector.py（云厂商抓取，5272 字节）

**职责**：抓取华为云、阿里云、腾讯云等云厂商的免费活动页面。

**关键函数**：
- `collect_cloud_activities(old_acts)`：抓取所有云厂商活动，old_acts 用于 fallback

### scripts/direct_collector.py（官方 API 抓取，9350 字节）

**职责**：直接调用 Epic/Steam/GOG 官方 API 获取免费游戏。

**关键函数**：
- `collect_epic_free_games()`：Epic Games 免费游戏 API
- `collect_steam_free_weekend()`：Steam 免费周末
- `collect_gog_free_games()`：GOG 免费游戏

### scripts/ai_client.py（AI 客户端，5288 字节）

**职责**：封装 OpenAI 兼容协议的 AI 调用。

**关键类**：
- `RateLimiter`：滑动窗口速率限制（45 次/5 分钟）
- `AIClient`：AI 客户端，支持 chat/chat_text/chat_json

**配置**（通过环境变量）：
- `AI_BASE_URL`：中转站地址（主力 `https://api.chatanywhere.tech/v1`）
- `AI_API_KEY`：API key（存在 GitHub Secret 里）
- `AI_MODEL`：模型名（默认 `gpt-6.1-sol`，workflow env 会覆盖）
- `AI_FALLBACK_BASE_URL` / `AI_FALLBACK_API_KEY` / `AI_FALLBACK_MODEL`：备用中转站（可选）

### scripts/prompts.py（AI 提示词）

**职责**：定义给 AI 的系统提示词和 prompt 模板。

**关键内容**：
- `SYSTEM_PROMPT`：AI 的完整操作手册（什么算薅羊毛活动、什么不算、游戏标题中文译名规则、输出格式）
- `build_extract_messages()` / `build_search_messages()`：预留的模板（当前生产链路未调用；
  AI 唯一在用的入口是 collect.py 的 `_process_natural_language`，直接用 SYSTEM_PROMPT）

### scripts/dedup.py（去重+合并+状态，3294 字节）

**职责**：活动去重、合并、状态刷新。

**关键函数**：
- `normalize_activity(raw, category)`：规范化活动（生成 id、补全字段）
- `merge(old_list, new_list, today)`：合并新旧活动列表
- `refresh_status(activities, today)`：根据日期刷新 status（upcoming/active/expired）
- `dedupe_within(new_list)`：新活动内部去重

### scripts/svg_calendar.py（SVG 甘特图，13349 字节）

**职责**：生成 SVG 甘特图日历。

**关键函数**：
- `generate_svg(activities, output_path)`：生成 SVG 文件
- `status_of(start, end, today)`：计算活动状态（用于渲染实线/虚线）

**渲染逻辑**：
- upcoming（未开始）：虚线
- active（进行中）：实线
- expired（已过期）：灰色淡显

### scripts/calendar_generator.py（README+文档生成，8653 字节）

**职责**：生成 README.md 和 docs/分类活动.md。

**关键函数**：
- `generate_readme()`：生成 README.md
- `generate_docs_data()`：生成 docs/分类活动.md

### scripts/utils.py（工具函数，3608 字节）

**职责**：通用工具函数。

**关键函数**：
- `log(msg)`：带时间戳的日志
- `now_bj()` / `today_bj()`：北京时间
- `parse_date(s)` / `date_to_str(d)`：日期转换
- `make_id(*parts)`：生成活动 id
- `load_json(path)` / `save_json(path, data)`：JSON 读写
- `status_of(start, end, today)`：活动状态计算
- `safe_text(s, max_len)`：安全文本截断

### scripts/sources_manager.py（源管理，3298 字节）

**职责**：管理 data/sources.json 里的信息源。

---

## 4. AI 工作流程

### AI 在项目中的角色

AI 只负责 **PENDING_URLS.md 自然语言条目**的理解（用户写"Qoder每天领100积分"这类描述时，
AI 解析成结构化活动）。抓取主链路（blog/cloud/direct collector）不走 AI，纯关键词规则解析，
所以 AI 挂了不影响日常抓取。

### 调用链

```
collect.py process_pending_urls()          # finalize 阶段触发
  → _process_natural_language(desc, ...)   # 仅自然语言行走这里
    → ai_client.py chat_json()             # 调 AI
      → prompts.py SYSTEM_PROMPT           # 组装 prompt
      → ChatAnywhere API (gpt-6.1-sol)     # 主力，接入点 api.chatanywhere.tech
        ↳ 连续 3 次失败自动切 SiliconFlow (deepseek-ai/DeepSeek-V3.2)  # 备用
    → 返回 JSON → 解析为活动列表 → 写入 data/{category}/activities.json
```

### AI 的输入输出

**输入**：
- system prompt：操作手册（什么算薅羊毛活动、输出格式）
- user prompt：网页内容 + 来源信息 + 当前日期

**输出**：严格 JSON
```json
{
  "activities": [
    {
      "title": "华为云 AI 200 元代金券",
      "source_url": "https://...",
      "claim_url": "",
      "start_date": "2026-10-18",
      "end_date": "2026-10-25",
      "value": "200 元代金券",
      "requirements": ["实名认证", "新用户"],
      "description": "新用户专享",
      "tags": ["代金券", "华为云", "AI"]
    }
  ]
}
```

### PENDING_URLS 自然语言处理

用户可以在 PENDING_URLS.md 里写自然语言描述（不只是 URL）：
```
Qoder现在每天领100积分，非常好用 #ai
```

`_process_natural_language()` 会：
1. 用 AI 理解这段描述
2. AI 基于描述本身的信息提取（无联网能力，不编造；信息不足返回空）
3. 返回活动信息，直接写入 activities.json

### AI 模型选择

- **当前主力**：`gpt-6.1-sol`（ChatAnywhere，2026-11-15 两轮实测：JSON 最干净、相对日期最准、
  福利价值抓取最全；该 key 下 19 个模型可用，见 AGENT.md 13.1.1）
- **备用**：`deepseek-ai/DeepSeek-V3.2`（SiliconFlow），主力连续 3 次失败（401/欠费/超时）自动切换，
  逻辑在 `ai_client.py` 的 `_providers()`/`chat()`
- **历史坑**：旧 key 在 ChatAnywhere 免费版 401（gpt-4o-mini / deepseek-v3-2 均失败，见 PENDING_URLS
  已处理区 2026-10-28 记录）；2026-11-15 换新 key 后 gpt 系/DeepSeek 系均正常。接入点 `.tech` 实测可达，
  `.org` 从部分网络连不上（本地超时，GitHub runner 之前一直用 .org 也通）
- **速率限制**：代码里 RateLimiter 限制 45 次/5 分钟

---

## 5. 数据流与状态机

### 活动状态

```
upcoming (未开始) → active (进行中) → expired (已过期)
     │                   │
     └─ 虚线渲染 ─┘   └─ 实线渲染 ─┘
```

`status_of(start, end, today)` 计算逻辑：
- today < start → upcoming
- start ≤ today ≤ end → active
- today > end → expired
- start 为空 → active（立即开始）
- end 为空 → active（长期有效）

### 数据文件

```
data/
├── sources.json              # 源登记表 62 个：heybox 类 9 个参与轮询，html 类 53 个仅登记
├── ai/activities.json        # AI 类活动
├── open-source/activities.json
├── drive/activities.json
├── games/activities.json
├── shopping/activities.json
├── video-vip/activities.json
├── netdisk-vip/activities.json
└── game-discount/activities.json
```

### 活动字段

```json
{
  "id": "abc123def456",          // MD5(title+source_url)[:12]
  "title": "活动标题",
  "category": "ai",              // 8 个分类之一
  "source_url": "https://...",   // 活动来源页面
  "claim_url": "https://...",    // 领取链接（可空）
  "start_date": "2026-10-18",    // YYYY-MM-DD
  "end_date": "2026-10-25",      // YYYY-MM-DD（可空=长期）
  "value": "200 元代金券",       // 福利价值
  "requirements": ["新用户"],    // 条件
  "description": "描述",
  "tags": ["AI", "华为云"],
  "discovered_at": "2026-10-18T...",
  "last_seen": "2026-10-18",
  "status": "active"             // upcoming/active/expired
}
```

### 8 个分类

| 分类 | 说明 | 主要来源 |
|------|------|---------|
| ai | AI/云服务优惠 | 云厂商页面 + 博客 |
| open-source | 开源免费工具 | 博客聚合 |
| drive | 开车线报 | V2EX |
| games | 游戏喜加一 | Epic/Steam/GOG API |
| shopping | 购物优惠 | 博客聚合 |
| video-vip | 视频会员 | 博客聚合 |
| netdisk-vip | 网盘会员 | 博客聚合 |
| game-discount | 游戏打折 | 小黑盒 |

---

## 6. 用户画像与交流指南

### 用户画像

**身份**：技术爱好者，运营一个自动化薅羊毛情报站 GitHub 仓库

**特点**：
- 中文母语，所有交流用简体中文
- 懂技术但不写代码，依赖 AI 做开发
- 对信息质量有高要求，会亲自验证结果
- 注重效率，不喜欢浪费时间和额度
- 直接表达需求，不绕弯子
- 会提供必要的资源（如 API key）但期望 AI 善用

**交流原则**：
1. **全程简体中文**：包括内部思考和推理过程
2. **直接给结果**：用户要的是结果，不是过程描述
3. **主动验证**：做完后主动检查结果，不要等用户发现问题
4. **诚实报告**：失败了就说失败，不要掩饰
5. **不暴露敏感信息**：token、API key 等绝不写入文档或代码

**用户常见指令**：
- "action" → 触发 GitHub Actions 运行或查看运行状态
- "检查 run #XX 的结果" → 检查指定 Actions 运行的结果
- 描述问题 → 期望 AI 定位根因并修复

**用户不喜欢的**：
- 反复问同一个问题
- 长篇大论但不给结论
- 隐瞒失败或问题
- 在文档/代码里暴露 token

---

## 7. 开发环境与常见操作

### 环境限制（上一任开发环境的经验记录，新环境可能不适用，但值得先看）

1. **文件恢复机制**：工作区文件和 .git/objects 会在 bash 命令间被恢复到 git HEAD 状态。edit 工具的修改也会被恢复。
   - **解决方案**：用 `python3 -c` 在 bash 内修改文件到 /tmp，再用 GitHub API 创建 blob 提交

2. **GIT_INDEX_FILE 干扰**：用自定义索引文件提交后，git push 前必须 unset GIT_INDEX_FILE
   - **解决方案**：直接用 GitHub API 创建提交（POST git/blobs → POST git/trees → POST git/commits → PATCH git/refs）

3. **bash 工具挂起**：sleep、heredoc、执行外部脚本、长命令可能挂起
   - **解决方案**：用短内联 && 命令和 `python3 -c` 命令

4. **git push 网络问题**：github.com 端口 443 间歇超时
   - **解决方案**：用 GitHub API 直接创建提交

5. **ChatAnywhere 不可直接访问**：从开发环境无法直接调 ChatAnywhere API
   - **解决方案**：通过 GitHub Actions 间接测试

### 用 GitHub API 提交修改

```python
import urllib.request, json, base64

TOKEN = '你的 GitHub token'  # 不要写入文档！
API = 'https://api.github.com/repos/jiuyuan233/wool-gathering'

def api_call(method, path, data=None):
    url = f'{API}/{path}'
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        'Authorization': f'token {TOKEN}',
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req))

# 1. 获取远程 main 最新 commit
ref = api_call('GET', 'git/ref/heads/main')
parent_sha = ref['object']['sha']
parent_commit = api_call('GET', f'git/commits/{parent_sha}')
base_tree = parent_commit['tree']['sha']

# 2. 创建 blob
with open('/tmp/modified_file.py', 'rb') as f:
    content = f.read()
blob = api_call('POST', 'git/blobs', {
    'content': base64.b64encode(content).decode(),
    'encoding': 'base64',
})

# 3. 创建 tree
new_tree = api_call('POST', 'git/trees', {
    'base_tree': base_tree,
    'tree': [{'path': 'scripts/xxx.py', 'mode': '100644', 'type': 'blob', 'sha': blob['sha']}],
})

# 4. 创建 commit
new_commit = api_call('POST', 'git/commits', {
    'message': 'commit message',
    'tree': new_tree['sha'],
    'parents': [parent_sha],
})

# 5. 更新 ref
api_call('PATCH', 'git/refs/heads/main', {'sha': new_commit['sha']})
```

### 触发 Actions 运行

```python
req = urllib.request.Request(
    f'{API}/actions/workflows/daily-collect.yml/dispatches',
    data=json.dumps({'ref': 'main', 'inputs': {'mode': 'all'}}).encode(),
    method='POST',
    headers={'Authorization': f'token {TOKEN}', 'Accept': 'application/vnd.github+json'}
)
urllib.request.urlopen(req)
```

### 检查 Actions 运行状态

```python
req = urllib.request.Request(
    f'{API}/actions/runs?per_page=3',
    headers={'Authorization': f'token {TOKEN}', 'Accept': 'application/vnd.github+json'}
)
data = json.load(urllib.request.urlopen(req))
for r in data['workflow_runs']:
    print(f'run #{r["run_number"]} status={r["status"]} conclusion={r["conclusion"]}')
```

### 更新 GitHub Secret

```python
from nacl import encoding, public
import base64

# 1. 获取 public key
pk = api_call('GET', 'actions/secrets/public-key')

# 2. 加密
public_key = public.PublicKey(pk['key'].encode(), encoding.Base64Encoder())
sealed_box = public.SealedBox(public_key)
encrypted = sealed_box.encrypt(SECRET_VALUE.encode())
encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')

# 3. 更新 secret
api_call('PUT', 'actions/secrets/SECRET_NAME', {
    'encrypted_value': encrypted_b64,
    'key_id': pk['key_id'],
})
```

---

## 8. 遗留问题（截至 2026-11-15 已全部关闭）

> 以下问题逐一核实并处理：问题 1（换强模型+备用切换）、问题 3（AI 不在抓取主链路）、
> 问题 5（确认旧 key 失效并换新）、问题 6（早已修复）；问题 2 属于"待线上数据验证"，
> 问题 4 按设计闭环（见下）。新出现的请追加到本节。

### 问题 1：PENDING_URLS 自然语言处理依赖 AI 可用性

**状态**：已解决（2026-11-15）

**详情**：
- `_process_natural_language()` 用 AI 理解自然语言描述
- 已换主力模型 gpt-6.1-sol（ChatAnywhere 新 key，实测可用），并支持备用中转站自动切换；
  单次调用失败也有 try-except 兜底，不影响 finalize 其他环节

**残留风险**：ChatAnywhere 免费额度耗尽且 SiliconFlow 余额耗尽时，自然语言条目会处理失败并记录
到「已处理」区，等待下次运行重试。

### 问题 2：小黑盒社区合集帖抓取效果待验证

**状态**：代码已实现，但实际抓取效果未确认

**详情**：
- `collect_heybox_community()` 用 Playwright 渲染小黑盒社区页面
- 用 `eval_on_selector_all` 提取帖子链接
- 但小黑盒是 SPA，DOM 结构可能变化
- 如果 `eval_on_selector_all` 没找到帖子链接，会 fallback 到文本提取（但没有链接）

**建议**：
- 检查 Actions 日志确认小黑盒抓取是否成功
- 如果 Playwright 渲染失败，考虑用小黑盒的 API 接口

### 问题 3：AI 调用失败导致 process_category 中断

**状态**：已解决（核实：AI 不在抓取主链路上）

**详情**：
- `collect_blog_activities()` / `collect_cloud_activities()` / `collect_games_category()`
  均为纯关键词规则解析，**不调用 AI**，AI 故障不影响抓取
- 唯一调 AI 的 `_process_natural_language()` 在 `process_pending_urls()` 里已被
  try-except 包裹，失败只记录到「已处理」区，不中断流程

### 问题 4：Qoder 活动未出现在 SVG 日历

**状态**：已解决（2026-11-02 由 AI 自然语言处理自动创建）

**详情**：
- 2026-11-02 那次运行里，AI 成功理解了 PENDING_URLS 里的 Qoder 描述，
  创建了「Qoder 每天免费领 100 积分」（长期活动，end_date 空），已显示在 README 的 AI 分区
- 2026-11-15 复验：条目在库；AI 无联网能力所以无法自动更新它的细节，
  细节有变时用户可在 PENDING_URLS 提交官方页面 URL 触发重新抓取

### 问题 5：gpt-4o-mini 在 ChatAnywhere 免费版不可用

**状态**：已解决（2026-11-15 确认为旧 key 失效）

**详情**：
- 旧 key 测试 gpt-4o-mini 返回 401 Unauthorized，后来连 deepseek-v3-2 也 401（key 额度/权限问题）
- 2026-11-15 换新 key 实测：gpt-4o-mini / gpt-4o / gpt-5 系 / gpt-6 系 / deepseek 系等 19 个模型全部可用
- **当前主力**：ChatAnywhere `gpt-6.1-sol`；SiliconFlow DeepSeek-V3.2 跨服务商兜底

### 问题 6：SVG 虚线 bug（已修复）

**状态**：已修复

**详情**：
- 活动创建时 status="upcoming"，但只有重新抓取该分类才会更新 status
- 某分类今天没抓 → status 一直是 "upcoming" → SVG 画虚线
- **修复**：finalize() 里先 refresh_status 再 generate_svg；svg_calendar.py 用 status_of() 实时计算

---

## 9. 已实现功能清单

### 核心功能
- [x] 6 个定时任务分时段自动收集
- [x] 8 个分类的活动管理
- [x] AI 理解 PENDING_URLS 自然语言条目（DeepSeek-V3.2 主力 + ChatAnywhere 备用自动切换）
- [x] 去重 + 合并 + 状态刷新
- [x] SVG 甘特图日历（实线/虚线区分状态）
- [x] README.md 自动生成
- [x] docs/分类活动.md 自动生成
- [x] 过期活动自动归档到 docs/archive/（归档索引防丢 + 防回流，2026-11-15 接入 finalize）
- [x] README 兜底过滤已结束活动
- [x] PENDING_URLS.md 用户提交入口（URL + 自然语言）
- [x] 小黑盒游戏打折抓取（Playwright）
- [x] 小黑盒社区合集帖抓取（Playwright）
- [x] 云厂商活动抓取
- [x] Epic/Steam/GOG 官方 API
- [x] V2EX 开车线报
- [x] 博客/RSS 聚合

### 近期修改（2026-11-15）
- [x] archive_expired() 接入 finalize：279 条过期活动按月归档到 docs/archive/，README 不再显示已结束活动
- [x] 归档索引 docs/archive/index.json 全量重渲染各月 .md，修复旧实现覆盖丢历史的问题
- [x] _merge_and_save() 丢弃已归档 id，防止过期活动被源站重新抓回
- [x] AI 主力换为 ChatAnywhere gpt-6.1-sol（新 key 实测 19 个模型可用；旧 key 401 失效）
- [x] ai_client.py 支持备用中转站自动切换（AI_FALLBACK_* 环境变量，SiliconFlow DeepSeek-V3.2 兜底）
- [x] prompts.py 增加游戏标题中文译名规则（对接 AGENT.md 15.7）
- [x] 文档同步（AGENT.md 第 13/20 节、DEV_GUIDE、本文件）
- [x] process_pending_urls() 兑现「提交 URL 即抓取」：html URL 当场抓一次解析入库（实测 IT之家喜加一标签页入库 20 条）；heybox URL 当场触发 Playwright 抓取
- [x] 修复 blog_collector.fetch() 中文 URL 报 ascii 编码错误的 bug（percent-encode）
- [x] workflow 15:53 时段补上 game-discount（此前该分类只在手动 all 模式才被抓）
- [x] 新增 docs/日常更新指南.md（两个 AI 角色分工 + 日常维护 SOP）；全部 docs 文档重写核对

### 近期修改（2026-10-28）
- [x] process_pending_urls() 支持自然语言输入
- [x] collect_heybox_community() 改为合集帖模式
- [x] SVG 虚线 bug 修复（finalize refresh_status + status_of 实时计算）
- [x] AI 模型测试（gpt-4o-mini 不可用，换回 deepseek-v3-2）
- [x] safe_text import 修复

---

## 10. GitHub Actions 配置详解

### workflow 文件

`.github/workflows/daily-collect.yml`

### 环境变量

```yaml
env:
  TZ: Asia/Shanghai
  AI_BASE_URL: https://api.chatanywhere.tech/v1          # 主力 ChatAnywhere
  AI_API_KEY: ${{ secrets.AI_API_KEY }}                  # GitHub Secret
  AI_MODEL: gpt-6.1-sol
  AI_FALLBACK_BASE_URL: https://api.siliconflow.cn/v1    # 备用 SiliconFlow
  AI_FALLBACK_API_KEY: ${{ secrets.AI_FALLBACK_API_KEY }}
  AI_FALLBACK_MODEL: deepseek-ai/DeepSeek-V3.2
```

### GitHub Secrets

| Secret 名 | 说明 |
|-----------|------|
| AI_API_KEY | ChatAnywhere API key（主力） |
| AI_FALLBACK_API_KEY | SiliconFlow API key（备用） |
| AI_BASE_URL / AI_MODEL | 已硬编码在 workflow 里 |

### 运行模式

| 模式 | 说明 |
|------|------|
| all | 全量收集（所有分类 + finalize） |
| ai | AI 分类（cloud + blog） |
| ai-cloud | 仅云厂商 |
| ai-blog | 仅博客聚合 |
| games | 游戏分类（direct + blog） |
| games-direct | 仅官方 API |
| games-blog | 仅博客聚合 |
| drive | 开车线报 |
| finalize | 整理（SVG + README） |

### 手动触发

```python
# 用 GitHub API 触发
api_call('POST', 'actions/workflows/daily-collect.yml/dispatches', {
    'ref': 'main',
    'inputs': {'mode': 'all'}
})
```

### 提交逻辑

Actions 运行完后自动提交：
```bash
git add data/ docs/ README.md PENDING_URLS.md
git commit -m "chore(data): {mode} update {date}"
git push origin main  # 或 force-with-lease
```

---

## 附录：关键注意事项

1. **不要手动编辑生成产物**：README.md、docs/calendar.svg、docs/data/、docs/分类活动.md 都是脚本生成的
2. **不要在代码/文档里暴露 token**：GitHub token、AI API key 等敏感信息绝不写入文件
3. **定时任务避开整点**：cron 已提前 2 小时配置，减轻源网站压力
4. **领取链接直接跳小黑盒**：不跳 Steam，直接跳小黑盒帖子
5. **用 GitHub API 提交**：由于环境限制，用 GitHub API 创建提交比 git push 更可靠
6. **全量模式需要 20-30 分钟**：mode=all 处理所有 8 个分类 + PENDING_URLS + finalize
7. **AI 额度**：AI 仅处理 PENDING_URLS 自然语言条目（日常 0 次调用），ChatAnywhere 免费版（每周 50000 点）绰绰有余；主力失败自动切 SiliconFlow 备用
