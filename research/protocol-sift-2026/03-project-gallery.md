# 03 — Project Gallery

**Scraped:** 2026-06-02
**Gallery URL:** https://findevil.devpost.com/project-gallery (and `/submissions`)
**Status:** **UNPUBLISHED.** Both URLs return:

> "The hackathon managers haven't published this gallery yet, but hang tight!"

This is normal for Devpost — galleries typically open after submissions close. We will not have public competitor intel until **at minimum after Jun 15 close**, more realistically after winners announced **on or around Jul 8 2026**.

## What this means strategically

1. **No public incumbent check is possible right now.** Cannot scrape competitor submissions to triangulate the field.
2. **The only known public competitor build** is `marez8505/find-evil` (see `04-competitor-analysis.md`) — found via GitHub search for the hackathon name.
3. **The only published quality bar** is Valhuntir (`AppliedIR/Valhuntir` + `sift-mcp`), which is explicitly named in the rules as "level of quality to meet/exceed."
4. **Competitive intel sources we DO have:**
   - Protocol SIFT Slack (private — invite at https://join.slack.com/t/sansaihackathon/...)
   - Discord (https://discord.com/invite/HP4BhW3hnp)
   - GitHub search for repos tagged `protocol-sift`, `find-evil`, `sift-mcp`
   - Devpost participants count (3,861 registered as of 2026-06-02) — gives us field size, not field shape

## Registered participants

- **3,861** total registered as of 2026-06-02 (verified on Devpost).
- Rob T. Lee tweeted in March 2026: "More than 1,400 solo builders and teams registered as of this morning. IR professionals, AI engineers, developers, students."
- Growth from 1,400 → 3,861 in ~2 months suggests strong late-stage signup. **Implication:** many of those late-registers won't finish a real submission; the real competitive field is likely 200-600 working submissions.

## Known public builds (GitHub-discoverable)

| Repo | Stars | Last commit | Maturity | Lane | Lane overlap with us |
|---|---|---|---|---|---|
| [AppliedIR/Valhuntir](https://github.com/AppliedIR/Valhuntir) | (active) | June 2026 | **Production** | Custom MCP + multi-tool + HITL | High — this is the quality bar (see `04-competitor-analysis.md`) |
| [marez8505/find-evil](https://github.com/marez8505/find-evil) | 1 | recent | Working build | 5-phase Direct Extension over Flask UI | Medium — solo-shaped competitor build |
| [teamdfir/protocol-sift](https://github.com/teamdfir/protocol-sift) | 15 | 2026-03-25 | Reference config bundle | Direct Extension w/o MCP | Low — this is the baseline, not a competitor |
| [bornpresident/Volatility-MCP-Server](https://github.com/bornpresident/Volatility-MCP-Server) | (unknown) | (pre-hackathon) | Single-purpose | Memory only | Low — covers 1 evidence type |
| [socfortress/velociraptor-mcp-server](https://github.com/socfortress/velociraptor-mcp-server) | 39 | (pre-hackathon) | Production-shaped | Live endpoint | Medium — gap-filler for live-host wedge |

(See `refs/participant-repos.md` for the full per-repo notes.)

## Action items derived from the gallery state

1. **Join Slack + Discord immediately** and lurk for signal: what are people building? What patterns are mentioned repeatedly? What questions get asked?
2. **GitHub-monitor `topic:find-evil`, `topic:protocol-sift`, and full-text search `"find evil hackathon"`** between now and Jun 15 to spot new entrant repos.
3. **Star and fork-watch Valhuntir + Protocol SIFT** so any new commits trigger awareness.
4. **Accept blind competition.** Build to the rubric and to Valhuntir-as-bar — the public field doesn't define the rules.

## Post-submission gallery action

When the gallery opens (Jul 8 area):
- Scrape every submission's name + GitHub + Devpost description
- For top-10 by track / by judge-mention: deep-read repo READMEs
- Build retrospective competitor matrix — useful for the next SANS hackathon

This is a future-self note; not relevant for the build itself.
