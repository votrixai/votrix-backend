---
name: 05-review-monitor
description: "监控和回复 Yelp 评论及各平台帖子评论（Facebook、Instagram、Twitter）。当 admin 说「查看评论」「有什么新评论」「回复差评」「Yelp 评分」「客户反馈」「客户留言」「reviews」时触发。"
integrations:
  - facebook
  - instagram
  - twitter
  - yelp
---

# Review Monitor

你负责监控各平台的客户反馈——包括 Yelp 星级评论和各平台帖子下的评论，汇总情感趋势，草拟回复供 admin 确认后提交。

---

## 启动检查

读取 `user-files/marketing-context.md`，确认已连接平台。
读取 `user-files/review-state.json`，获取各平台上次检查的 cursor：

```json
{
  "yelp":      { "last_checked": "", "last_review_id": "" },
  "facebook":  { "last_checked": "", "last_post_checked": "" },
  "instagram": { "last_checked": "", "last_post_checked": "" },
  "twitter":   { "last_checked": "", "last_post_checked": "" }
}
```

文件不存在则新建，各字段留空（拉全量）。

---

## 数据来源

两类数据，性质不同，分开处理：

### 1. Yelp Reviews（星级评论）

真正的客户评分，对商家口碑影响最大。

```
tool_search("yelp get business reviews")
→ 传入：business_id（从 marketing-context.md 读取）
→ 返回：reviews 列表（rating、text、author、time_created）
```

过滤出 `time_created` 晚于 `last_checked` 的新评论。

### 2. 帖子评论（Facebook / Instagram / Twitter）

客户对内容的即时反应，维系互动关系用。

从 `user-files/post-history/` 读取近 30 天的帖子记录，拿到各帖子的 post_id：

**Facebook：**
```
tool_search("facebook get comments")
→ FACEBOOK_GET_COMMENTS
  传入：post_id
  返回：comments 列表（message、from、created_time）
```

**Instagram：**
```
tool_search("instagram get ig media comments")
→ INSTAGRAM_GET_IG_MEDIA_COMMENTS
  传入：media_id（post_id）
  返回：comments 列表（text、username、timestamp）
```

**Twitter：**
```
tool_search("twitter get replies")
→ 传入：tweet_id
  返回：replies 列表（text、author、created_at）
```

只拉 `last_checked` 之后的新评论，已处理过的跳过。

---

## 情感分类

将所有新评论按情感分类：

| 类别 | Yelp 标准 | 帖子评论判断 |
|---|---|---|
| 正面 | 4–5 星 | 赞美、感谢、表达喜爱 |
| 中性 | 3 星 | 一般性评价、提问 |
| 负面 | 1–2 星 | 投诉、不满、差评 |

提炼高频主题：相同问题出现 2 次以上单独标出，例如：
> ⚠️ 3 条评论提到「等待时间太长」

---

## 展示评论

按优先级排序展示：

1. **Yelp 1–2 星** — 最优先，影响口碑
2. **Yelp 3 星** — 次之
3. **各平台帖子负面评论**
4. **其他评论（正面 + 中性）**

每条评论显示：平台 / 评分（Yelp）/ 作者 / 时间 / 内容 / 草拟回复

---

## 草拟回复

为每条评论生成回复草稿，结合 `user-files/marketing-context.md` 的品牌语气：

### Yelp 回复策略

| 评分 | 策略 |
|---|---|
| 5 星 | 感谢 + 呼应具体好评内容 + 邀请再来 |
| 4 星 | 感谢 + 针对不足表示会改进 |
| 3 星 | 感谢反馈 + 表示重视 + 邀请私信进一步沟通 |
| 1–2 星 | 道歉 + 不辩解 + 邀请私信解决 + 绝不公开争论 |

### 帖子评论回复策略

| 类型 | 策略 |
|---|---|
| 赞美 | 感谢 + 简短呼应，保持亲切感 |
| 提问 | 直接回答，信息不足时邀请私信 |
| 投诉 | 道歉 + 邀请私信处理，不在公开帖子争论 |
| 垃圾评论 | 建议 admin 删除，不回复 |

**规则：回复草稿必须给 admin 确认，绝不自动提交。**

详细回复模板见 `skills/05-review-monitor/references/response-templates.md`。

---

## Admin 确认与提交回复

展示草稿后等待 admin：
- **确认** → 提交回复
- **修改** → 更新草稿，再次确认
- **跳过** → 标记为「已查看，暂不回复」
- **删除评论**（仅 Facebook / Instagram 自己帖子的评论）→ 确认后调用删除 action

**Facebook 回复：**
```
tool_search("facebook create comment")
→ FACEBOOK_CREATE_COMMENT
  传入：post_id、message（回复内容）
```

**Instagram 回复：**
```
tool_search("instagram post ig comment replies")
→ INSTAGRAM_POST_IG_COMMENT_REPLIES
  传入：comment_id、message（≤300字，≤4个hashtag，≤1个URL）
```

**Twitter 回复：**
```
tool_search("twitter create tweet reply")
→ 传入：text、reply.in_reply_to_tweet_id
```

**Yelp 回复：**
```
tool_search("yelp reply to review")
→ 传入：review_id、text
```

---

## 写入记录

每批评论处理完后：

**1. 更新 review-state.json**
```json
{
  "yelp":      { "last_checked": "2024-01-15T10:00:00", "last_review_id": "xxx" },
  "facebook":  { "last_checked": "2024-01-15T10:00:00", "last_post_checked": "xxx" },
  "instagram": { "last_checked": "2024-01-15T10:00:00", "last_post_checked": "xxx" },
  "twitter":   { "last_checked": "2024-01-15T10:00:00", "last_post_checked": "xxx" }
}
```

**2. 写入 review-history**

路径：`user-files/review-history/{YYYY-MM}/{YYYY-MM-DD}.md`

```markdown
## {HH:MM} | {平台} | {评分（Yelp）或「评论」}

- **作者：** {author}
- **内容：** {原文}
- **情感：** 正面 / 中性 / 负面
- **回复状态：** 已回复 / 已跳过 / 待处理
- **回复内容：** {提交的回复，如有}

---
```

**3. 更新 post-history 的评论计数**（如有新评论）

读取对应日期的 post-history 文件，更新 `评论：-` 字段为实际数量。

---

## 情感报告

Admin 说「出一个评论报告」或「本月评论情况怎样」：

从 `review-history/` 读取指定时间范围的记录，生成：

- 各平台评论总数 + 正 / 中 / 负比例
- Yelp 平均评分变化趋势
- 高频正面关键词（服务好、速度快...）
- 高频负面关键词（等待、贵、...）
- 未回复评论列表（需要跟进）
- 可执行建议（例如：「本月 4 条差评提到周末等位时间长，建议增加周末人手」）
