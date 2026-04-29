# Agent Config Template

```json
{
  "agentId":  "your-agent-id",          // 必填，唯一标识，用于查找 agents/{agentId}/ 目录
  "name":     "Your Agent Name",        // 必填，显示名称
  "model":    "claude-haiku-4-5-20251001", // 可选，默认 haiku；复杂任务用 claude-sonnet-4-6
  "envId":    "env_xxx",                // 必填，Anthropic environment ID

  "skills": [                           // 可选，技能列表（slug，对应 skills/{slug}/）
    "skill-slug-one"
  ],

  "integrations": [                     // 可选，Composio integration 列表
    {
      "slug": "gmail",                  // 必填，Composio toolkit slug
    },
    {
      "slug": "instagram"               // 不写 tools = 所有工具都可用
    }
  ],

  "tools": [                            // 可选，自定义工具列表（从以下选填）
    "manage_connections",               // OAuth 连接管理（有 integrations 时必加）
    "cron_create",                      // 定时任务 - 创建
    "cron_delete",                      // 定时任务 - 删除
    "cron_list",                        // 定时任务 - 列出
    "image_generate"                    // AI 图片生成
  ]
}
```

## 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `agentId` | ✅ | 目录名，`agents/{agentId}/` |
| `name` | ✅ | Agent 显示名称 |
| `model` | ❌ | 默认 `claude-haiku-4-5-20251001` |
| `envId` | ✅ | Anthropic environment ID |
| `skills` | ❌ | 技能 slug 列表，对应 `skills/` 目录 |
| `integrations[].slug` | ✅ | Composio toolkit slug，如 `gmail`、`instagram` |
| `integrations[].tools` | ❌ | 不填 = 该 integration 所有工具都启用；**注意：只要任意一个 integration 填了 tools，所有未填 tools 的 integration 工具会被屏蔽。要么全填，要么全不填** |
| `tools` | ❌ | 自定义工具，有 integrations 时记得加 `manage_connections` |
