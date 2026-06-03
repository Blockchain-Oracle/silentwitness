# refs/participant-repos — Known public competitor builds

The Devpost gallery is unpublished until after Jun 15 close. The only public competitor build we can analyze is one repo found via GitHub topic search.

---

## marez8505/find-evil

| Field | Value |
|---|---|
| URL | https://github.com/marez8505/find-evil |
| License | MIT |
| Stars / forks | 1 / 0 |
| Language | Python 63.4% + HTML + Shell |
| Pattern | Direct Agent Extension w/ multi-phase pipeline + Flask UI |
| Last commit | recent (June 2026) |

### Architecture (as readable from README)

**5-phase pipeline, each with self-correction:**

```
[Phase 1: Triage] → [Phase 2: Disk Timeline] → [Phase 3: Memory]
                                                     ↓
[Phase 5: Correlation] ←─────────── [Phase 4: Persistence]
```

Each phase emits JSON-formatted tool outputs with audit hashes. Flask web UI is bound to `127.0.0.1` with bcrypt-protected admin access.

### Scoring estimate against our rubric

| Criterion | Score | Why |
|---|---|---|
| Autonomous Execution Quality | ✓✓ | Per-phase self-correction is real but not closed-loop critic |
| IR Accuracy | ✓ – ✓✓ | No validation against authoritative source, no measured hallucination rate |
| Breadth & Depth | ✓✓ | 5 phases is broad-ish |
| Constraint Implementation | ✗ | Direct Extension; no MCP, no architectural enforcement |
| Audit Trail | ✓✓ | JSON + audit hashes — better than Protocol SIFT, worse than Valhuntir |
| Usability | ✓✓✓ | Flask web UI is friendlier than CLI-only |

**Likely placement:** Stage 1 pass, mid-pack Stage 2. Strong Usability but weak on the heavy-weight criteria.

### What we should copy

- **5-phase frame is clean and Mandiant-shaped.** Reuse this skeleton: Triage → Disk → Memory → Persistence → Correlation.
- **JSON outputs + audit hashes** is a credible audit floor. We exceed by matching Valhuntir (HMAC-signed ledger + content hashes).
- **Flask web UI bound to 127.0.0.1 + bcrypt** is a respectable security default. If we ship a UI, match these defaults.

### What we beat

- No MCP → we go MCP.
- No closed-loop critic → we build it.
- No hallucination measurement → we measure.
- No HMAC-signed approvals → we add (copy Valhuntir).
- No adversarial-evidence defense → we add the sanitizer wedge.

---

## How to discover more competitor repos as they appear

### GitHub search queries to run weekly

```bash
# Topic-based
gh search repos topic:find-evil --sort=updated --limit 50
gh search repos topic:protocol-sift --sort=updated --limit 50
gh search repos topic:sift-mcp --sort=updated --limit 50

# Full-text
gh search repos "find evil hackathon" --sort=updated --limit 50
gh search repos "protocol sift" --sort=updated --limit 50
gh search code "findevil.devpost.com" --limit 30
gh search code "protocol-sift" --limit 30
```

### GitHub web searches (for non-code mentions)

- https://github.com/topics/find-evil
- https://github.com/topics/protocol-sift
- https://github.com/topics/dfir-mcp
- https://github.com/topics/sift-mcp

### Devpost (after gallery opens)

After Jun 15 11:45 PM EDT:
- https://findevil.devpost.com/project-gallery
- https://findevil.devpost.com/submissions

Scrape each submission's GitHub URL, README, and Devpost description for retrospective analysis.

### Slack + Discord lurking

The richest signal is in:
- Protocol SIFT Slack: https://join.slack.com/t/sansaihackathon/shared_invite/zt-3zhbphvt0-3mMkKpBeUvll1DYwnr1yOA
- Discord: https://discord.com/invite/HP4BhW3hnp

Watch `#showcases`, `#help-mcp`, `#help-architecture`, `#general` for repo links and "I'm building X" posts.

---

## Action items

1. **Save GitHub search alerts** for `topic:find-evil` and `topic:protocol-sift` (email or RSS)
2. **Star marez8505/find-evil** so we get commit notifications
3. **Update this file** when new public builds surface
4. **Post-deadline (Jun 16+)**: scrape the full Devpost gallery and add to this file as a retrospective
