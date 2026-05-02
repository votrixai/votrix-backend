# Instagram 评论监控 API

---

## 获取评论

```
INSTAGRAM_GET_IG_MEDIA_COMMENTS(
  media_id = {post_id}
)
→ data[].id、data[].text、data[].username、data[].timestamp
```

从 `mnt/memory/social-media-manager/post-history/` 读取近 30 天帖子的 post_id，逐一拉取。  
只处理上次巡查时间之后的新评论（`timestamp > 上次巡查时间`）。

---

## 回复评论

```
INSTAGRAM_POST_IG_COMMENT_REPLIES(
  comment_id = {comment_id},
  message    = {回复内容，≤300 字，≤4 个 hashtag，≤1 个 URL}
)
```

---

## 删除评论

仅限自己帖子下的垃圾评论，admin 确认后执行：

```
INSTAGRAM_DELETE_COMMENT(
  comment_id = {comment_id}
)
```

---

## 注意

- Instagram Story 评论不可通过 API 读取
- DM（私信）不在此工具范围内

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| token 过期 / 权限不足 | 告知 admin 需重新连接 Instagram，引导运行 setup |
| media_id 无效 | 跳过该帖子，继续处理其他帖子 |
| 回复超过 300 字 | 截短后重试 |
