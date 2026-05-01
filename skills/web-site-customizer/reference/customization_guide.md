# Customization Guide

How to apply brand and content customizations to Next.js templates.

## Color Mapping

Map brand colors to Tailwind config `extend.colors`:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: '{brand.primary_color}',
        secondary: '{brand.secondary_color}',
        accent: '{brand.accent_color}',
      }
    }
  }
}
```

Templates use `text-primary`, `bg-primary`, `border-primary`, etc. throughout.

## Font Mapping

| Preference | Body Font | Heading Font | Google Fonts Import |
|------------|-----------|--------------|---------------------|
| modern | Inter | Inter | `Inter:wght@400;500;600;700` |
| classic | Merriweather | Playfair Display | `Merriweather:wght@400;700&Playfair+Display:wght@700` |
| playful | Poppins | Quicksand | `Poppins:wght@400;500;600&Quicksand:wght@700` |
| minimal | DM Sans | Space Grotesk | `DM+Sans:wght@400;500;700&Space+Grotesk:wght@700` |

Update `app/layout.tsx` or `pages/_app.tsx` with the Google Fonts import and font-family CSS variables.

## Content Data Files

Templates store content in one of these patterns:

### Pattern A: JSON data file
```
data/content.json
```
Replace values using jq:
```bash
jq --arg headline "$HEADLINE" '.home.hero.headline = $headline' data/content.json > tmp.json && mv tmp.json data/content.json
```

### Pattern B: TypeScript constants
```
lib/content.ts
```
Use sed or write the full file with the content values.

### Pattern C: MDX files
```
content/pages/about.mdx
```
Write MDX files directly with frontmatter and content.

## Section Types

Each template page is composed of configurable sections:

| Section Type | Fields | Used In |
|-------------|--------|---------|
| hero | headline, subheadline, cta_text, cta_url, image_url | All templates |
| features | items[] (title, description, icon) | SaaS, Agency, General |
| pricing | tiers[] (name, price, features[], cta) | SaaS, General |
| testimonials | items[] (quote, author, title, company, avatar) | Most templates |
| team | members[] (name, title, bio, image, social) | Agency, Medical, Nonprofit |
| gallery | images[] (url, alt, caption) | Restaurant, Portfolio, Real Estate |
| faq | items[] (question, answer) | Most templates |
| contact | fields[], recipient, success_message | All templates |
| cta | headline, body, cta_text, cta_url | All templates |
| menu | categories[] (name, items[] (name, description, price)) | Restaurant |
| stats | items[] (value, label) | Nonprofit, Agency |

## Metadata Configuration

Update `app/layout.tsx` metadata export:

```tsx
export const metadata: Metadata = {
  title: {
    template: '%s | {business_name}',
    default: '{business_name} - {tagline}',
  },
  description: '{default_description}',
  openGraph: {
    title: '{business_name}',
    description: '{default_description}',
    images: ['{og_image_url}'],
  },
}
```

## Feature Integration

### Contact Form
Replace the form action endpoint. For static sites, use Formspree or similar:
```json
{
  "action": "https://formspree.io/f/{form_id}",
  "fields": ["name", "email", "message"],
  "success_redirect": "/thank-you"
}
```

### Booking System
Link to external booking provider:
```json
{
  "provider": "cal.com",
  "url": "https://cal.com/{username}",
  "embed": true
}
```

### Social Links
Configure in the footer/header component data:
```json
{
  "twitter": "https://twitter.com/{handle}",
  "linkedin": "https://linkedin.com/company/{slug}",
  "instagram": "https://instagram.com/{handle}"
}
```
