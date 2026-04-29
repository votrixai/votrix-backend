# Facebook 发布 API

---

## 前置：获取 Page ID

`page_id` 从 `/workspace/marketing-context.md` 的 `## 已连接平台 → Facebook` 读取。
如需确认可调：

```
FACEBOOK_LIST_MANAGED_PAGES()
→ 返回 data[].id（page_id）和 data[].name
```

---

## Feed Post — 纯文字 / 链接

```
FACEBOOK_CREATE_POST(
  page_id   = {page_id},
  message   = {正文},
  link      = {链接 url},   # 可选，自动生成预览卡
  published = true
)
→ data.id = post_id（格式：pageId_postId）
```

**注意：**
- `message` 和 `link` 至少提供一个
- 贴链接会自动生成预览卡，正文不需要重复描述链接内容
- hashtag 在 Facebook 效果弱，放正文末尾即可

---

## Feed Post — 带图片

```
FACEBOOK_CREATE_PHOTO_POST(
  page_id   = {page_id},
  url       = {image_public_url},  # 直链 HTTPS，不能是 HTML 页面
  message   = {正文 + hashtag},
  published = true
)
→ data.id = post_id（格式：pageId_postId）
```

**注意：**
- `url` 必须是图片文件直链，返回正确 MIME type（image/jpeg 或 image/png）
- 不支持重定向 URL 或需要认证的链接

---

## Reels / 视频

```
FACEBOOK_CREATE_VIDEO_POST(
  page_id     = {page_id},
  file_url    = {video_public_url},  # 直链 MP4，H.264 + AAC 编码
  description = {简短文案},
  title       = {视频标题},          # 可选
  published   = true
)
→ data.id = post_id
```

**注意：**
- `file_url` 必须是直链 MP4，不能是 YouTube 等播放页链接
- 视频上传后进入处理状态，处理完成后才对用户可见
- Facebook Reels 与 Instagram Reels 可用同一视频素材

---

## Story

不支持。

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| token 过期 / 权限不足 | 告知 admin 需重新连接 Facebook，引导运行 setup |
| 图片 URL 无法访问 | 确认 URL 是直链 HTTPS，返回正确 MIME type |
| 视频格式不支持 | 建议使用 MP4 + H.264/AAC，告知 admin 重新提供 |
| 发布失败（网络/限流） | 保留草稿，建议稍后重试 |
| 内容违反平台政策 | 返回 Facebook 原始错误信息，建议修改后重试 |
