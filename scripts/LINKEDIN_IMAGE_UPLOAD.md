# LinkedIn 带图片发帖问题记录

## 问题现象

调用 `LINKEDIN_CREATE_LINKED_IN_POST` 带图片时报错：

```
Failed to download file with s3key 'urn:li:image:D5610AQFDXhzuX6zksw':
storage returned HTTP 404. The file may not exist, may have been deleted,
or the download URL may have expired.
```

---

## 根本原因

### Composio 的 `images` 参数是 FileUploadable 类型

`LINKEDIN_CREATE_LINKED_IN_POST` 的 `images` 字段不接受：
- LinkedIn image URN（`urn:li:image:XXXX`）
- 公开 URL（`https://...`）
- Supabase 路径

它只接受 `{name, s3key, mimetype}` 格式，其中 `s3key` 必须是 **Composio 自己 S3 里的文件路径**。

Composio 的处理流程是：
1. 收到 tool call
2. 用 `s3key` 从自己的 S3 下载文件字节
3. 把文件上传到目标平台（LinkedIn）
4. 再执行 API 调用

所以如果 `s3key` 对应的文件不在 Composio 的 S3 里，就会 404。

### 试过但行不通的方案

| 尝试 | 结果 | 原因 |
|---|---|---|
| `images: [{url: "https://..."}]` | 报错：missing s3key, name, mimetype | Composio 不接受 URL 格式 |
| `images: [{id: "urn:li:image:XXXX"}]` | 404 | Composio 把 id 当 s3key，找自己 S3 找不到 |
| `images: [{s3key: "supabase路径", ...}]` | 404 | Supabase 不是 Composio 的 S3 |
| `LINKEDIN_INITIALIZE_IMAGE_UPLOAD` + curl PUT + `images: [{id: urn}]` | 404 | 同上，Composio 仍然找自己的 S3 |
| `LINKEDIN_REGISTER_IMAGE_UPLOAD` + curl PUT + `LINKEDIN_CREATE_ARTICLE_OR_URL_SHARE` | 报错 | 该工具只支持 ARTICLE/NONE 类型，不支持图片 |

---

## 正确方案

### Composio 官方 File Upload API

从 `https://backend.composio.dev/api/v3/openapi.json` 找到官方接口：

**Step 1 — 请求 presigned 上传 URL**

```
POST https://backend.composio.dev/api/v3/files/upload/request
x-api-key: {COMPOSIO_API_KEY}

{
  "toolkit_slug": "linkedin",
  "tool_slug": "LINKEDIN_CREATE_LINKED_IN_POST",
  "filename": "image.jpeg",
  "mimetype": "image/jpeg",
  "md5": "{文件的 MD5 hex}"
}

→ {
    "key": "287960/linkedin/LINKEDIN_CREATE_LINKED_IN_POST/request/d94937c4...",  ← 这就是 s3key
    "new_presigned_url": "https://storage.composio.dev/...",
    "metadata": {"storage_backend": "s3"}  // 或 "azure_blob_storage"
  }
```

**Step 2 — PUT 文件字节到 presigned URL**

```
PUT {new_presigned_url}
Content-Type: image/jpeg
# 如果 storage_backend 是 azure_blob_storage，还需要：
# x-ms-blob-type: BlockBlob

Body: <图片二进制>

→ 201 成功
```

**Step 3 — 用 s3key 发帖**

```
LINKEDIN_CREATE_LINKED_IN_POST(
  author    = "urn:li:organization:{org_id}",
  commentary = "...",
  images    = [{s3key: "287960/linkedin/.../d94937c4...", name: "image.jpeg", mimetype: "image/jpeg"}],
  visibility = "PUBLIC",
  lifecycleState = "PUBLISHED"
)
→ {"x_restli_id": "urn:li:share:7454468725623328769"}  ✅
```

---

## 实现

新增工具 `composio_upload_file`（`app/tools/composio_files.py`）封装上述三步：

1. 从 Anthropic Files API 下载文件字节（文件必须在 `/mnt/session/outputs/`）
2. 计算 MD5
3. 调 `/api/v3/files/upload/request` 拿 presigned URL + s3key
4. PUT 文件到 presigned URL
5. 返回 `{s3key, name, mimetype}`

Agent 调用示例：

```
# image_generate 的图片在 uploads/，需先 cp 到 outputs/
bash: cp /mnt/session/uploads/generated_xxx.jpeg /mnt/session/outputs/image.jpeg

composio_upload_file(
  file_path    = "/mnt/session/outputs/image.jpeg",
  toolkit_slug = "linkedin",
  tool_slug    = "LINKEDIN_CREATE_LINKED_IN_POST"
)
→ {s3key: "...", name: "image.jpeg", mimetype: "image/jpeg"}

LINKEDIN_CREATE_LINKED_IN_POST(images=[{s3key: "...", name: "...", mimetype: "..."}], ...)
→ ✅ 发布成功
```

---

## 注意事项

- `new_presigned_url` 有时效（通常 15–60 分钟），`upload/request` 和 PUT 必须连续执行
- `upload/request` 需要 `x-api-key`（Composio API key），是官方 API，在 OpenAPI spec 中有文档
- `composio_upload_file` 要求文件在 `/mnt/session/outputs/`（通过 `publish_file` 或直接写入触发 Files API 注册）
- `image_generate` 生成的图片默认在 `/mnt/session/uploads/`，需 `cp` 到 `outputs/`
