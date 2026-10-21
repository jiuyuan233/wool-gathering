# 薅羊毛情报站维护规范（AGENT.md）

> 本文档是给**任何 AI 或人类维护者**看的操作规范。目标：哪怕是不那么聪明的 AI，
> 照着本文档一步一步做，也能正确维护这个薅羊毛情报站，不会搞乱数据或渲染。
>
> **优先级**：本文档是项目级规则，优先级高于全局 AGENT.md。

---

## 0. 一句话理解这个项目

GitHub Actions 每天分六个时段（分散全天、避开整点）自动抓取 AI/云服务优惠、开源免费工具、
开车线报、游戏喜加一，去重合并后生成 README + SVG 甘特图日历，自动 commit 推送回仓库。
维护者的任务是：**改规则、修 bug、加源、跑流程、推结果**，不要手动改 `data/` 或 `docs/` 里的生成产物。

---

## 1. 仓库结构（只需记住这几个关键文件）

```
wool-gathering/
├── AGENT.md                      # 本文件（维护规范）
├── .github/workflows/daily-collect.yml  # Actions：六时段定时任务（分散全天避开整点）
├── scripts/                      # 所有 Python 脚本
│   ├── collect.py                # 主入口（Action 调这个）
│   ├── blog_collector.py         # 博客/V2EX/Reddit/ITAD/itch.io 抓取 + 分类规则
│   ├── cloud_collector.py        # 云厂商活动抓取（华为云/阿里云/腾讯云）
│   ├── direct_collector.py       # Epic/Steam/GOG 官方 API 抓取
│   ├── dedup.py                  # 规范化 + 去重 + 合并
│   ├── calendar_generator.py     # 生成 README + 前端 JSON（含车型子分类）
│   ├── svg_calendar.py           # 生成 SVG 甘特图（含文字防重叠）
│   ├── utils.py                  # 工具函数（日期/ID/状态）
│   └── readme_template.md        # README 模板
├── data/                         # 原始数据（脚本写，人别手改）
│   ├── ai/activities.json
│   ├── open-source/activities.json
│   ├── drive/activities.json
│   ├── games/activities.json
│   └── sources.json              # 种子源列表（可手改）
└── docs/                         # 生成产物（脚本写，人别手改）
    ├── calendar.svg              # README 嵌入的甘特图
    └── data/{activities,meta}.json
```

**铁律**：`data/*/activities.json`、`docs/calendar.svg`、`docs/data/*`、`README.md` 都是脚本生成的，
**不要手动编辑**。要改数据，改 `scripts/` 里的规则然后重跑；要改源，改 `data/sources.json`。

---

## 2. 八大分类规则（核心，必须背下来）

| 类别 | 代号 | 包含什么 | 谁来识别 |
|------|------|---------|---------|
| AI / 云服务优惠 | `ai` | 云厂商代金券/免费额度/打折、AI 中转站优惠、博客里讲云/AI 优惠的帖 | `cloud_collector.py` + `blog_collector.py`（默认归 ai，除非命中其他规则） |
| 购物优惠 | `shopping` | 双11打折、红包等纯购物促销 | `blog_collector.is_shopping()` |
| 视频会员 | `video-vip` | 爱奇艺/腾讯视频等视频 VIP 优惠 | `blog_collector.is_video_vip()` |
| 网盘会员 | `netdisk-vip` | 夸克/百度等网盘 SVIP 优惠 | `blog_collector.is_netdisk_vip()` |
| 开源免费工具 | `open-source` | 一直免费的开源软件/GitHub 工具（非限时促销） | `blog_collector.is_open_source()` |
| 开车线报 | `drive` | 群发车/上车/拼车/线报类帖子 | `blog_collector.is_drive_post()` |
| 游戏喜加一 | `games` | Epic/Steam/GOG/itch.io 免费游戏、限免、giveaway | `direct_collector.py` + `blog_collector.py` |
| 游戏打折 | `game-discount` | Steam 新品节/尖叫节等打折汇总（史低/新史低/一折以下） | `blog_collector.collect_heybox_discounts()`（小黑盒 SPA + Playwright 渲染） |

### 2.1 分类判定顺序（在 `blog_collector.parse_blog_articles` 里）

1. 先判 `is_open_source(title)` → 命中归 `open-source`
2. 再判 `is_shopping(title)` → 命中归 `shopping`
3. 再判 `is_video_vip(title)` → 命中归 `video-vip`
4. 再判 `is_netdisk_vip(title)` → 命中归 `netdisk-vip`
5. 否则归调用时传入的 `category`（ai 模式传 ai，games 模式传 games）

### 2.2 关键词定义（在 `blog_collector.py` 顶部）

- **开车线报** `DRIVE_HINTS = ["开车","发车","上车","拼车","线报","羊毛群","薅羊毛","白嫖群"]`
- **开源工具** `OPEN_SOURCE_HINTS = ["开源","github 上发现","在 github 发现","免费小工具","工具箱"]`
  且不含 `OPEN_SOURCE_EXCLUDE = ["限时","打折","优惠","年卡","vip","赠送","周年庆","半价"]`（含促销词的不算纯开源）
- **购物** `SHOPPING_HINTS = ["双11","双 11","红包","wps","vmware","videoproc","复旦","周年庆","打折好价","codex"]`
- **视频会员** `VIDEO_VIP_HINTS = ["爱奇艺","腾讯视频"]`
- **网盘会员** `NETDISK_VIP_HINTS = ["夸克网盘","百度网盘","网盘svip","网盘 svip","网盘会员"]`
- **价值词** `WOOL_VALUE_WORDS`：限免/喜加一/代金券/0元/免费领/打折/优惠/…（决定博客帖是否收录）
- **排除模式** `WOOL_EXCLUDE_PATTERNS`：讨论帖/请教/周刊等误判（正则）

### 2.3 开车线报车型子分类（在 `calendar_generator.CAR_TYPES`）

drive 分区在 README 里会按车型子分组渲染，顺序即列表顺序：

1. **云服务器车**：云服务器/ecs/主机/vps/轻量/华为云/阿里云/腾讯云/…
2. **AI 车**：ai/codex/deepseek/大模型/chatgpt/claude/gemini/gpt/通义/文心/kimi/智谱
3. **会员车**：vip/svip/会员/年卡/网盘/视频/音乐/爱奇艺/腾讯视频/…
4. **软件工具车**：软件/工具/专业版/激活/序列号/license/office/ide/jetbrains
5. **其他车**：以上都不命中

`guess_car_type(title)` 按顺序匹配，先命中先归。**云服务器车优先于 AI 车**（即使标题同时含两者）。

---

## 3. 开源工具的特殊规则（容易搞错，重点记）

开源免费工具 = **一直免费**的软件，不是限时活动。所以：

1. **end_date 必须为空**：`blog_collector._activity()` 生成开源条目时 `end_days` 参数不传，end_date 留空。
   如果历史数据里开源条目有假 end_date，必须一次性脚本清空（已清理过一次）。
2. **不进 SVG 时间轴**：`svg_calendar.generate_svg()` 显式排除 `category == "open-source"`。
   SVG 画 ai + shopping + video-vip + netdisk-vip + drive + games 六类有日期的活动。
3. **README 时间列显示"长期免费"**：`calendar_generator._md_table()` 里 end_date 为空时显示"长期免费"而非假日期。
4. **仍出现在 README 表格里**：开源工具在 README 的"开源免费工具"分区正常列表，只是不进甘特图。

---

## 4. SVG 日历规则（防文字重叠，重点记）

`svg_calendar.py` 里的关键常量和函数：

- `LEFT_LABEL_W = 240`：左侧活动名留 240px
- `_visual_width(s)`：计算显示宽度，权重 = 全角字符 1.0 / 半角 0.55 / emoji 1.6
- `_truncate_label(s, max_units=16.0)`：按显示宽度截断，超限加省略号
- `_esc(s)`：**先截断再转义**（顺序不能反，否则 html.unescape 双重转义会出 bug）
- **textLength 强制压缩**：每个 `<text>` 加 `textLength="{可用像素}"` + `lengthAdjust="spacingAndGlyphs"`，
  浏览器强制把文字压缩到该宽度内，这是杜绝与时间横条重叠的最可靠保障
- 字号 12px，行高 28px，横条高 18px

**如果出现文字与横条重叠**：检查 `_esc` 是否先截断再转义、textLength 是否生效、`LEFT_LABEL_W` 是否够宽。
不要靠调字号或行高硬挤，textLength 才是根本解。

### 4.1 时间轴跨度一个月 + 分区显示

**日历显示所有有时间限制的活动**（除开源项目外），时间轴跨度固定为当月：

- 时间轴刻度范围 = 当月 1 日到月末（前后留 1 天边距）
- 显示所有有 `start_date` 和 `end_date` 的活动，不管持续时间多长
- 开源项目（无 `end_date`）不显示在时间轴
- 超过一个月持续时间的活动：横条顶满整个跨度（clamp 到时间轴范围）
- 不在当月的活动：横条贴在对应边界

**按分区分组显示**：

- 分区顺序：AI / 云服务 → 开车线报 → 游戏喜加一
- 每个分区有标题行（带活动条数）
- 分区内按 `end_date` 升序排列（快结束的排上面）

**README 分区逻辑**（`calendar_generator.generate_readme`）：

1. 限时活动按 category 分区：🤖 AI / 云服务优惠、🚗 开车线报、🎮 游戏喜加一
2. 长期活动（含 open-source + is_long_term）统一归到「♾️ 长期免费」分区
3. open-source 不再单独成区，已合并进长期免费分区

**长期免费判定**（`utils.is_long_term(a, today, threshold_days=90)`）用于 README 分区：

- 无 `end_date`（永久免费，如开源工具）→ 长期
- `end_date` 距今超过 90 天（约 3 个月）→ 长期
- 其余 → 限时

---

## 5. 更新流程（六时段分散全天，避开整点）

GitHub Actions 每天自动跑六次（`.github/workflows/daily-collect.yml`），任务分散到全天，
**所有 cron 都避开整点**（分钟非 0），减轻免费源网站压力：

| 北京时间 | UTC | cron | 模式 | 做什么 |
|---------|-----|------|------|-------|
| 06:17 | 22:17 | `17 22 * * *` | `ai-cloud` | 仅抓云厂商（华为云/阿里云/腾讯云） |
| 09:23 | 01:23 | `23 1 * * *` | `ai-blog` | 仅抓博客聚合（ai 板块，含 open-source 分流） |
| 11:41 | 03:41 | `41 3 * * *` | `drive` | V2EX 开车线报 |
| 14:37 | 06:37 | `37 6 * * *` | `games-direct` | 仅抓 Epic/Steam/GOG 官方 API |
| 16:53 | 08:53 | `53 8 * * *` | `games-blog` | 仅抓 ITAD/itch.io/Reddit/ggdeals |
| 20:47 | 12:47 | `47 12 * * *` | `finalize` | 整理：生成 SVG 日历 + 前端 JSON + README |

**设计原则**：不集中在一个时间段请求免费源网站，把请求量分散到全天 6 个时段，间隔约 2-3 小时。

### 5.1 命令对照（子模式）

```bash
# 细粒度子模式（workflow 定时用这些，分散请求）
python scripts/collect.py ai-cloud       # 仅云厂商
python scripts/collect.py ai-blog        # 仅博客（ai 板块）
python scripts/collect.py games-direct   # 仅 Epic/Steam/GOG 官方 API
python scripts/collect.py games-blog     # 仅 ITAD/itch.io/Reddit
python scripts/collect.py drive          # V2EX 开车线报
python scripts/collect.py finalize       # 整理：生成 SVG + README

# 粗粒度模式（手动触发或调试用，= 对应子模式之和）
python scripts/collect.py ai         # = ai-cloud + ai-blog
python scripts/collect.py games      # = games-direct + games-blog
python scripts/collect.py all        # 全部（手动触发用）
```

### 5.2 collect.py 内部流程

1. `process_category(cat)`：抓取 → `normalize_activity` 规范化 → 按 `category` 字段分流 → `_merge_and_save` 去重合并写回
2. `finalize()`：读所有 `data/*/activities.json` → `generate_docs_data()` 生成前端 JSON → `generate_svg()` 生成 SVG → `generate_readme()` 生成 README
3. `merge(old, new, today)`：**旧值优先**——已存在的字段不被新数据覆盖（尤其 end_date 一旦写入不覆盖）；
   status 按起止日期每天重算（active/upcoming/ended）

### 5.3 Actions 提交规则

workflow 最后一步：`git add data/ docs/calendar.svg docs/data/ README.md` → 有 diff 才 commit →
commit message 格式 `chore(data): {mode} update {YYYY-MM-DD}` → `git pull --rebase` → `git push`。

---

## 6. 本地调试（照着做就能跑）

```bash
cd /workspace/wool-gathering
pip install -r scripts/requirements.txt

# 跑整理阶段（最安全，不抓网络，只读本地数据生成 SVG + README）
python scripts/collect.py finalize

# 跑某个板块（会抓网络，可能慢/失败，建议加超时意识）
python scripts/collect.py ai
python scripts/collect.py games

# 看结果
ls -la data/*/activities.json docs/calendar.svg README.md
```

**本地跑 finalize 会修改 README.md / docs/calendar.svg / docs/data/**，这些是生成产物。
如果只是调试看效果，跑完 `git reset --hard origin/main` 丢弃即可（Actions 会自己跑）。
如果要推送，先确认 `docs/data/meta.json` 的 `repository` 字段不是空字符串（本地没 `GITHUB_REPOSITORY` 环境变量会变空）。

---

## 7. 推送方式（网络不稳要重试）

```bash
# 方式一：git push（网络不稳，失败就重试 2-3 次）
git add -A && git commit -m "feat: 你的改动说明" && git push

# 方式二：GitHub Contents API（更稳，但需要 token）
# token 可从 git remote URL 提取：git remote get-url origin 里含 ghp_xxx@
```

**推送前必做**：
1. `git pull --rebase origin main` 拉最新（Actions 可能刚推过）
2. 确认没有改 `data/` / `docs/` 里的生成产物（除非是脚本跑出来的）
3. commit message 用中文，前缀规范：`feat:` 新功能 / `fix:` 修 bug / `chore:` 杂项 / `docs:` 文档

---

## 8. 数据格式约定

每条活动 JSON（`data/{cat}/activities.json` 是数组）：

```json
{
  "id": "稳定ID（标题+URL哈希，去重依据）",
  "title": "活动标题",
  "category": "ai | open-source | drive | games",
  "source_url": "来源页",
  "claim_url": "领取页",
  "start_date": "YYYY-MM-DD 或空",
  "end_date": "YYYY-MM-DD 或空（开源工具必须空）",
  "value": "福利描述",
  "requirements": ["条件1", "条件2"],
  "description": "说明",
  "tags": ["标签"],
  "discovered_at": "ISO 时间",
  "last_seen": "YYYY-MM-DD",
  "status": "active | upcoming | ended（按日期自动算）"
}
```

**铁律**：
- `id` 必须稳定（同活动每次抓取 id 不变），否则去重失效
- `status` 不要手写，由 `utils.status_of(start, end, today)` 按日期算
- `end_date` 空 = 长期免费（仅开源工具允许）；非空必须是 `YYYY-MM-DD`
- `merge` 旧值优先：已存在字段不覆盖，所以清理假 end_date 要写一次性脚本直接改文件

---

## 9. 禁止事项（做了会搞乱项目）

1. **禁止手动编辑** `data/*/activities.json`、`docs/calendar.svg`、`docs/data/*`、`README.md`——这些都是脚本生成的，改了会被下次跑覆盖或造成不一致。要改数据，改脚本规则再跑。
2. **禁止给开源工具填 end_date**——开源是长期免费，end_date 必须空，否则会进 SVG 时间轴显示假日期。
3. **禁止 rebase 或强推远程 main**——Actions 每天在 main 上 commit，rebase 会丢 Actions 的数据更新 commit。要同步用 `git pull --rebase`（本地 rebase 到远程之上，不破坏远程历史）。
4. **禁止改 `merge` 的"旧值优先"语义**——这是防止新抓数据覆盖已确认字段的保护。要清理错误字段，写一次性脚本。
5. **禁止在 SVG 里靠调字号/行高防重叠**——用 `textLength` 强制压缩才是根本解（见第 4 节）。
6. **禁止把开车/线报关键词加到 `WOOL_EXCLUDE_PATTERNS`**——开车帖由 `is_drive_post` 识别后归 drive 分区，不能再当误判排除。
7. **禁止删 `CATEGORIES` 里的类别**——四个类别 `["ai","open-source","drive","games"]` 是全项目共识，删了会导致数据无处归。

---

## 10. 常见问题

**Q: Actions 跑了但某板块没更新？**
A: 看 Actions 日志。常见：① 网络抓取失败（腾讯云反爬返回 JS 挑战页，靠缓存回退保留数据）；② 种子源页面结构变了；③ 该板块当天确实没新活动。不是 bug，是没新数据。

**Q: SVG 文字和横条重叠了？**
A: 检查 `svg_calendar._esc` 是否先截断再转义、textLength 是否加上、`LEFT_LABEL_W` 是否够。不要调字号硬挤。

**Q: 开源工具在 SVG 里显示了假日期？**
A: 它的 end_date 没清空。写一次性脚本把 `data/open-source/activities.json` 里所有条目的 `end_date` 置空，再跑 finalize。

**Q: 想加新的开车线报源？**
A: 改 `data/sources.json` 加一条，或在 `blog_collector.collect_blog_activities` 里加抓取逻辑。开车帖靠 `is_drive_post` 识别，不用手动标 category。

**Q: 想加新的车型子分类？**
A: 改 `calendar_generator.CAR_TYPES` 列表，加 `(标签, [关键词])`。顺序即分组顺序，先命中先归。

**Q: 本地跑 finalize 后 meta.json 的 repository 是空字符串？**
A: 本地没 `GITHUB_REPOSITORY` 环境变量。要么 `export GITHUB_REPOSITORY="jiuyuan233/wool-gathering"` 再跑，要么别推本地跑的产物（Actions 跑时会自动填）。

---

## 11. 给维护 AI 的行为准则

1. **先读本文档再动手**——不要凭猜测改东西。
2. **以远程 origin/main 为准**——本地历史可能因 rebase 搞乱过，动手前先 `git fetch && git reset --hard origin/main`。
3. **小步快跑**——改一处跑一次 finalize 验证，不要攒一堆改动一起推。
4. **不确定就问**——分类规则、end_date 语义、推送方式有歧义时，问用户，别瞎猜。
5. **生成产物别 commit**——本地调试跑出来的 `data/` `docs/` `README.md` 改动，调试完 `git reset --hard` 丢弃，让 Actions 自己跑。只有改了 `scripts/` 规则或 `sources.json` 才需要 commit 推送。
6. **中文回复**——所有回复、commit message、文档都用简体中文。

---

## 12. 示范：实跑一次 finalize 流程

下面是一次真实的 `finalize` 运行示范（21:00 时段的任务），供维护 AI 参考。

### 步骤 1：确认起点与远程一致

```bash
$ git log --oneline -1
31ff6a0 feat: 开源工具退出活动时间轴，时间列显示长期免费
$ git status --short
?? AGENT.md          # 只有新文档未跟踪，working tree 干净
```

### 步骤 2：安装依赖

```bash
$ pip install -r scripts/requirements.txt
```

### 步骤 3：执行 finalize

```bash
$ python scripts/collect.py finalize
[INFO] ============================================================
[INFO] 开始每日整理
[INFO] 运行时间: 2026-10-19T16:07:08+08:00
[INFO] ============================================================
[INFO] [ai] 当前共 18 条（active=18）
[INFO] [open-source] 当前共 12 条（active=12）
[INFO] [drive] 当前共 2 条（active=2）
[INFO] [games] 当前共 69 条（active=65）
[INFO] 生成前端数据...
[INFO] 已生成 docs/data/activities.json (101 条) 和 meta.json
[INFO] 生成 SVG 日历...
[INFO] 已生成 SVG 日历 calendar.svg（89 条有时间轴，0 条无日期，开源工具 12 条长期免费不显示）
[INFO] 生成 README...
[INFO] 已生成 README.md
[INFO] 整理完成
```

### 步骤 4：验证产物

```bash
$ git diff --stat
 README.md                 |  26 ++--
 docs/calendar.svg         | 323 +++++++++++++++++++---------------------------
 docs/data/activities.json |  96 +++++------
 docs/data/meta.json       |   4 +-
```

关键验证点（全部通过）：
- SVG 副标题：`共 101 条（89 条有时间轴，开源工具长期免费不显示）` → 开源已正确排除
  - 89 = ai 18 + drive 2 + games 69，开源 12 条不进时间轴
- README 开源分区：时间列显示 `长期免费` 而非假日期
- textLength 属性：标题/副标题 2 个；活动行条件性添加（文字超长才加，当前都不超）
- 活动横条 180 个 = 89 条 × 2（背景条 + 进度填充）

### 步骤 5：注意本地跑的坑

```bash
$ python3 -c "import json; print(json.load(open('docs/data/meta.json'))['repository'])"
（空字符串）
```

本地跑 `finalize` 时 `docs/data/meta.json` 的 `repository` 字段会变空（没 `GITHUB_REPOSITORY` 环境变量）。
**所以本地跑的产物不要直接推送**，否则会把远程 meta.json 的 repository 覆盖成空。

### 步骤 6：清理本地产物改动

按本规范第 11 节第 5 条，本地调试跑出来的 `data/` `docs/` `README.md` 改动应丢弃，让 Actions 自己跑：

```bash
$ git checkout -- README.md docs/        # 丢弃产物改动
# 只保留 AGENT.md 等源文件改动用于提交
```

### 结论

一次完整的 finalize 流程：**1 条命令 → 读 4 个数据文件 → 生成 4 个产物 → 验证 3 个关键点 → 清理本地产物**。
维护 AI 照着这 6 步走，不会出错。如果要跑 `ai` 或 `games` 模式（会抓网络），步骤相同，只是步骤 3 换命令、
步骤 4 验证点换成"新增了多少条数据"。

---

## 13. AI 中转站配置与手动触发

项目用 OpenAI 兼容协议的 AI 中转站辅助信息抽取（`scripts/ai_client.py`）。
workflow 已默认配置 ChatAnywhere 中转站 + `deepseek-v3-2` 弱模型，**只需配一个 GitHub Secret 即可跑通**。

### 13.1 当前配置（在 `.github/workflows/daily-collect.yml` 的 env 里）

| 环境变量 | 值 | 说明 |
|---------|-----|------|
| `AI_BASE_URL` | `https://api.chatanywhere.org/v1` | ChatAnywhere 国外接入点（Action runner 在海外，用 .org；国内调试用 .tech） |
| `AI_API_KEY` | `${{ secrets.AI_API_KEY }}` | 从 GitHub Secret 读，**不 commit 到代码** |
| `AI_MODEL` | `deepseek-v3-2` | 弱模型，最便宜之一（input 0.0012/1K，output 0.0018/1K） |

### 13.2 配置 GitHub Secret（必须做，否则 AI 调用失败）

1. 仓库 **Settings → Secrets and variables → Actions → New repository secret**
2. Name 填 `AI_API_KEY`，Value 填你的 ChatAnywhere API Key（形如 `sk-xxx`）
3. 点 Add secret 保存。workflow 会自动读取，无需改代码。

> fork 的仓库 secrets 不会从上游继承，必须自己配。

### 13.3 换其他中转站（可选）

框架不绑定具体厂商，任意 OpenAI 协议兼容的中转站都能用。编辑 `.github/workflows/daily-collect.yml` 的 env 改 `AI_BASE_URL`/`AI_MODEL`：

| 中转站 | `AI_BASE_URL` | `AI_MODEL` | 说明 |
|--------|---------------|------------|------|
| ChatAnywhere（当前默认） | `https://api.chatanywhere.org/v1` | `deepseek-v3-2` | 免费版每周 50000 点 + 每天 100 次 |
| DeepSeek 官方 | `https://api.deepseek.com/v1` | `deepseek-chat` | 便宜、中文好、有 function calling |
| 智谱 BigModel | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | 免费额度大 |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` | 阿里云百炼 |

### 13.4 手动触发 workflow（调试 / 首次运行）

1. 进仓库 **Actions** 标签页
2. 左侧选 **Daily Collect** workflow
3. 点右上角 **Run workflow** 按钮 → 选 main 分支 → 点绿色 Run workflow 按钮
4. 等绿勾出现（约 2-5 分钟），点进去可看每步日志
5. 运行成功后，README 顶部 SVG + 分类表格 + `data/*/activities.json` 自动更新并 commit

> workflow 会按当前 UTC 小时自动判断跑哪个子模式（见第 5 节六时段表）。手动触发默认跑 `all`（全量）。

### 13.5 ChatAnywhere 免费版限制（用 ChatAnywhere 时必看）

- 每周 50000 点免费配额 + 每天 100 次请求次数配额
- **用弱模型 `deepseek-v3-2` 省额度**，别用 pro/max/gpt-4，超出额度要付费
- 每次跑约调 AI 30-50 次（51 个种子源抽取 + 联网搜索补充），免费额度基本够

### 13.6 已收录的 AI 信息源

- **腾讯 WorkBuddy**（workbuddy.tencent.com）：AI Agent 办公助手，已加到 `cloud_collector.CLOUD_PAGES`（第 11 条）抓取 + 种子数据
- ChatAnywhere 中转站本身**不再作为优惠条目收录**到 `data/ai/activities.json`（曾收录后删除，仅保留 workflow 配置用于 AI 抽取辅助）

### 13.7 相关文件

- `scripts/ai_client.py`：OpenAI 兼容客户端，读 `AI_BASE_URL`/`AI_API_KEY`/`AI_MODEL` 环境变量，默认 model `gpt-4o-mini`
- `.github/workflows/daily-collect.yml`：workflow env 配了 AI（key 从 secret 读）
- `scripts/cloud_collector.py`：`CLOUD_PAGES` 11 条（华为云 3 + 阿里云 3 + 腾讯云 4 + 腾讯 WorkBuddy 1）

---

## 14. 游戏平台介绍

详细的游戏平台介绍见 **[docs/GAME_PLATFORMS.md](docs/GAME_PLATFORMS.md)**，包含：
- 当前启用的 6 个游戏源（Epic/Steam/GOG/itch.io/ITAD/Reddit）的抓取方式
- sources.json 里登记的其他 15 个平台（可扩展启用）
- 各平台特点对比、免费游戏类型、抓取可靠性
- 如何启用新平台的步骤

---

## 15. AI 操作指南：手动新增/更新活动信息

当用户要求手动新增或更新某条活动信息时，按以下步骤操作。

### 15.1 判断活动属于限时还是长期

用 `utils.is_long_term(a)` 判定（阈值 90 天，约 3 个月）：

| 条件 | 判定 | README 归属 | SVG 时间轴 |
|------|------|------------|-----------|
| 无 `end_date` | 长期 | 「♾️ 长期免费」 | 不显示 |
| `end_date` 距今 > 90 天 | 长期 | 「♾️ 长期免费」 | 显示（在对应分区分组） |
| `end_date` 距今 <= 90 天 | 限时 | 按 category（AI/开车/游戏） | 显示 |

**日历显示所有有时间限制的活动**（有 `end_date` 的），不管持续时间多长：

- 时间轴跨度固定为当月（刻度只显示当月 1 日到月末）
- 超过一个月持续时间的活动：横条顶满整个跨度
- 不在当月的活动：横条贴在对应边界
- 按分区分组：AI / 云服务 → 开车线报 → 游戏喜加一
- 分区内按 `end_date` 升序排列（快结束的排上面）
- 开源项目（无 `end_date`）不显示在时间轴

### 15.2 手动新增一条活动

1. 确定目标分类目录：`data/ai/`、`data/shopping/`、`data/video-vip/`、`data/netdisk-vip/`、`data/drive/`、`data/games/`、`data/open-source/`
2. 读对应的 `activities.json`，追加一条活动对象：

```json
{
  "id": "可读前缀-md5hash前10位",
  "title": "活动标题",
  "category": "ai",
  "source_url": "来源页面 URL",
  "claim_url": "领取页面 URL",
  "start_date": "2026-10-19",
  "end_date": "2026-12-31",
  "value": "福利价值描述",
  "requirements": ["注册账号"],
  "description": "来源: xxx",
  "tags": ["blog", "xxx"],
  "discovered_at": "2026-10-19",
  "last_seen": "2026-10-19",
  "status": "active"
}
```

3. **永久免费活动**：`end_date` 留空（不填），自动归到长期免费分区
4. **长期但非永久**：`end_date` 填距今 > 90 天的日期（如 `2027-12-31`），也归到长期免费分区
5. **限时活动**：`end_date` 填距今 <= 90 天的日期，显示在当月时间轴（如与当月有交集）

### 15.3 手动更新已有活动

1. 读 `data/<分类>/activities.json`，按 `id` 或 `title` 找到目标活动
2. 修改需要更新的字段（如 `end_date`、`value`、`claim_url`）
3. 更新 `last_seen` 为当天日期
4. 手动改完直接写文件即可（不走 merge，merge 是旧值优先）

### 15.4 改完后重新生成产物

```bash
cd /workspace/wool-gathering
python3 scripts/collect.py finalize
```

重新生成：`docs/calendar.svg`（时间轴跨度一个月，显示全部限时活动，按分区分组）+ `docs/data/`（前端 JSON）+ `README.md`（含长期免费分区）

### 15.5 提交推送

```bash
git add data/ docs/ README.md CHANGELOG.md AGENT.md
git commit -m "feat: 描述你的改动"
git push origin main
```

### 15.6 验证清单

- SVG 标题显示「活动时间轴（YYYY年M月）」
- SVG 有 7 个分区标题行（AI/购物/视频会员/网盘会员/开车/游戏/游戏打折），分区内快结束的排上面
- 超过一个月的活动横条顶满整个跨度
- 无 `end_date` 的活动不在 SVG 时间轴，在 README「♾️ 长期免费」分区
- 有 `end_date` 的活动都在 SVG 时间轴（不管多长时间）
- 总条数 = SVG 显示条数 + 开源工具条数
- 游戏分区英文标题后附中文翻译（格式 `英文原名 ｜中文译名`）

### 15.7 游戏标题中文翻译规则

游戏喜加一分区的活动标题常为英文（Epic/Steam/itch.io 独立游戏），需在原标题后附中文翻译。

**格式**：`原标题 ｜中文译名`

例：
- `Epic 免费游戏: Bad Cheese ｜坏奶酪`
- `[itch.io] Offrecord Episode 1（限免） ｜非官方记录第一章`
- `[Steam] (Game) Dumb Ways to Build（Reddit-FreeGameFindings） ｜蠢蛋建造法`

**翻译原则**：
1. 有官方中文译名的用官方译名（如 Castlevania → 恶魔城，Monument Valley → 纪念碑谷）
2. 无官方译名的按含义翻译（如 Bad Cheese → 坏奶酪，The Wrong Way → 逆行）
3. 纯音译无意义时保留英文（如 Pdm）
4. 标题已有中文的无需再加（如 `Agent A - 伪装游戏`）

**操作步骤**：
1. 打开 `data/games/activities.json`
2. 找到含英文且无 `｜` 的标题
3. 在标题末尾加 ` ｜中文译名`（注意｜前有一个空格）
4. 运行 `python3 scripts/collect.py finalize` 重新生成产物
5. 验证 README 游戏表格标题含中文翻译
6. 提交推送

### 15.8 小黑盒游戏打折信息操作指南

小黑盒（xiaoheihe.cn）是游戏社区 SPA，分享帖含 Steam 新品节/尖叫节打折汇总（史低/新史低/一折以下）。需 Playwright 渲染才能获取内容。

**数据流**：
1. `data/sources.json` 里 `type=heybox` 的源 → `blog_collector.collect_heybox_discounts()` → Playwright 渲染 → 提取标题/日期/摘要 → 归入 `game-discount` 分区
2. `collect.py game-discount` 触发抓取
3. SVG 紫色（#8b5cf6）分区显示

**手动新增小黑盒打折帖**：
1. 获取小黑盒分享帖 URL（形如 `https://api.xiaoheihe.cn/v3/bbs/app/api/web/share?...&link_id=xxx`）
2. 在 `data/sources.json` 加一条：
   ```json
   {
     "name": "小黑盒帖子标题",
     "url": "分享帖URL",
     "category": "game-discount",
     "type": "heybox",
     "enabled": true,
     "note": "说明"
   }
   ```
3. 或直接在 `data/game-discount/activities.json` 手动加一条活动
4. 运行 `python3 scripts/collect.py finalize` 重新生成产物
5. 验证 SVG 有「游戏打折」紫色分区
6. 提交推送

**Playwright 依赖**：
- 本地需 `pip install playwright && playwright install chromium`
- GitHub Actions 需在 workflow 里加 Playwright 安装步骤
- 若 Playwright 不可用，`collect_heybox_discounts()` 自动跳过并告警
