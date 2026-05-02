# Twitter Analytics API

---

## 单帖表现

```
TWITTER_GET_POST_ANALYTICS(
  ids        = [{tweet_id}],   # 最多 100 个，批量传入
  start_time = {YYYY-MM-DDTHH:mm:ssZ},
  end_time   = {YYYY-MM-DDTHH:mm:ssZ},
  granularity = "total"        # hourly / daily / weekly / total
)
→ data[].impression_count、like_count、retweet_count、reply_count、quote_count
```

从 `mnt/memory/social-media-manager/post-history/` 读取近 30 天推文的 tweet_id，批量传入（每次最多 100 个）。

---

## 账号粉丝数

```
TWITTER_USER_LOOKUP_ME()
→ data.public_metrics.followers_count、data.public_metrics.following_count
```

---

## 注意

- `impression_count` 仅对自己账号的推文有效，搜索他人推文时返回 0
- Thread 只记录第 1 条推文的 tweet_id，analytics 也只拉第 1 条数据代表整个 Thread

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| token 过期 | 告知 admin 需重新连接 Twitter，该平台数据跳过 |
| tweet_id 不存在（已删除） | 标记为「已删除」，从统计中排除 |
| API 限流（429） | 告知 admin，建议 15 分钟后重试 |
