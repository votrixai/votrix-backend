# Facebook Analytics API

---

## 账号级别数据

```
FACEBOOK_GET_PAGE_INSIGHTS(
  page_id = {page_id},
  metric  = ["fans", "page_impressions", "page_engaged_users"],
  period  = "week"   # day / week / month
)
→ data[].name、data[].values（时间序列）
```

- `fans`：粉丝净增量
- `page_impressions`：页面总触达
- `page_engaged_users`：互动用户数

---

## 单帖表现

```
FACEBOOK_GET_POST_INSIGHTS(
  post_id = {post_id},
  metric  = ["post_impressions", "post_reactions_by_type_total", "post_clicks"]
)
→ data[].name、data[].values
```

- `post_impressions`：触达人数
- `post_reactions_by_type_total`：各类 reaction 数（like/love/haha/wow/sad/angry）
- `post_clicks`：帖子点击数

汇总互动数 = 所有 reaction 之和 + 评论数 + 分享数。

---

## 刷新流程

从 `mnt/memory/social-media-manager/post-history/` 读取近 30 天帖子的 post_id，逐一调用单帖接口。  
每次最多处理 10 条，处理完询问是否继续。

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| token 过期 / 权限不足 | 告知 admin 需重新连接 Facebook，该平台数据跳过 |
| post_id 不存在（已删除） | 标记为「已删除」，从统计中排除 |
| API 限流 | 告知 admin，建议 15 分钟后重试 |
