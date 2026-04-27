# Twitter 图片 / 视频发布 — 调研与实验记录

## 结论速查

| 能力 | 状态 | 备注 |
|---|---|---|
| 发图片（≤5MB，JPEG/PNG/WEBP） | ✅ 可用 | 需走四步流程，见下文 |
| 发视频 | ❌ 不可用 | Composio 无 FINALIZE 工具，chunked upload 完不成 |
| Instagram 图片 | ✅ 可用 | publish_file → 公开 URL → image_url |
| Instagram Reels 视频 | ✅ 可用 | video_generate 直接返回公开 URL，无需额外步骤 |

---

## 为什么之前推特图片发不上去

三个 bug 叠加导致：

### Bug 1 — `upload_file` dispatch 缺失（已修复）

`app/tools/__init__.py` 历史上把 `composio_upload_file` 改名为 `upload_file` 后，dispatch 没有跟上，
调用时返回 `{"error": "Unknown custom tool: upload_file"}`。

**修复**：`__init__.py` 加入 `upload_file` → `file.handle` 的 dispatch，并改为相对导入（`from . import ...`）避免循环导入。

### Bug 2 — `config.json` 工具名过期（已修复）

`agents/post-agent/config.json` 的 `tools` 数组里还写着 `"composio_upload_file"`（旧名），
agent provision 时找不到这个名字，导致该工具根本没有注册到 agent。

**修复**：将 `"composio_upload_file"` 改为 `"upload_file"`。

### Bug 3 — skill 文档错误（已修复）

`skills/social-media-post-publishing/references/twitter-publishing.md` 写着：
> 「图片需要提前上传获取 media_id，当前若无上传工具则纯文字发布」

这是错误的描述——`TWITTER_UPLOAD_MEDIA` 工具一直存在于 Composio MCP server 中。
Agent 读到这段描述后直接跳过图片上传，只发文字。

**修复**：完全重写 twitter-publishing.md，明确四步流程（见下文）。

---

## Twitter 图片发布正确流程

```
Step 0 — 把图片移到 /mnt/session/outputs/（仅 image_generate 输出需要）
  image_generate 把图片存在 /mnt/session/uploads/，必须先复制：
  bash: cp /mnt/session/uploads/{filename} /mnt/session/outputs/{filename}
  poster-design 的输出已在 /mnt/session/outputs/，跳过此步。

Step 1 — 上传到 Composio 存储，获取 s3key：
  upload_file(
    file_path    = "/mnt/session/outputs/{filename}",
    toolkit_slug = "twitter",
    tool_slug    = "TWITTER_UPLOAD_MEDIA"
  )
  → {s3key, name, mimetype}

Step 2 — 上传到 Twitter，获取 media_id：
  TWITTER_UPLOAD_MEDIA(
    media          = {s3key, name, mimetype},   # Step 1 完整返回值
    media_category = "tweet_image"
  )
  → data.media_id（纯数字字符串）

Step 3 — 发推附图：
  TWITTER_CREATION_OF_A_POST(
    text            = "推文内容",
    media_media_ids = ["{media_id}"]
  )
  → data.id = tweet_id
```

**关键限制：**
- Step 1 不可跳过：`TWITTER_UPLOAD_MEDIA` 只接受 Composio 内部 s3key，不接受 Supabase URL 或外部 URL
- `image_generate` 返回的 `url`（Supabase）和 `path`（`/mnt/session/uploads/`）**不能直接用作 s3key**
- `media_id` 有效期极短，Step 2 后立即执行 Step 3
- 多图（最多 4 张）：每张分别走 Step 0–2，收集所有 media_id 后一次传入 Step 3

---

## Twitter 视频为什么不可用

Composio MCP server（`votrix-post-agent`，id: `a335a1a1-de7a-4c4c-b8f9-eec0f6d67d1e`）
当前包含的 Twitter 媒体相关工具（共 168 个工具，78 个 Twitter）：

```
TWITTER_INITIALIZE_MEDIA_UPLOAD   ← 可以初始化
TWITTER_APPEND_MEDIA_UPLOAD       ← 可以追加分块
TWITTER_GET_MEDIA_UPLOAD_STATUS   ← 可以查询状态
TWITTER_UPLOAD_MEDIA              ← 仅支持图片（tweet_image / dm_image）
```

**缺失**：`TWITTER_FINALIZE_MEDIA_UPLOAD`、`TWITTER_UPLOAD_LARGE_MEDIA`

Twitter 的分块上传必须走三步：INIT → APPEND → FINALIZE。没有 FINALIZE，上传永远完不成，
用未 finalized 的 media_id 发推会返回 `"Your media IDs are invalid."`（已实验验证）。

`TWITTER_UPLOAD_LARGE_MEDIA`（deprecated）虽然在 Twitter toolkit 文档里存在（共 79 个工具），
但 Composio 生成 allowed_tools 时没有包含它，原因可能是它已标记为 deprecated。

---

## Instagram Reels 视频发布流程（正常可用）

`video_generate` 返回的是 Supabase 公开 URL，Instagram 的 `video_url` 参数直接接受公开 URL，
两者天然对接，无需 `upload_file` 中转：

```
Step 1 — 生成视频：
  video_generate(
    prompt          = "...",
    aspect_ratio    = "9:16",    # Reels 必须竖屏
    duration_seconds = 8
  )
  → {url}   ← 已是 Supabase 公开 URL

Step 2 — 创建 Reels 容器：
  INSTAGRAM_POST_IG_USER_MEDIA(
    ig_user_id    = {ig_user_id},
    video_url     = {url},
    media_type    = "REELS",
    share_to_feed = true,
    caption       = "文案 + hashtag"
  )
  → data.id = creation_id

Step 3 — 发布（视频需处理时间）：
  INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH(
    ig_user_id       = {ig_user_id},
    creation_id      = {creation_id},
    max_wait_seconds = 120
  )
  → data.id = post_id
```

---

## 实验记录

**实验 1**（失败）：直接用 Supabase URL 作为 s3key 传入 `TWITTER_UPLOAD_MEDIA`
→ 报错：`"Failed to download file with s3key '...': storage returned HTTP 404"`

**实验 2**（失败）：用 `TWITTER_INITIALIZE_MEDIA_UPLOAD` + `TWITTER_APPEND_MEDIA_UPLOAD` 分块上传
→ 成功获得 media_id `2048716579492270081`，但无法 FINALIZE
→ 用该 media_id 发推：`"Your media IDs are invalid."` (HTTP 400)

**实验 3**（成功）：走完整四步流程
→ `upload_file` → `{s3key}` → `TWITTER_UPLOAD_MEDIA` → `media_id: 2048719204270927872`
→ `TWITTER_CREATION_OF_A_POST` → tweet_id: `2048719267072282898` ✅

---

## 文件改动列表

| 文件 | 改动 |
|---|---|
| `app/tools/__init__.py` | 加 `upload_file` dispatch；改相对导入解决循环导入 |
| `agents/post-agent/config.json` | `composio_upload_file` → `upload_file` |
| `skills/social-media-post-publishing/references/twitter-publishing.md` | 完全重写，记录正确四步流程 |
