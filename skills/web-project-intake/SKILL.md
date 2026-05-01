---
name: web-project-intake
description: "Capture website requirements from the user. Triggered when the user wants to build a website, says 'new site', 'build website', 'create website', or when no project state exists."
integrations: []
---

# Web Project Intake

## Startup Check

Read `/workspace/pipeline_state.json`:

- **Does not exist** -- run the full flow from Phase 1
- **Exists with completed stages** -- offer to resume from where the pipeline left off, or start a new project (which overwrites existing state)
- **User specifies a section** (e.g. "change my pages") -- jump directly to the relevant phase and re-save

---

## Phase 1 -- Business Information

Collect the following from the user. Ask naturally, not as a form dump -- start with the business name and let the conversation flow.

| Field | Description | Required |
|-------|-------------|----------|
| business_name | Name of the business | Yes |
| business_type | One of: saas, restaurant, portfolio, ecommerce, agency, medical, real_estate, nonprofit, blog, other | Yes |
| site_purpose | What the website should accomplish (1-2 sentences) | Yes |

If the user provides a website URL or enough context, infer the business_type rather than asking explicitly.

---

## Phase 2 -- Pages

Present a predefined list of common pages based on the business_type. Let the user select from the list and add custom pages.

**Predefined pages by type:**

| Business Type | Suggested Pages |
|--------------|-----------------|
| saas | home, features, pricing, about, contact, blog, docs, changelog |
| restaurant | home, menu, about, contact, gallery, reservations, catering |
| portfolio | home, projects, about, contact, resume, blog |
| ecommerce | home, products, about, contact, cart, faq, returns |
| agency | home, services, portfolio, about, contact, blog, careers, case-studies |
| medical | home, services, about, contact, team, appointments, patient-portal, insurance |
| real_estate | home, listings, about, contact, agents, resources, testimonials |
| nonprofit | home, mission, programs, about, contact, donate, events, volunteer |
| blog | home, blog, about, contact, categories, newsletter |
| other | home, about, contact (ask the user for additional pages) |

The user can add any custom page not on the list. Record the final page list.

---

## Phase 3 -- Brand

Collect brand preferences:

| Field | Description | Default |
|-------|-------------|---------|
| primary_color | Primary brand color (hex) | Ask user |
| secondary_color | Secondary brand color (hex) | Complementary to primary |
| accent_color | Accent color (hex) | Optional |
| logo_url | URL to logo image | Optional |
| font_preference | One of: modern, classic, playful, minimal, custom | modern |
| custom_font | Font name if font_preference is custom | Only if custom |

If the user has no color preference, suggest a palette based on the business_type and industry conventions. Always confirm the final palette before proceeding.

---

## Phase 4 -- Content

For each page in the page list, ask the user if they want to:

1. **Provide content** -- paste or describe the content for that page
2. **Generate placeholders** -- the agent will create high-quality placeholder content based on the business info

For placeholder generation, produce realistic content that matches the business type and purpose -- not lorem ipsum. Include realistic headings, body text, and calls to action.

Record the content source for each page (user-provided or generated).

---

## Phase 5 -- Features

Present the feature list and let the user toggle each on or off:

| Feature | Description | Default |
|---------|-------------|---------|
| contact_form | Contact form with email delivery | On |
| booking_system | Appointment or reservation booking | Off |
| newsletter_signup | Email newsletter subscription form | Off |
| social_links | Social media profile links | On |
| analytics | Google Analytics or Plausible integration | On |
| seo_meta | SEO meta tags and Open Graph data | On |
| blog_cms | Blog with markdown or CMS content | Off |
| image_gallery | Image gallery or portfolio grid | Off |
| testimonials_carousel | Customer testimonials slider | Off |
| pricing_table | Pricing comparison table | Off |
| faq_accordion | FAQ section with expandable answers | Off |
| map_embed | Google Maps embed for location | Off |
| chat_widget | Live chat or chatbot widget | Off |
| cookie_banner | Cookie consent banner (GDPR) | Off |

Suggest enabling features that are commonly needed for the business_type (e.g. booking_system for restaurants, pricing_table for SaaS).

---

## Phase 6 -- Domain

Ask the user about their domain preference:

| Option | Description |
|--------|-------------|
| connect_domain | User has a domain and wants to connect it via Cloudflare |
| skip_domain | Use the default Vercel subdomain for now |

If `connect_domain`:
- Ask for the domain name (e.g. `example.com`)
- Confirm the user has access to the domain's DNS settings in Cloudflare
- Note: actual DNS configuration happens later in the pipeline (web-domain-manager and web-dns-binder)

If `skip_domain`:
- The site will be accessible at `{project-slug}.vercel.app`
- The user can connect a domain later

---

## Phase 7 -- Project Slug

Ask the user for a project slug (used for directory naming, GitHub repo name, and Vercel project name).

Rules for the slug:
- Lowercase letters, numbers, and hyphens only
- No spaces or special characters
- 3-50 characters

If the user has no preference, generate one from the business name (e.g. `acme-corp-website`).

---

## Phase 8 -- Save and Handoff

Present a complete summary of all collected information to the user. Wait for explicit confirmation before saving.

Write `/workspace/project_brief.json` (schema: `/mnt/skills/web-project-intake/reference/project_brief.schema.json`):

```json
{
  "business": {
    "name": "",
    "type": "",
    "purpose": ""
  },
  "pages": [],
  "brand": {
    "primary_color": "",
    "secondary_color": "",
    "accent_color": "",
    "logo_url": "",
    "font_preference": "",
    "custom_font": ""
  },
  "content": {},
  "features": {},
  "domain": {
    "strategy": "",
    "domain_name": ""
  },
  "project_slug": ""
}
```

Write `/workspace/pipeline_state.json`:

```json
{
  "current_stage": "web-project-intake",
  "completed_stages": ["web-project-intake"],
  "project_slug": "",
  "started_at": "",
  "updated_at": ""
}
```

Tell the user the project brief is saved and hand off to `web-template-selector`.

---

## Error Handling

| Error | Action |
|-------|--------|
| User provides incomplete business info | Ask follow-up questions for missing required fields |
| Invalid hex color code | Ask the user to re-enter or suggest a valid hex color |
| Project slug already exists | Warn the user and suggest an alternative slug |
| User wants to change a previous phase | Jump back to that phase, re-collect, and re-save |
| Pipeline state file is corrupted | Offer to start fresh or attempt to recover from partial state |
