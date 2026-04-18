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

## 启动检查

读取 `/workspace/marketing-context.md`：
- 确认 `## 已连接平台` 里目标平台有 Page ID / Account ID
- 未连接的平台：告知 admin 需先运行 setup 连接该平台，跳过该平台继续其他

---

## 获取待发布内容

**从 content-creator 直接衔接**
内容已在对话 context 中，直接进入发布流程。

**Admin 指定草稿**
列出 `/workspace/drafts/` 下所有草稿展示给 admin 选择，读取对应文件。

**Admin 提供现成文案**
直接用 admin 给的内容，询问目标平台。

---

## 图片处理

内容带图片时，发布前先调 `image_upload` 上传到 Supabase Storage 拿公开 URL：

```
image_upload(storage_path="...", user_id="...")
→ 返回 public_url
```

---

## 链接处理

| 平台 | 处理方式 |
|---|---|
| Facebook | 正文直接放链接，自动生成预览卡 |
| Twitter | 链接放正文末尾，固定占 23 字 |
| LinkedIn | 正文末尾写「链接见评论」，发布后把链接发到第一条评论 |
| Instagram | 正文链接不可点击，改写为「链接在主页 Bio」 |

---

## 定时发布

Admin 说「明天早上 9 点发」：
1. 在草稿文件里标注定时时间
2. 用 `CronCreate` 创建一次性任务，到时触发本 skill 读取该草稿发布
3. 告知 admin 定时任务已设置，并说明草稿路径

---

## 发布后处理

每个平台发布成功后，立即执行：

**1. 删除草稿文件**

将草稿文件内容清空（虚拟文件系统不支持 delete，写空内容代替）。

**2. 写入 post-history**

路径：`/workspace/post-history/{YYYY-MM}/{YYYY-MM-DD}.md`

文件存在则读取后末尾追加，不存在则新建：

```markdown
## {HH:MM} | {平台} | {主题标题}

- **Post ID：** {post_id}
- **文案：** {文案前 100 字}...
- **Hashtag：** {hashtag 列表}
- **链接：** {链接，无则留空}
- **配图：** {storage_path，无则留空}
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
✓ Instagram — 发布成功（post_id: xxx）
✓ Facebook  — 发布成功（post_id: xxx）
✗ Twitter   — 失败：media_id 上传超时，草稿已保留，建议稍后重试
```

各平台独立汇报，失败不影响其他平台。

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| 平台 token 过期 | 告知 admin 需重新连接该平台，引导运行 setup |
| Instagram container 处理超时 | 重新创建 container，原 creation_id 不可复用 |
| Instagram 超过 25 posts/日限额 | 告知 admin 剩余配额，建议明天发布 |
| 图片格式/尺寸不符 | 告知具体要求，等 admin 重新提供 |
| 发布失败（网络/限流） | 保留草稿，建议稍后重试 |
| 内容违反平台政策 | 返回平台原始错误信息，建议修改后重试 |
