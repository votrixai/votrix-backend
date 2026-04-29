# Twitter 评论监控 API

---

## 获取提及 / Reply

Twitter 无法按 tweet_id 直接获取 reply 列表。改用全文搜索抓取 @提及：

```
TWITTER_FULL_ARCHIVE_SEARCH(
  query       = "@{twitter_handle}",
  start_time  = {上次巡查时间，ISO 8601，如 2024-01-15T10:00:00Z},
  max_results = 50
)
→ data[].id、data[].text、data[].author_id、data[].created_at
```

`twitter_handle` 从 `/workspace/marketing-context.md` 的 `## 已连接平台 → Twitter` 读取。

过滤掉自身账号发出的推文（`author_id` = 自身账号 ID），只处理他人的 @提及和 reply。

---

## 回复推文

```
TWITTER_CREATION_OF_A_POST(
  text                       = {回复内容，≤280 字},
  reply_in_reply_to_tweet_id = {原推文 id}
)
```

---

## 注意

- 无法删除他人推文，垃圾评论只能选择不回复
- Twitter API 有频率限制，巡查间隔建议不短于 6 小时

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| token 过期 | 告知 admin 需重新连接 Twitter，引导运行 setup |
| 搜索结果为空 | 正常情况，无新提及，静默跳过 |
| 回复超过 280 字 | 截短后重试 |
| 限流（429） | 记录当前进度，下次巡查继续 |
