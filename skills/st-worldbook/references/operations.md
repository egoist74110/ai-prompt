# Local SillyTavern operations

These API and entry details were checked against local SillyTavern 1.18.0 source. Recheck the installed version's source or behavior when it differs.

## API and session

Use the discovered base URL and the intended ST user session. With CSRF protection enabled, `GET /csrf-token` returns `{token}` and sets a session cookie; retain the cookie and send `x-csrf-token: <token>` on POST requests. Preserve any authentication cookie as well. On a CSRF `403`, obtain a fresh token and session, then retry only a read request automatically. Do not blindly retry a write whose outcome is uncertain; inspect the book first. CSRF can be disabled in ST, so do not treat the handshake as proof of authentication.

| POST endpoint | Request | Result |
|---|---|---|
| `/api/worldinfo/list` | `{}` | Array of `{file_id, name, extensions}` |
| `/api/worldinfo/get` | `{name: file_id}` | Book data; `{entries:{}}` also represents a missing file |
| `/api/worldinfo/edit` | `{name: file_id, data: <full book object>}` | `{ok:true}`; atomically writes the supplied whole book |
| `/api/worldinfo/delete` | `{name: file_id}` | HTTP 200 on deletion |
| `/api/worldinfo/import` | `multipart/form-data` with file field `avatar`; optional `convertedData` string | `{name}`; writes by uploaded filename |

Use `file_id` from `/list` for `/get` and `/edit`; `name` may be a display name stored inside the JSON. `/import` requires an uploaded file even if `convertedData` is supplied. It can overwrite an existing book of the same filename. Most `/api/worldinfo/*` routes accept POST, not GET.

## Disk and enabled books

- Books: `<user-dir>/worlds/<file_id>.json` in the verified installation. The API resolves the current ST user's directory.
- Globally enabled books: `settings.json` → `world_info_settings.world_info.globalSelect`.
- Character binding: character card metadata `data.extensions.world`. An embedded card book is `data.character_book`; its entry shape differs from an on-disk worldbook. Character cards are usually PNGs containing metadata.
- Global scan settings are under `world_info_settings`.

## Safe edit sequence

1. Confirm the exact `file_id` appears in `/list` and on disk. A `/get` response containing empty `entries` is not proof that the file exists.
2. Copy the target JSON to a timestamped backup **outside `worlds/`**; a JSON backup inside `worlds/` appears as another book. Preserve the full original object, including top-level metadata and all unrelated entries.
3. GET the full book, modify only the intended fields in memory, and check the current file has not changed before POST. The endpoint has no conditional update, so avoid concurrent editors; if uncertain, re-read and merge or stop.
4. POST the complete object to `/edit`. Its file write is atomic, but the GET→edit→POST sequence is not a transaction.
5. Re-GET and compare the changed entries plus unchanged metadata and entries. If the POST response is lost or a retry is considered, inspect first. Report the backup location and exact change.

For an intentional new book, make creation explicit; do not infer it from the dummy `/get` response. Delete and import require their own explicit user request.

## Entry fields

On-disk book: `{ "entries": { "<uid>": <entry> } }`. For new entries, inspect the installed version's default entry template and allocate a unique `uid` and map key; do not replace a whole entry with only the fields listed here.

- `comment`: UI title/memo; `content`: injected content. The entry title is `comment`, not `name`.
- `key[]`: primary keywords. `keysecondary[]` is used when `selective` is true; `selectiveLogic`: `0=AND_ANY`, `1=NOT_ALL`, `2=NOT_ANY`, `3=AND_ALL`.
- `constant`: activates without matching keys, subject to other filters, disable state, probability, and budget. `disable`: entry off. `useProbability` and `probability`: activation roll.
- `group`, `groupWeight`, `groupOverride`: inclusion-group selection.
- `order`: higher values are considered first for activation and budget; final prompt placement can use a different order. `ignoreBudget` exempts an entry from the world-info budget check.
- `position`: `0=before character`, `1=after character`, `2=Author's Note top`, `3=Author's Note bottom`, `4=at depth`, `5=Example Messages top`, `6=Example Messages bottom`, `7=outlet`.
- `depth`: insertion depth when `position=4`; `role`: inserted message role at that depth (`0=system`, `1=user`, `2=assistant`). `scanDepth`: per-entry keyword scan depth.
- `sticky`, `cooldown`, `delay`: timed activation effects; `excludeRecursion`, `preventRecursion`, `delayUntilRecursion`: recursion behavior.
- `matchPersonaDescription`, `matchCharacterDescription`, `matchCharacterPersonality`, `matchCharacterDepthPrompt`, `matchScenario`, `matchCreatorNotes`: additional keyword match sources.
- Other fields include `triggers[]`, `automationId`, `outletName`, `vectorized`, `displayIndex`, and `extensions`; preserve existing values unless the requested change calls for them.
