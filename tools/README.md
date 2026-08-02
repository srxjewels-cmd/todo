# tools

Utilities for getting the SRX stock list out of wherever it lives and into a
chat. Unrelated to the todo CLI at the repo root — they just needed somewhere
to live.

Both emit the same four formats, so it doesn't matter which source you pull
from:

| format | good for |
| --- | --- |
| `md`   | pasting into an AI chat — a markdown table |
| `txt`  | pasting into a customer chat — one readable line per item |
| `csv`  | Sheets / Excel |
| `json` | feeding another script |

## `stock-export.js` — from the web app

A browser-console script. Open <https://srx-stock.web.app/>, DevTools → Console,
paste the whole file, Enter. (Chrome may want you to type `allow pasting` first.)
It copies a markdown table to your clipboard straight away.

It scrolls and clicks "load more" first, then reads whichever of these it finds:
the Firestore offline cache (the whole collection, not just the rendered page),
an HTML table, or a repeated card/grid layout.

Afterwards `__srx` is left on the page:

```js
__srx.copy('txt')      // to the clipboard in another format
__srx.download('csv')  // save to a file
__srx.rows             // the raw extracted rows
__srx.json(true)       // include hidden columns (image URLs, ids)
```

## `vdb-to-chat.mjs` — from the VDB API

Node 18+, no dependencies. Run it on your own machine; VDB's hosts are blocked
inside a Claude sandbox.

```bash
export VDB_API_KEY=...          # keep it out of the repo
node tools/vdb-to-chat.mjs --probe
node tools/vdb-to-chat.mjs --format md
node tools/vdb-to-chat.mjs --format csv --out stock.csv
```

VDB doesn't publish its API schema, so **start with `--probe`**. It makes one
request and reports where the items actually sit in the response, what fields
they have, which ones it recognises, and how pagination is signalled. Feed what
it prints back into `--fields` if the default column pick isn't what you want.

Endpoint and auth vary by account tier, so both are configurable:

```bash
--base https://api.vdbapp.com          # VDB_API_BASE
--endpoint /v1/diamonds                # VDB_ENDPOINT
--auth bearer                          # VDB_AUTH — also basic,
                                       #   header:X-Api-Key, query:api_key
```

`--help` lists the rest. The API key is redacted from all output, including
error messages.
