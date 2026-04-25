# LinkedIn Analytics API

---

## 帖子表现（组织主页）

```
LINKEDIN_GET_SHARE_STATS(
  organizational_entity = "urn:li:organization:{org_id}",
  time_intervals        = "(timeRange:(start:{start_ms},end:{end_ms}),timeGranularityType:DAY)"
  # 时间戳为毫秒级 epoch；省略 time_intervals 则返回全时段累计数据
)
→ impressionCount、clickCount、likeCount、commentCount、shareCount
```

`org_id` 从 `/workspace/marketing-context.md` 的 `## 已连接平台 → LinkedIn` 读取。

**注意：** 此接口返回的是组织主页所有内容的汇总数据，不能按单条帖子拆分。  
单帖维度数据目前 Composio LinkedIn 工具集不支持，只能用汇总数据分析整体趋势。

---

## 账号粉丝数

```
LINKEDIN_GET_NETWORK_SIZE(
  edgeType = "COMPANY_FOLLOWED_BY_MEMBER"
)
→ followerCountsByAssociationType（关注人数）
```

---

## 页面浏览数据

```
LINKEDIN_GET_ORG_PAGE_STATS(
  organization       = "urn:li:organization:{org_id}",
  timeRangeStart     = {start_ms},   # 毫秒级 epoch，可选
  timeRangeEnd       = {end_ms},     # 毫秒级 epoch，可选
  timeGranularityType = "DAY"        # DAY / MONTH，可选
)
→ pageViews、uniqueVisitors、customButtonClicks
```

---

## 局限说明

LinkedIn Analytics 当前仅支持组织主页维度，无单帖拆分。分析时：
- 使用汇总数据判断整体内容表现趋势
- 结合 post-history 中的发布频率和内容类型，做相关性推断

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| token 过期 / 权限不足 | 告知 admin 需重新连接 LinkedIn，该平台数据跳过 |
| 429 rate limit | LinkedIn 共享 OAuth 限流严格，建议稍后重试 |
| org_id 无效 | 确认 marketing-context.md 中 LinkedIn org_id 格式正确 |
