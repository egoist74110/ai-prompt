---
name: figma
description: "Read Figma design files (node structure, styles, images). Parses file_key + node_id from a Figma URL and calls the REST API with a PAT to fetch design data. Use when the intent matches a design link, Figma, or extracting design parameters."
---

# figma — Figma design file reader

Goal: read Figma design node data (structure, styles, colors, spacing) by calling the Figma REST API directly with a local PAT, without depending on the Figma MCP or a browser.

## 0. Reuse verified local state first

Resolve all repository-relative paths from the directory containing `router.md`.

Check `.local/runtime.json` first:

- `credentials.figma_pat`

If cached and the file exists, **use it directly — do not re-discover**.

Only re-run discovery when:

1. this skill has never run on this machine;
2. the cached file path no longer exists (file moved/deleted);
3. the API call returns 401/403 (token invalid).

After discovery succeeds, write the locator back to `.local/runtime.json`. Never write the PAT itself into the cache in plaintext.

## 1. Locating the PAT

### Known sources (priority order)

1. `.local/runtime.json` → `credentials.figma_pat` (type + path)
2. Common path probing (read-only, never print contents):
   - `/mnt/.config/figma/token`
   - `~/.config/figma/token`
   - `~/.config/figma/pat`
3. If none exist → ask the user for the PAT file path, then write it back to runtime.

### Cache format

```json
{
  "figma_pat": {
    "type": "file",
    "path": "<machine-local-path>",
    "note": "Figma Personal Access Token, plain single-line text; once read, use only for the X-Figma-Token header — never print it in plaintext"
  }
}
```

## 2. Parsing parameters from a Figma URL

Figma URL format:
```
https://www.figma.com/design/<file_key>/<file_name>?node-id=<node_id>&...
https://www.figma.com/file/<file_key>/<file_name>?node-id=<node_id>&...
```

Parsing rules:
- `file_key`: first path segment after `/design/` or `/file/`
- `node_id`: the `node-id` query parameter, formatted like `3071-2`; keep the `-` as-is for API calls
- If `node-id` is absent, the whole file is targeted (large — use with caution)

## 3. API calls

Base URL: `https://api.figma.com`
Auth header: `X-Figma-Token: <PAT>`

### Read a specific node (most common)

```bash
curl -s -H "X-Figma-Token: <PAT>" \
  "https://api.figma.com/v1/files/<file_key>/nodes?ids=<node_id>&geometry=paths"
```

- `ids` supports multiple values, comma-separated: `ids=3071-2,3071-5`
- `geometry=paths` returns vector path data (optional — omit when image rendering isn't needed)
- Response JSON: `nodes["<node_id>"].document` is the node tree

### Read the whole file (use with caution, slow for large files)

```bash
curl -s -H "X-Figma-Token: <PAT>" \
  "https://api.figma.com/v1/files/<file_key>"
```

### Download node images (PNG/SVG)

```bash
curl -s -X POST -H "X-Figma-Token: <PAT>" \
  -H "Content-Type: application/json" \
  -d '{"nodes":[{"id":"<node_id>","renderOptions":{"format":"png","scale":2}}],"format":"png"}' \
  "https://api.figma.com/v1/images/<file_key>"
```

Response: `{"images": {"<node_id>": "https://..."}}` — returns an image URL; download it with another curl call.

### Read file metadata (verify the token)

```bash
curl -s -H "X-Figma-Token: <PAT>" "https://api.figma.com/v1/me"
```

Note: a 403 from `/v1/me` **does not by itself mean the PAT is invalid** — a token scoped to file-read-only can also get 403 there. Trust an actual file read instead.

## 4. Reading the node tree

The `document` field is the Figma node tree. Key properties:

| Field | Meaning |
|------|------|
| `type` | FRAME / TEXT / RECTANGLE / VECTOR / GROUP / COMPONENT, etc. |
| `name` | layer name |
| `absoluteBoundingBox` | `{x, y, width, height}` absolute coordinates |
| `fills` | fill (`type: "SOLID"` → `color: {r,g,b,a}` in 0-1 range) |
| `strokes` | stroke |
| `cornerRadius` / `rectangleCornerRadii` | corner radius |
| `style` | TEXT node's `fontSize`, `fontWeight`, `letterSpacing`, `lineHeightPx` |
| `characters` | TEXT node's text content |
| `constraints` | auto-layout constraints |
| `layoutMode` | HORIZONTAL / VERTICAL / NONE (auto-layout) |
| `itemSpacing` | auto-layout spacing |
| `paddingLeft/Right/Top/Bottom` | auto-layout padding |
| `children` | array of child nodes |

### Color conversion

Figma colors `r/g/b` are 0-1 floats. Convert to hex:
```
hex = "#{Math.round(r*255).toString(16).padStart(2,'0')}..."
```

### Sizing

Figma design sizes are already in px (for a 750-wide mobile design, the project's postcss-pxtorem converts to rem automatically — just write the design's px value directly).

## 5. Workflow

1. Parse `file_key` + `node_id` from the Figma URL the user provided
2. Get the PAT from cache/discovery (never print it)
3. `curl` the nodes API to fetch the node tree
4. Parse the JSON and extract the needed info (layout, colors, font size, spacing, copy)
5. Map the design parameters onto the code implementation
6. If a visual reference is needed, call the images API to download a PNG screenshot

## 6. Caveats

- The PAT is sensitive: never print it, never commit it to the repo, never write it to logs
- For large files (>100 pages), avoid reading the whole file — read specific nodes only
- `geometry=paths` makes responses much larger — only add it when vector path data is actually needed
- Image download URLs are time-limited (usually a few hours) — download immediately
- A design's auto-layout parameters (`layoutMode`, `itemSpacing`, padding) map directly to CSS flex properties

## 7. Wrap-up

- Report which nodes were read and which design parameters were extracted
- If a new PAT path was discovered and verified successfully, confirm it was written back to `.local/runtime.json`
