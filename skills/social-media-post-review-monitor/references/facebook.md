# Facebook 评论监控 API

---

## 获取评论

```
FACEBOOK_GET_COMMENTS(
  post_id = {post_id}
)
→ data[].id、data[].message、data[].from、data[].created_time
```

从 `mnt/memory/social-media-manager/post-history/` 读取近 30 天帖子的 post_id，逐一拉取。  
只处理上次巡查时间之后的新评论（`created_time > 上次巡查时间`）。

---

## 回复评论

```
FACEBOOK_CREATE_COMMENT(
  post_id = {post_id},
  message = {回复内容}
)
```

---

## 删除评论

仅限自己主页的垃圾评论，admin 确认后执行：

```
FACEBOOK_DELETE_COMMENT(
  comment_id = {comment_id}
)
```

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| token 过期 / 权限不足 | 告知 admin 需重新连接 Facebook，引导运行 setup |
| post_id 无效 | 跳过该帖子，继续处理其他帖子 |
