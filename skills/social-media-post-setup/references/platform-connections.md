# Platform Connection Reference

每个平台的连接流程都一样：调用 `manage_connections(toolkit="<name>")` → 检查状态 → 引导授权 → 记录账号信息。

连接信息与平台 ID 写入 **`mnt/memory/social-media-manager/marketing-context.md`** 的 `## 已连接平台`（持久记忆仅 Markdown；媒体文件用 `publish_file` 得 URL 后再写入该文件的 `## 品牌素材` 等小节）。

---

## Facebook

```python
manage_connections(toolkit="facebook")
```

- `connected: false` → 发 `redirect_url` 给 admin，提醒勾选 **Pages** 权限
- 连接后：列出 Pages → 让 admin 选择 → 记录 `page_id`、`page_name`

写入 `mnt/memory/social-media-manager/marketing-context.md` 对应小节：
```
### Facebook
- 启用：true
- 主页名称：{page_name}
- Page ID：{page_id}
```

能做：发帖（含图片/视频）、读评论/评分、回复评论、读 Page insights

---

## Instagram

前提：需要 Instagram Business/Creator 账号，且已关联 Facebook Page。

```python
manage_connections(toolkit="instagram")
```

连接后获取：`instagram_account_id`、`username`、`account_type`

- 若 `account_type` 是 PERSONAL，停止并提示 admin 切换为企业号

写入 `mnt/memory/social-media-manager/marketing-context.md` 对应小节：
```
### Instagram
- 启用：true
- 用户名：{username}
- Account ID：{instagram_account_id}
```

能做：发图片/视频帖、读 insights、读/回复评论

---

## LinkedIn

```python
manage_connections(toolkit="linkedin")
```

连接后获取：`linkedin_person_id`、`linkedin_organization_id`（公司 Page）、`company_name`

写入 `mnt/memory/social-media-manager/marketing-context.md` 对应小节：
```
### LinkedIn
- 启用：true
- 公司名称：{company_name}
- Organization ID：{linkedin_organization_id}
- Person ID：{linkedin_person_id}
```

能做：以个人或公司 Page 发帖（文字/图片/视频/PDF 轮播）、读 insights

---

## Twitter / X

```python
manage_connections(toolkit="twitter")
```

连接后获取：`twitter_user_id`、`username`

写入 `mnt/memory/social-media-manager/marketing-context.md` 对应小节：
```
### Twitter
- 启用：true
- 用户名：{username}
- User ID：{twitter_user_id}
```

能做：发推文（含媒体）、发 Thread、读 analytics

---

## Yelp

Yelp 不是发帖平台，只支持评论管理。用 `tool_search("composio manage connections yelp")` 找到授权工具发起连接。

连接后获取：`yelp_business_id`、`business_name`

写入 `mnt/memory/social-media-manager/marketing-context.md` 对应小节：
```
### Yelp
- 商家名称：{business_name}
- Business ID：{yelp_business_id}
```

能做：读评论、回复评论、读综合评分 | 不能做：发内容/帖子
