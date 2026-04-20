# Twitter / X 发布 API

---

## Single Tweet

```
TWITTER_CREATION_OF_A_POST(
  text            = {推文正文，≤280 字，链接占 23 字},
  media_media_ids = [{media_id}]   # 可选，最多 4 张图，需提前上传
)
→ data.id = tweet_id（写入 post-history）
```

**注意：**
- 图片需要提前上传获取 media_id，当前若无上传工具则纯文字发布，告知 admin 需手动添加图片
- hashtag 直接写在 `text` 里（最多 1–2 个）
- 链接直接放 `text` 末尾，无论长短固定占 23 字

---

## Thread（推文串）

Thread 通过 `reply_in_reply_to_tweet_id` 串联，依次发布：

```
Step 1 — 发第 1 条（hook）：
TWITTER_CREATION_OF_A_POST(
  text = {第 1 条文案，≤280 字}
)
→ tweet_id_1

Step 2 — 发第 2 条（reply to 第 1 条）：
TWITTER_CREATION_OF_A_POST(
  text                     = {第 2 条文案，≤280 字},
  reply_in_reply_to_tweet_id = {tweet_id_1}
)
→ tweet_id_2

Step 3 — 发第 3 条（reply to 第 2 条）：
TWITTER_CREATION_OF_A_POST(
  text                     = {第 3 条文案，≤280 字},
  reply_in_reply_to_tweet_id = {tweet_id_2}
)
→ tweet_id_3

... 以此类推，每条 reply to 上一条

最后一条：总结 + CTA
```

**注意：**
- 每条必须 ≤280 字（链接占 23 字）
- 必须按顺序发，拿到上一条 tweet_id 才能发下一条
- Twitter 不允许 reply 已编辑的推文；如遇此情况改用 `quote_tweet_id`
- post-history 记录第 1 条的 tweet_id 即可代表整个 Thread

---

## 链接处理

Twitter 链接直接放正文末尾，无论原始 URL 长短，固定占 23 字。无需特殊处理。

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| token 过期 | 告知 admin 需重新连接 Twitter，引导运行 setup |
| 推文超过 280 字 | 检查 `text` 字数，链接记为 23 字，重新截短后重试 |
| reply_in_reply_to_tweet_id 无效 | 确认上一条 tweet_id 是纯数字字符串（非 placeholder），重新获取后重试 |
| 内容违反平台政策 | 返回 Twitter 原始错误信息，建议修改后重试 |
| 发布失败（网络/限流） | 保留草稿，建议稍后重试；Thread 中断时记录已发到第几条 |
