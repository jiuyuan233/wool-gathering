# 开发文档（交接文档）

> 本文档是给**接手开发的 AI 或人类**看的完整交接资料。包含项目全貌、架构设计、
> 每个文件职责、AI 工作流程、用户画像、遗留问题和开发指南。
> 
> **最后更新**：2026-10-28
> **当前 AI 模型**：deepseek-v3-2（ChatAnywhere 免费版）
> **当前状态**：所有核心功能已实现，部分遗留问题待解决（见第 8 节）

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
- **AI**：ChatAnywhere 中转站（OpenAI 兼容协议），模型 `deepseek-v3-2`
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
│  main() → process_pending_urls() → process_category()    │
│         → finalize() → archive_expired()                 │
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
│          AI 抽取 (ai_client.py)           │
│  网页内容 → AI 理解 → 结构化活动 JSON     │
│  模型: deepseek-v3-2 (ChatAnywhere)       │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│        dedup.py (去重 + 合并 + 状态)      │
│  normalize_activity → merge → refresh_   │
│  status → dedupe_within                  │
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

### scripts/blog_collector.py（博客+小黑盒抓取，28152 字节）

**职责**：从博客、RSS、社区聚合网站抓取活动信息。

**关键函数**：

| 函数 | 职责 |
|------|------|
| `collect_blog_activities(category)` | 从 sources.json 里该分类的博客源抓取 |
| `collect_heybox_discounts()` | 小黑盒游戏打折（SPA，需 Playwright） |
| `collect_heybox_community(category)` | 小黑盒社区合集帖（SPA，需 Playwright） |
| `parse_itad/itchio/ggdeals/reddit/rss/v2ex` | 各平台解析器 |

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
- `AI_BASE_URL`：中转站地址（`https://api.chatanywhere.org/v1`）
- `AI_API_KEY`：API key（存在 GitHub Secret 里）
- `AI_MODEL`：模型名（`deepseek-v3-2`）

### scripts/prompts.py（AI 提示词，5960 字节）

**职责**：定义给 AI 的系统提示词和 prompt 模板。

**关键内容**：
- `SYSTEM_PROMPT`：AI 的完整操作手册（什么算薅羊毛活动、什么不算、输出格式）
- `build_extract_messages()`：从种子源抽取活动的 messages
- `build_search_messages()`：联网搜索活动的 messages

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

AI 负责理解网页内容并抽取薅羊毛活动。脚本抓取网页内容后喂给 AI，AI 返回结构化 JSON。

### 调用链

```
collect.py process_category()
  → blog_collector.py collect_blog_activities()
    → sources_manager.py fetch_source()  # 抓网页
    → ai_client.py chat_json()           # 调 AI
      → prompts.py build_extract_messages()  # 组装 prompt
      → ChatAnywhere API (deepseek-v3-2)     # 实际调用
    → 返回 JSON → 解析为活动列表
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
2. 让 AI 联网搜索该产品的免费福利
3. 返回活动信息，直接写入 activities.json

### AI 模型选择

- **当前**：`deepseek-v3-2`（ChatAnywhere 免费版）
- **已测试不可用**：`gpt-4o-mini`（返回 401 Unauthorized）
- **限制**：免费版每周 50000 点 + 每天 100 次请求
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
├── sources.json              # 61 个信息源
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

### 环境限制（重要！）

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

## 8. 遗留问题

### 问题 1：PENDING_URLS 自然语言处理依赖 AI 可用性

**状态**：代码已实现，但 AI 调用失败时无法处理

**详情**：
- `_process_natural_language()` 用 AI 理解自然语言描述
- 如果 AI 调用失败（如 401、限流），自然语言无法处理
- 当前 deepseek-v3-2 可用，但能力有限，可能无法准确理解复杂描述

**建议**：
- 换更强的 AI 模型（需要 ChatAnywhere 支持）
- 或增加 fallback：AI 失败时用关键词匹配创建简单活动

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

**状态**：潜在问题

**详情**：
- `collect_blog_activities()` 调用 AI 抽取活动
- 如果 AI 调用失败抛异常，可能导致 `process_category` 中断
- `collect_heybox_community()`（不依赖 AI）可能没机会执行

**建议**：
- 在 `process_category` 里给 `collect_blog_activities` 加 try-except
- 确保 AI 失败不影响非 AI 的收集逻辑

### 问题 4：Qoder 活动未出现在 SVG 日历

**状态**：待解决

**详情**：
- Qoder 源在 sources.json 里（`https://docs.qoder.cn/qoder/overview`）
- 但 data/ai/activities.json 里 0 条 Qoder 活动
- 可能原因：Qoder 页面是 JS 渲染的，抓到空壳；或 AI 没抽取到

**建议**：
- 检查 Qoder 页面是否需要 Playwright 渲染
- 或在 PENDING_URLS.md 里用自然语言让 AI 直接创建活动

### 问题 5：gpt-4o-mini 在 ChatAnywhere 免费版不可用

**状态**：已确认

**详情**：
- 测试 gpt-4o-mini 返回 401 Unauthorized
- ChatAnywhere 免费版可能只支持 deepseek 系列模型
- 用户决定不换模型，继续用 deepseek-v3-2

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
- [x] AI 抽取薅羊毛活动（deepseek-v3-2）
- [x] 去重 + 合并 + 状态刷新
- [x] SVG 甘特图日历（实线/虚线区分状态）
- [x] README.md 自动生成
- [x] docs/分类活动.md 自动生成
- [x] 过期活动归档到 docs/archive/
- [x] PENDING_URLS.md 用户提交入口（URL + 自然语言）
- [x] 小黑盒游戏打折抓取（Playwright）
- [x] 小黑盒社区合集帖抓取（Playwright）
- [x] 云厂商活动抓取
- [x] Epic/Steam/GOG 官方 API
- [x] V2EX 开车线报
- [x] 博客/RSS 聚合

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
  AI_BASE_URL: https://api.chatanywhere.org/v1
  AI_API_KEY: ${{ secrets.AI_API_KEY }}  # GitHub Secret
  AI_MODEL: deepseek-v3-2
```

### GitHub Secrets

| Secret 名 | 说明 |
|-----------|------|
| AI_API_KEY | ChatAnywhere API key |
| AI_BASE_URL | 中转站地址（已硬编码在 workflow 里） |
| AI_MODEL | 模型名（已硬编码在 workflow 里） |

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
7. **AI 免费版限制**：每周 50000 点 + 每天 100 次请求，用 deepseek-v3-2 省额度
