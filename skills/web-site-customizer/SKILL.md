---
name: web-site-customizer
description: "Clone the selected template, customize branding and content, push to GitHub. Triggered after template selection is confirmed, or when the user says 'customize site', 'apply branding', 'edit template', 'update content'."
integrations: []
---

# Web Site Customizer

## Startup Check

Read `/workspace/project_brief.json` and `/workspace/template_selection.json`:

1. Confirm both files exist and are valid -- if not, tell the user which prior step to run
2. Check `/workspace/pipeline_state.json` to verify web-template-selector is in `completed_stages`
3. Confirm `template_selection.json` has `confirmed: true`

Read `/workspace/site_config.json` if it exists:
- Already has a pushed repo -- ask the user if they want to re-customize or keep the current version
- Has partial progress -- resume from the last completed phase

---

## Phase 1 -- Clone Template

Clone the selected template from the `votrix-site-templates` GitHub org:

```bash
git clone https://github.com/votrix-site-templates/{template_repo}.git /workspace/{project_slug}
cd /workspace/{project_slug}
rm -rf .git
git init
```

Git tokens are pre-configured in the sandbox. Do not ask the user for credentials.

---

## Phase 2 -- Explore Template Structure

**This is the most important phase.** Before making any changes, understand the template's codebase like a developer would.

Read and analyze these files (paths may vary per template):
- `package.json` -- dependencies, scripts, framework version
- `tailwind.config.js` or `tailwind.config.ts` -- theme configuration, color definitions, font setup
- `next.config.js` or `next.config.mjs` -- Next.js configuration
- `app/layout.tsx` or `src/app/layout.tsx` -- root layout, global styles, font imports
- `app/page.tsx` or `src/app/page.tsx` -- home page structure
- Content files -- look for `/content/`, `/data/`, `/config/`, or `/lib/` directories with site content
- Component files -- look for `/components/` to understand the UI component library

Build a mental map of:
- Where colors are defined (Tailwind config, CSS variables, or inline)
- Where fonts are loaded (layout file, CSS, or config)
- Where content lives (hardcoded in pages, separate data files, or CMS)
- How navigation is structured (header component, config file, or layout)
- How pages are organized (app router structure)

**Key principle:** Do not assume file paths. Each template has its own structure. Read the code and adapt your approach accordingly. Refer to `/mnt/skills/web-site-customizer/reference/customization_guide.md` for common patterns and best practices.

---

## Phase 3 -- Apply Branding

Using the brand settings from `project_brief.json`:

**Colors:**
- Update the Tailwind config to add or override colors under `extend.colors`:
  - `primary` -- maps to the project's primary_color
  - `secondary` -- maps to the project's secondary_color
  - `accent` -- maps to the project's accent_color (if provided)
- Update any CSS variables or theme files that reference brand colors
- Replace hardcoded color values in components where appropriate

**Fonts:**
- Based on font_preference, select and configure an appropriate Google Font:
  - modern -- Inter, Plus Jakarta Sans, or similar
  - classic -- Merriweather, Playfair Display, or similar
  - playful -- Poppins, Quicksand, or similar
  - minimal -- DM Sans, Space Grotesk, or similar
  - custom -- use the specified custom_font name
- Update the root layout to import the font via `next/font/google`
- Apply the font to the body or main content wrapper

**Logo:**
- If logo_url is provided, download the logo and place it in the `/public/` directory
- Update the header/navbar component to use the logo image
- If no logo_url, use the business_name as text in the header

---

## Phase 4 -- Apply Content

For each page in the project's page list:

**If user-provided content exists:**
- Replace the template's placeholder content with the user's content
- Maintain the template's component structure and styling
- Adapt the content to fit the template's layout patterns

**If generating placeholder content:**
- Write realistic, business-appropriate content based on the business info
- Match the tone to the business_type (professional for medical, creative for portfolio, etc.)
- Include realistic headings, body paragraphs, calls to action, and meta descriptions
- Never use lorem ipsum or obviously fake content

---

## Phase 5 -- Configure Features

For each enabled feature in `project_brief.json`, configure it in the codebase:

| Feature | Implementation Approach |
|---------|------------------------|
| contact_form | Add form component with action endpoint (or Formspree/similar) |
| booking_system | Add booking widget or link to external booking service |
| newsletter_signup | Add email capture form (Mailchimp embed or similar) |
| social_links | Add social media icons with links to footer/header |
| analytics | Add Google Analytics or Plausible script to layout |
| seo_meta | Add meta tags and Open Graph data to each page's metadata export |
| blog_cms | Set up blog directory with markdown support if not already present |
| image_gallery | Add gallery component with grid layout |
| testimonials_carousel | Add testimonials slider component with placeholder data |
| pricing_table | Add pricing comparison component |
| faq_accordion | Add FAQ section with expandable items |
| map_embed | Add Google Maps iframe to contact page |
| chat_widget | Add chat widget script to layout |
| cookie_banner | Add cookie consent banner component |

For features the template already supports, configure them. For missing features, create new components following the template's existing patterns and design language.

---

## Phase 6 -- Build Navigation

Using the final page list:

1. Read the template's existing navigation component or config
2. Update the navigation items to match the project's page list
3. Ensure all pages are linked in both the header navigation and footer
4. Add mobile-responsive navigation if not already present

---

## Phase 7 -- Create Missing Pages

For pages in the project's page list that do not exist in the template:

1. Identify the template's page pattern (app router structure, shared layouts, component imports)
2. Create new page files following the same pattern
3. Use the template's existing components and styles for consistency
4. Apply the appropriate content from Phase 4

---

## Phase 8 -- Preview Summary

Present a summary of all customizations to the user:

```
Customization Summary
------------------------------------
Template:         {template_name}
Project:          {project_slug}
------------------------------------
Brand Applied:
  Colors:         {primary} / {secondary} / {accent}
  Font:           {font_name} ({font_preference})
  Logo:           {logo status}
------------------------------------
Pages:            {N} total
  From template:  {list}
  Created new:    {list}
------------------------------------
Features:         {N} enabled
  Configured:     {list}
  Custom-built:   {list}
------------------------------------
Content:
  User-provided:  {N} pages
  Generated:      {N} pages
------------------------------------
```

Ask the user if they want to adjust anything before pushing to GitHub. If they request changes, loop back to the appropriate phase.

---

## Phase 9 -- Push to GitHub

Once the user confirms the customization:

1. Create a new repository in the `votrix-site-deploys` org:

```bash
cd /workspace/{project_slug}
git add .
git commit -m "Initial customized site: {business_name}"
git remote add origin https://github.com/votrix-site-deploys/{project_slug}.git
git push -u origin main
```

2. Verify the push was successful by checking the remote.

---

## Phase 10 -- Save and Handoff

Write `/workspace/site_config.json` (schema: `/mnt/skills/web-site-customizer/reference/site_config.schema.json`):

```json
{
  "project_slug": "",
  "template_id": "",
  "template_name": "",
  "github_repo": "votrix-site-deploys/{project_slug}",
  "github_url": "https://github.com/votrix-site-deploys/{project_slug}",
  "commit_sha": "",
  "customizations": {
    "colors": {},
    "font": "",
    "logo": "",
    "pages_from_template": [],
    "pages_created": [],
    "features_configured": [],
    "features_custom_built": [],
    "content_user_provided": [],
    "content_generated": []
  },
  "pushed_at": ""
}
```

Update `/workspace/pipeline_state.json`:
- Add `"web-site-customizer"` to `completed_stages`
- Set `current_stage` to `"web-site-customizer"`
- Update `updated_at` timestamp

Tell the user the customized site is pushed to GitHub and hand off to `web-vercel-deployer`.

---

## Error Handling

| Error | Action |
|-------|--------|
| Template repo not found or clone fails | Verify the template_repo value, check network access, report the error |
| Git push fails (auth) | Verify git tokens are configured in the sandbox; do not ask the user for credentials |
| Git push fails (repo exists) | Offer to use a different project slug or force-push if the user confirms |
| Build errors in customized code | Read error output, fix the issue, rebuild and verify before pushing |
| User requests changes after push | Create a new commit with the changes and push again |
| Template structure is unexpected | Adapt the approach -- read the code and figure out the correct file paths |
