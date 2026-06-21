# Consolidated chat interfaces

Refactored embed-safe chat HTML: shared templates, JSON config, and a build script. Generated files in this folder are self-contained for iframe embeds.

## Layout

- `src/templates/` — shared HTML templates (`base`, `extended`, `extended_save`)
- `src/chat_pages.json` — per-page webhook URLs, session keys, welcome text, document save settings
- `src/lib/chat_document_save.js` — document fetch/save library (inlined into save pages at build time)
- `scripts/build_chat_interfaces.py` — build script
- `chat_interface*.html` — generated output (deploy these)

## Build

From the repo root:

```bash
python consolidated/scripts/build_chat_interfaces.py
```

Or from this folder:

```bash
cd consolidated && python scripts/build_chat_interfaces.py
```

This regenerates all `chat_interface*.html` files in `consolidated/`.

## Add or change a page

1. Edit `src/chat_pages.json`
2. Run the build script above

For shared UI or chat logic, edit files under `src/templates/` instead of the generated HTML.

To recreate templates from HTML (rare):

```bash
python consolidated/scripts/bootstrap_templates.py
```
