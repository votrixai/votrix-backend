# Agent Config Template

```json
{
  "agentId":  "your-agent-id",          // Required, unique identifier, used to locate the agents/{agentId}/ directory
  "name":     "Your Agent Name",        // Required, display name
  "model":    "claude-haiku-4-5-20251001", // Optional, defaults to haiku; use claude-sonnet-4-6 for complex tasks
  "envId":    "env_xxx",                // Required, Anthropic environment ID

  "skills": [                           // Optional, list of skills (slugs, corresponding to skills/{slug}/)
    "skill-slug-one"
  ],

  "integrations": [                     // Optional, list of Composio integrations
    {
      "slug": "gmail",                  // Required, Composio toolkit slug
    },
    {
      "slug": "instagram"               // Omitting tools = all tools are available
    }
  ],

  "tools": [                            // Optional, list of custom tools (pick from the following)
    "manage_connections",               // OAuth connection management (must include when integrations are present)
    "cron_create",                      // Scheduled tasks - create
    "cron_delete",                      // Scheduled tasks - delete
    "cron_list",                        // Scheduled tasks - list
    "image_generate"                    // AI image generation
  ]
}
```

## Field Descriptions

| Field | Required | Description |
|------|------|------|
| `agentId` | ✅ | Directory name, `agents/{agentId}/` |
| `name` | ✅ | Agent display name |
| `model` | ❌ | Defaults to `claude-haiku-4-5-20251001` |
| `envId` | ✅ | Anthropic environment ID |
| `skills` | ❌ | List of skill slugs, corresponding to the `skills/` directory |
| `integrations[].slug` | ✅ | Composio toolkit slug, e.g. `gmail`, `instagram` |
| `integrations[].tools` | ❌ | Omitting = all tools for that integration are enabled; **Note: if any integration specifies tools, all integrations without tools specified will have their tools blocked. Either specify tools for all, or for none** |
| `tools` | ❌ | Custom tools; remember to add `manage_connections` when integrations are present |
