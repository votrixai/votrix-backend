---
name: social-media-post-analytics
description: "拉取各平台数据，分析帖子表现、受众增长，生成报告。当 admin 说「数据报告」「表现怎样」「多少人看了」「粉丝增长」「哪篇帖子效果最好」「analytics」「insights」时触发。"
integrations:
  - facebook
  - instagram
  - twitter
  - linkedin
---

# Analytics

你负责从各平台拉取表现数据，结合本地 post-history 记录，生成可执行的分析报告。

---

## 启动检查

读取 `/workspace/marketing-context.md`，确认：
- 已连接平台列表（只分析已连接的平台）
- Page ID / Account ID（API 调用必需）

---

## 数据架构：两层读取

**原则：先读本地，缺数据再调 API。**

### 第一层：本地 post-history

路径：`/workspace/post-history/{YYYY-MM}/{YYYY-MM-DD}.md`

每条帖子记录格式：
```
- 触达：-
- 互动：-
- 点赞：-
- 评论：-
- 分享：-
```

字段为 `-` 表示尚未拉取，需要调 API 刷新。

### 第二层：平台 API（按需刷新）

仅当本地数据为 `-` 时调用。每次最多批量处理 **10 条**帖子，处理完告知 admin 并询问是否继续。

---

## 平台 API 调用

### Facebook

```
# 账号级别数据（粉丝、触达、互动趋势）
FACEBOOK_GET_PAGE_INSIGHTS
  传入：page_id、metric（fans、page_impressions、page_engaged_users）、period（day/week/month）
  返回：各指标时间序列数据

# 单帖表现
FACEBOOK_GET_POST_INSIGHTS
  传入：post_id、metric（post_impressions、post_reactions_by_type_total、post_clicks）
  返回：该帖数据
```

### Instagram

```
# 账号级别数据
INSTAGRAM_GET_USER_INSIGHTS
  传入：ig_user_id、metric（reach、impressions、profile_views、follower_count）、period（day/week/month）
  返回：各指标时间序列数据

# 单帖表现
INSTAGRAM_GET_IG_MEDIA_INSIGHTS
  传入：media_id（post_id）、metric（reach、impressions、likes、comments、shares、saved）
  返回：该帖数据
```

### Twitter

```
# 推文表现
通过 Composio Twitter 工具传入 tweet_id
  返回：impression_count、like_count、retweet_count、reply_count、quote_count

# 账号增长
通过 Composio Twitter 工具传入 user_id
  返回：followers_count、following_count
```

### LinkedIn

```
# 帖子表现
通过 Composio LinkedIn 工具传入 post_id（ugcPost URN 格式）
  返回：impressionCount、likeCount、commentCount、shareCount、clickCount

# 账号粉丝数
通过 Composio LinkedIn 工具传入 organization_id
  返回：followerCountsByAssociationType
```

---

## 刷新本地数据

API 拉取后，立即更新对应 post-history 文件里的 `-` 字段：

读取文件 → 替换对应帖子下的 `触达：-`、`互动：-`、`点赞：-`、`评论：-`、`分享：-` → 写回文件。

同时将本次刷新时间写入 `/workspace/marketing-context.md` 的 `## 运行状态` 对应平台字段。

---

## 报告类型

Admin 说「出报告」时询问要哪种，或根据问句直接判断：

### 1. 快速总结（默认）

> Admin 说「最近表现怎样」「给我看看数据」

- 各平台最近 7 天：总触达、总互动、新增粉丝
- 表现最好的 1 篇帖子（各平台）
- 一句话结论 + 1 个可执行建议

### 2. 帖子排名

> Admin 说「哪篇帖子效果最好」「帖子排行」

从 post-history 读取指定时间范围内所有帖子，按互动率排序：

```
互动率 = (点赞 + 评论 + 分享) / 触达 × 100%
```

展示 Top 5，标注平台、主题、发布时间、关键指标。
分析共同特征：时间段、内容类型、hashtag 组合。

### 3. 账号增长

> Admin 说「粉丝增长怎样」「涨了多少粉」

- 各平台粉丝数变化（本周 vs 上周）
- 增长最快的时间段
- 对应期间发布了什么内容（关联分析）

### 4. 内容策略分析

> Admin 说「哪类内容效果好」「内容建议」

按内容主题（Pillar）分组统计平均互动率：

| 主题 | 帖子数 | 平均互动率 | 最佳平台 |
|---|---|---|---|
| 产品推广 | - | - | - |
| 行业知识 | - | - | - |
| 幕后故事 | - | - | - |
| 客户案例 | - | - | - |

输出：哪类内容效果最好，哪类需要调整，发布时间优化建议。

### 5. 完整月报

> Admin 说「出月报」「本月数据」

综合以上 4 类，涵盖：
- 各平台账号增长汇总
- 本月所有帖子表现排名
- 内容策略分析
- 本月评论情感趋势（如有）
- 下月建议：内容方向、发布频率、需要改进的平台

---

## 展示报告

优先在对话中直接展示，数字用表格，趋势用对比（本周 vs 上周）。

报告超过一屏时，询问 admin 是否保存为文件。Admin 确认后写入：

路径：`/workspace/analytics-reports/{YYYY-MM}/{报告类型}-{YYYY-MM-DD}.md`

文件命名示例：
- `summary-2024-01-15.md`
- `post-ranking-2024-01-15.md`
- `monthly-report-2024-01.md`

---

## 批量处理限制

单次 API 刷新最多处理 **10 条**帖子。处理完毕后：

```
已刷新 10 条帖子数据（共 23 条待更新）。
是否继续拉取剩余 13 条？（每次拉取 10 条）
```

Admin 说「继续」就处理下一批；说「够了」就用已有数据生成报告。

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| 平台 token 过期 | 告知 admin 需重新连接该平台，该平台数据跳过 |
| 帖子 ID 不存在（已删除） | 标记为「已删除」，从统计中排除 |
| API 限流 | 告知 admin 当前受限，建议 15 分钟后重试 |
| post-history 文件不存在 | 告知 admin 该时间段无发布记录 |
| 数据全为 `-` 且无 API 连接 | 提示需要先连接平台才能拉取数据 |
