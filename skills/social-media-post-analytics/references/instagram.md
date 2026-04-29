# Instagram Analytics API

---

## 账号级别数据

```
INSTAGRAM_GET_USER_INSIGHTS(
  ig_user_id = {ig_user_id},
  metric     = ["reach", "impressions", "profile_views", "follower_count"],
  period     = "week"   # day / week / month
)
→ data[].name、data[].values（时间序列）
```

`ig_user_id` 从 `/workspace/marketing-context.md` 的 `## 已连接平台 → Instagram` 读取。

---

## 单帖表现

```
INSTAGRAM_GET_IG_MEDIA_INSIGHTS(
  media_id = {post_id},
  metric   = ["reach", "impressions", "likes", "comments", "shares", "saved"]
)
→ data[].name、data[].values
```

互动率 = (likes + comments + shares + saved) / reach × 100%

---

## 注意

- Story 的 insights 仅在发布后 24 小时内可拉取，超时数据不可获取
- Reels 的 `reach` 和 `impressions` 可能远高于普通 Feed，分析时注意区分内容类型

---

## 刷新流程

从 `/workspace/post-history/` 读取近 30 天帖子的 post_id，逐一调用单帖接口。  
每次最多处理 10 条，处理完询问是否继续。

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| token 过期 / 权限不足 | 告知 admin 需重新连接 Instagram，该平台数据跳过 |
| media_id 不存在（已删除） | 标记为「已删除」，从统计中排除 |
| Story 数据不可用（超 24h） | 记录为「数据已过期」，不再重试 |
| API 限流 | 告知 admin，建议 15 分钟后重试 |
