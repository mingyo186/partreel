# Credits — quality reports & contributions

Bug reports and quality feedback are contributions. Anyone whose report leads to
a fix is recorded here (and in the fix commit as `Reported-by:`), alongside code
and part contributors ([GitHub contributors](https://github.com/mingyo186/partreel/graphs/contributors),
imported-library authors in [ATTRIBUTIONS.md](ATTRIBUTIONS.md)).

## Quality reports

| Reporter | Report | Result |
|---|---|---|
| reddit u/asdfasdferqv | Footprint zoom "totally broken" (2026-07-24) | Exposed missing mobile pinch zoom → shipped touch pinch + scroll passthrough (`033e7013`) |
| reddit u/asdfasdferqv | Follow-up: it was a desktop **touchpad** (2026-07-25) | Root cause found — viewer hijacked all wheel events. Input redesign: plain scroll passes to page; pinch / double-click / zoom buttons (`192028ab`) |
| reddit u/Apart-Touch9277 | "5 pin JST" finds nothing; asked for semantic search (2026-07-26) | Search rebuilt on MiniSearch — word-order-independent, typo-tolerant, ranked (`63f9b570`, `9eea0651`) |

## Field reports

Real-board results reported via part-page issue links (worked / problem) are
credited on the part page badge and in the issue history.
