# ComputGeneral

Minimal English organization website with CGI branding and two blogs.

- `index.md`: General Computing, General Rendering and General Intelligentia (CGI) entries.
- `_computing/*.md` and `_rendering/*.md`: articles, saved as Markdown with title/date front matter.
- `computing.md`, `rendering.md`, `_layouts/blog.html`: public article lists.
- `_layouts/post.html`: article pages, including an Edit link.
- `admin/`: Decap CMS, pinned to 3.17.1, with separate collections and image uploads.
- `assets/css/style.scss`: CGI-style public layout.
- `_config.yml`: site metadata, collection routes and CGI URL.

## Write a post

Select **New post** in either blog. Once OAuth is configured, sign in with a GitHub account with repository write access, compose Markdown in the editor, upload images if needed, and publish. Publishing commits the content to `main`; GitHub Pages builds the public article. The Edit link opens the article in the editor.

Until OAuth setup is complete, the editor page clearly indicates this and offers **Write on GitHub**, which opens GitHub's own authenticated editor with a Markdown template in the correct collection. Use a descriptive, unique filename, write the article, and commit to publish.

See [GitHub login setup](oauth/README.md) for the authenticator, callback registration and secret configuration. The OAuth client secret never belongs in this repository. `admin/settings.json` keeps login disabled until configured and verified.

## Publish and validate

Push to `main` to deploy with GitHub Pages. Article collections are initially empty. There are no invented or sample production posts. Run OAuth tests with `node --test tests/oauth.test.mjs`.

Previous site content remains available in Git history. Original theme license: `LICENSE`.
