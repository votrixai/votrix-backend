---
name: social-media-post-review-monitor
description: "监控和回复各平台帖子评论（Facebook、Instagram、Twitter）。当 admin 说「查看评论」「有什么新评论」「回复差评」「客户反馈」「客户留言」「reviews」时触发。"
integrations:
  - facebook
  - instagram
  - twitter
---

# Review Monitor

你负责监控各平台帖子下的客户评论，汇总情感趋势，草拟回复供 admin 确认后提交。

---

## 启动检查

读取 `mnt/memory/social-media-manager/marketing-context.md`：
- 确认已连接平台
- 读取 `## 运行状态` 各平台的上次巡查时间和最后处理 ID，确定从哪里开始拉取新数据

---

## 数据来源

从 `mnt/memory/social-media-manager/post-history/` 读取近 30 天的帖子记录，拿到各帖子的 post_id。

根据已连接平台，读取对应 reference 文件执行 API 调用：

| 平台 | Reference 文件 |
|---|---|
| Facebook | `/workspace/skills/social-media-post-review-monitor/references/facebook.md` |
| Instagram | `/workspace/skills/social-media-post-review-monitor/references/instagram.md` |
| Twitter | `/workspace/skills/social-media-post-review-monitor/references/twitter.md` |

各平台独立拉取，一个失败不影响其他平台继续。

---

## 情感分类

将所有新评论按情感分类：

| 类别 | 判断标准 |
|---|---|
| 正面 | 赞美、感谢、表达喜爱 |
| 中性 | 一般性评价、提问 |
| 负面 | 投诉、不满、差评 |

提炼高频主题：相同问题出现 2 次以上单独标出，例如：
> ⚠️ 3 条评论提到「等待时间太长」

---

## 话题信号写入

情感分类完成后，若发现高频主题（同一问题出现 2 次以上），将信号写入 `mnt/memory/social-media-manager/marketing-context.md` 的 `## 内容策略 → 近期重点话题`：

```
- {日期} [review] {话题描述}（{N} 条评论提及）→ 建议：{内容行动建议}
```

例：
```
- 2024-01-15 [review] 客户询问营业时间（3条）→ 建议：做一条 Story 置顶说明营业时间
- 2024-01-18 [review] 多次提到停车不便（2条）→ 建议：发帖主动说明周边停车点
```

最多保留 5 条，超出时删除最旧的一条。更新 `近期重点话题 → 最后更新` 时间。

---

## 展示评论

按优先级排序展示：

1. **负面评论** — 最优先
2. **中性评论**
3. **正面评论**

每条评论显示：平台 / 作者 / 时间 / 内容 / 草拟回复

---

## 草拟回复

为每条评论生成回复草稿，结合 `mnt/memory/social-media-manager/marketing-context.md` 的品牌语气：

| 类型 | 策略 |
|---|---|
| 赞美 | 感谢 + 简短呼应，保持亲切感 |
| 提问 | 直接回答，信息不足时邀请私信 |
| 投诉 | 道歉 + 邀请私信处理，不在公开帖子争论 |
| 垃圾评论 | 建议 admin 删除，不回复 |

**规则：回复草稿必须给 admin 确认，绝不自动提交。**

详细回复模板见 `/workspace/skills/social-media-post-review-monitor/references/response-templates.md`。

---

## Admin 确认与提交回复

展示草稿后等待 admin：
- **确认**：提交回复
- **修改**：更新草稿，再次确认
- **跳过**：标记为「已查看，暂不回复」
- **删除评论**（仅 Facebook / Instagram）：确认后调用删除 action；Twitter 无法删除他人评论

回复 / 删除 API 详见各平台 reference 文件。

---

## 写入记录

每批评论处理完后：

**1. 更新 `mnt/memory/social-media-manager/marketing-context.md` 的 `## 运行状态`**

更新各平台的上次巡查时间和最后处理 ID。

**2. 写入 review-history**

路径：`mnt/memory/social-media-manager/review-history/{YYYY-MM}/{YYYY-MM-DD}.md`

```markdown
## {HH:MM} | {平台} | 评论

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

从 `mnt/memory/social-media-manager/review-history/` 读取指定时间范围的记录，生成：

- 各平台评论总数 + 正 / 中 / 负比例
- 高频正面关键词（服务好、速度快...）
- 高频负面关键词（等待、贵、...）
- 未回复评论列表（需要跟进）
- 可执行建议（例如：「本月 4 条差评提到周末等位时间长，建议增加周末人手」）
