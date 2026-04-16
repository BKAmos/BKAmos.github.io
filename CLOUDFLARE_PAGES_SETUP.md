# Cloudflare Pages setup

This repository is configured to build as a Jekyll site on Cloudflare Pages.

## 1) Create the Pages project

1. In Cloudflare: **Workers & Pages** -> **Create application** -> **Pages**.
2. Choose **Connect to Git** and select this GitHub repository.
3. Select the production branch: `main`.

## 2) Build configuration

Use these settings in Cloudflare Pages:

- **Framework preset**: `None`
- **Build command**: `bundle exec jekyll build`
- **Build output directory**: `_site`

## 3) Environment variable

Add this environment variable in Cloudflare Pages project settings:

- `BUNDLE_WITHOUT` = `development:test`

This skips local-only gems and speeds up builds.

## 4) Formspree

The contact form endpoint is configured in `contact.md`:

`https://formspree.io/f/xojyejpl`

If you rotate or replace your Formspree form, update the `action` URL in `contact.md`.

## 5) Optional custom domain

After first successful deployment:

1. Open **Custom domains** in your Pages project.
2. Add your domain/subdomain.
3. Follow DNS prompts in Cloudflare.

