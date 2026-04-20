---
name: social-media-post-publishing
description: "发布或定时发布内容到已连接的社交平台。当 admin 说「发布」「发帖」「定时发」「发到 Instagram」「发到 Facebook」「发到 Twitter」「发到 LinkedIn」「post」「schedule」时触发。生成内容见 social-media-post-content-creation。"
integrations:
  - facebook
  - instagram
  - twitter
  - linkedin
---

# Social Publisher

你负责将内容准确发布到对应平台，并将发布记录存入 `/workspace/post-history/`，供 analytics 后续分析使用。

---

## Cron 每日自动发布模式

触发消息为 `[cron] 内容发布` 时：

1. 读取 `/workspace/marketing-context.md` 的 `## 指令`，确认发布行为（需确认 / 直接发布）
2. 在 `/workspace/drafts/` 中查找文件名以**今天日期**开头的所有草稿
3. 过滤出状态为「待发布」的草稿，按平台分组
4. 状态为「草稿」（未经 admin 确认）的文件：
   - 若指令为「需要确认」：跳过，通知 admin「今天有 X 条草稿待确认」
   - 若指令为「直接发布」：视为已确认，直接进入发布流程
5. 依次发布各平台内容，执行发布后处理（写 post-history、清空草稿、汇报结果）
6. 当天无草稿时静默退出，不通知 admin

---

## 启动检查

读取 `/workspace/marketing-context.md`：
- 确认 `## 已连接平台` 里目标平台有 Page ID / Account ID / ig_user_id
- 未连接的平台：告知 admin 需先运行 setup 连接该平台，跳过后继续其他平台

---

## 获取待发布内容

**从 content-creator 直接衔接**
内容已在对话 context 中，直接进入发布流程。

**Admin 指定草稿**
列出 `/workspace/drafts/` 下所有草稿展示给 admin 选择，读取对应文件。

**Admin 提供现成文案**
直接用 admin 给的内容，询问目标平台和内容类型。

---

## 发布

根据草稿的 `平台` + `内容类型` 字段，读取对应 reference 文件执行 API 调用：

| 平台 | Reference 文件 |
|---|---|
| Instagram | `/workspace/skills/social-media-post-publishing/references/instagram-publishing.md` |
| Facebook | `/workspace/skills/social-media-post-publishing/references/facebook-publishing.md` |
| LinkedIn | `/workspace/skills/social-media-post-publishing/references/linkedin-publishing.md` |
| Twitter | `/workspace/skills/social-media-post-publishing/references/twitter-publishing.md` |

各平台独立发布，一个失败不影响其他平台继续。

---

## 发布后处理

每个平台发布成功后，立即执行：

**1. 更新草稿状态**

读取草稿文件，将 `状态` 字段改为「已发布」，其余内容保留不动。

**2. 写入 post-history**

路径：`/workspace/post-history/{YYYY-MM}/{YYYY-MM-DD}.md`

文件存在则读取后末尾追加，不存在则新建：

```markdown
## {HH:MM} | {平台} | {内容类型} | {主题标题}

- **Post ID：** {post_id}
- **文案：** {文案前 100 字}...
- **Hashtag：** {hashtag 列表}
- **链接：** {链接，无则留空}
- **配图：** {public_url，无则留空}
- **表现数据：**（由 analytics 填入）
  - 触达：-
  - 互动：-
  - 点赞：-
  - 评论：-
  - 分享：-

---
```

**3. 汇报结果**

```
✓ Instagram Reels  — 发布成功（post_id: xxx）
✓ Facebook Feed    — 发布成功（post_id: xxx）
✗ LinkedIn Text    — 失败：token 过期，请重新连接 LinkedIn
```

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| 平台 token 过期 | 告知 admin 需重新连接该平台，引导运行 setup |
| 图片/视频格式或尺寸不符 | 告知具体要求，等 admin 重新提供 |
| 发布失败（网络/限流） | 保留草稿状态为「待发布」，建议稍后重试 |
| 内容违反平台政策 | 返回平台原始错误信息，建议修改后重试 |

平台特有错误处理见各 reference 文件。
