# 01 — DFIR Foundations

> Domain knowledge for SilentWitness. Pure facts about how digital forensics and incident response is actually practiced. No architecture prescription — downstream design agents will decide how the agent embodies (or rejects) what is described here.

> **How to read this file:** Start at the top if you have never done DFIR. Skim to §12 (vocabulary) if you only need to look up a term. The mental models in §3, §4, §6, §8 are the ones a senior analyst carries into every case — those are the load-bearing sections for designing a hypothesis-first investigator.

> **Sources are cited inline.** Anything speculative is marked *(speculative)*. When this file says "common practice" it means: documented in SANS course material and observed in multiple practitioner blogs / DFIR Summit talks; not a single-source claim.

---

## Table of contents

1. What DFIR is (and what it is not)
2. The classical incident response lifecycle
3. Triage as a discipline
4. The senior analyst mental model
5. The order of volatility
6. "Finding Evil" / "Hunt Evil" — the SANS doctrine
7. The Pyramid of Pain
8. Hypothesis-driven investigation in practice
9. Multi-artifact corroboration patterns
10. Chain of custody (operational, not legal)
11. The DFIR analyst's day (sketch — deep version lives in `user/09`)
12. DFIR vocabulary glossary
13. SANS DFIR doctrine in five bullets
14. Common analytical anti-patterns

---

## 1. What DFIR is (and what it is not)

### 1.1 The two halves

**DFIR** stands for **Digital Forensics and Incident Response**. The name is a compound for a reason: in modern practice the two halves are inseparable on a live engagement, but historically and methodologically they were distinct, and the distinction still matters when you read older literature, court rulings, or job postings.

- **Digital forensics** (DF) — the scientific examination of digital evidence. Roots in law enforcement and the 1990s "computer forensics" world: seize the hard drive, image it, examine the image with rigorous documentation so the work can survive cross-examination in court. The discipline grew out of FBI / Secret Service casework, SANS' FOR500 (Windows Forensic Analysis) curriculum, Brian Carrier's *File System Forensic Analysis* (Addison-Wesley, 2005) which formalized the file-system layer, and the early Encase / FTK commercial tooling. Forensics is *retrospective* — you are reconstructing what happened from durable traces.

- **Incident response** (IR) — the operational discipline of detecting, containing, eradicating, and recovering from a security incident in real time. Roots in the CERT/CC and the original DoD incident handling guidance from the early 1990s. SANS' FOR508 (Advanced Incident Response, Threat Hunting, and Digital Forensics) is the modern codification. IR is *prospective and time-pressured* — you are stopping the bleeding while it bleeds.

In a 2026 enterprise engagement these are no longer two jobs. A senior IR consultant arriving on-site at 3 AM does both: they pull memory and disk images (forensics) while simultaneously isolating hosts and rotating credentials (IR). The combined acronym DFIR reflects how the work is sold and how the SANS GIAC certifications (GCFA, GCFE, GREM, GCIH, GNFA) bundle the skills.

### 1.2 How DFIR differs from neighboring disciplines

The hackathon judges include SOC managers, threat hunters, and red-teamers. Knowing what DFIR is *not* matters because the wedge sits inside DFIR and the neighboring disciplines have different success criteria.

- **SOC analysis** — the SOC (Security Operations Center) runs tier-1 / tier-2 / tier-3 triage of alerts produced by SIEMs (Splunk, Sentinel, Chronicle), EDRs (CrowdStrike Falcon, SentinelOne, Microsoft Defender for Endpoint), and detection engineering pipelines (Sigma, Snort, Suricata). SOC analysts work in alerts and tickets. Their core question is "does this alert represent a real attack?" — a *triage* question. SOC tier-3 work shades into DFIR but stops at the boundary of needing to image evidence or write a defensible incident report. SOC analysts measure themselves on MTTD (mean time to detect) and MTTR (mean time to respond). DFIR consultants are often called *into* a SOC when an alert has confirmed a real intrusion.

- **Threat hunting** — proactive, hypothesis-led search through telemetry for badness that has not yet alerted. The seminal vocabulary comes from David Bianco's "The Pyramid of Pain" (2013, see §7) and Sqrrl's "Hunt Evil" white paper series (2015–2017). A threat hunter starts with a hypothesis like "an adversary is using WMI for lateral movement in our environment" and crafts queries against EDR / Sysmon / SIEM data to confirm or refute it. They look like DFIR analysts but they work without a confirmed incident — they are trying to find the incident before it's declared. SANS FOR508 explicitly teaches threat hunting as a DFIR-adjacent skill. Note: **hypothesis-driven** is a methodological label that applies to both threat hunting *and* the post-incident DFIR triage described in §3 of this file; the wedge for SilentWitness is hypothesis-driven *triage and reporting*, which sits inside DFIR proper.

- **Red team** — adversary emulation. Authorized attackers (internal or external consultants) who attempt to compromise the environment to test defenses. They are the *source* of TTPs that blue teams must learn to detect. DFIR analysts often consume red-team reports to know what attack patterns are in scope. The methodology is completely different (offensive security uses tools like Cobalt Strike, Mythic, Sliver, BloodHound) and the success metric is opposite (the red team wins by *not* being detected).

- **Malware reverse engineering (RE)** — analyzing malicious binaries to understand capability, C2 protocols, persistence mechanisms. SANS FOR610 (Reverse-Engineering Malware) is the canonical course. DFIR analysts on a triage engagement usually do *not* deep-RE samples — they extract IOCs, hand the sample to an RE specialist or to VirusTotal / Hybrid Analysis / Joe Sandbox, and keep moving on the host work. The exception: senior DFIR consultants who hold GREM and do live RE during an engagement when speed matters.

- **eDiscovery** — the legal-discovery cousin of digital forensics. Same imaging and chain-of-custody discipline, completely different goal (responsive documents for a civil lawsuit, not evidence of attacker behavior). Tools overlap (Relativity, EnCase) but the people don't.

The wedge for SilentWitness is *DFIR triage and reporting*. It is not SOC alert triage, not threat hunting, not RE, not eDiscovery. The senior analyst persona — the FOR508 graduate, GCFA-holding consultant — is the user. The neighboring disciplines matter for vocabulary recognition and for understanding what judges from those backgrounds will be looking for.

---

## 2. The classical incident response lifecycle

Every IR program in the world traces its lineage to a small number of published frameworks. They differ in flavor but converge on the same five-or-six-stage skeleton. A practitioner can switch between frameworks during a single engagement without anyone noticing.

### 2.1 NIST SP 800-61 Rev. 2 — the U.S. canonical reference

**NIST Special Publication 800-61 Revision 2**, *Computer Security Incident Handling Guide* (Cichonski, Millar, Grance, Scarfone; National Institute of Standards and Technology; August 2012; https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final) is the document U.S. federal agencies, defense contractors, and a substantial fraction of regulated industries are required (or strongly encouraged) to follow. It defines four phases:

1. **Preparation** — building the IR program before an incident: policy, team, training, jump bag, communication plans, retainers with consultants, EDR deployment, log centralization, baseline images, tabletop exercises.

2. **Detection & Analysis** — alerting, triage, scoping, evidence collection, initial categorization (functional impact, information impact, recoverability). This is where most DFIR triage work lives.

3. **Containment, Eradication, & Recovery** — short-term containment (isolate hosts), long-term containment (apply temporary patches, rotate credentials), eradication (remove malware, delete attacker artifacts, rebuild systems), recovery (restore from clean backups, monitor for return).

4. **Post-Incident Activity** — lessons learned meeting, final incident report, evidence retention, metrics, program updates.

Note the structural choice: NIST 800-61r2 *fuses* containment / eradication / recovery into one phase. The next framework un-fuses them.

A NIST draft revision 3 has been circulating in public review since 2024, but as of June 2026 the operative authoritative version most organizations cite is still r2 *(speculative on the r3 status — confirm before citing in a deliverable)*.

### 2.2 SANS PICERL — the practitioner mnemonic

SANS teaches the same lifecycle as a six-letter mnemonic: **PICERL** — **P**reparation, **I**dentification, **C**ontainment, **E**radication, **R**ecovery, **L**essons Learned. The PICERL framing comes from the SANS Incident Handler's Handbook (Kral, 2011, SANS Reading Room — https://www.sans.org/white-papers/33901/) and is the version every SANS-trained handler can recite in their sleep. Practical differences from NIST:

- PICERL splits NIST's "Detection & Analysis" into the dedicated **Identification** stage. The reason is operational: identification asks the binary question "do we have an incident?" before any heavier work begins.
- PICERL keeps Containment, Eradication, Recovery as three explicit stages. Practitioners need to make a discrete handoff at each transition (containment is led by IR; recovery is often led by IT operations).
- PICERL's Lessons Learned is the same as NIST's Post-Incident Activity.

In SANS classroom material PICERL is often drawn as a clock or a loop, with the explicit teaching that you can re-enter any prior stage at any time (typical example: during Eradication you discover a new infected host, which kicks you back to Containment for that host).

Within each PICERL stage the SANS doctrine inserts standard activities. Identification, for example, decomposes into "alert validation," "scope determination," "incident declaration," and "evidence preservation." These sub-activities are where forensics gets dropped in.

### 2.3 ENISA — the European take

**ENISA** (European Union Agency for Cybersecurity) publishes the *Good Practice Guide for Incident Management* (latest substantive revision 2010, with updated training material in 2017 — https://www.enisa.europa.eu/topics/incident-response). It follows a NIST-shaped lifecycle but with two distinct flavors:

- **Heavier weight on coordination across CSIRT teams.** ENISA assumes the responder is a CSIRT (Computer Security Incident Response Team) whose authority extends across a national or sectoral constituency, not a single enterprise. Triage in this world includes deciding *which CSIRT owns the incident*.
- **Explicit attention to information sharing.** ENISA's lifecycle includes formal stages for incident classification using the eCSIRT.net taxonomy (later incorporated into the Reference Security Incident Taxonomy Working Group) and notification obligations under the NIS2 Directive.

For most enterprise DFIR work ENISA and NIST are interchangeable. The ENISA flavor matters when the engagement touches an EU regulator or a national CERT — and as of NIS2 enforcement (Oct 2024) the incident notification timelines (24-hour early warning, 72-hour notification, 1-month final report) shape the speed-of-reporting requirement that the SilentWitness wedge addresses.

### 2.4 ISO/IEC 27035 — the standards body version

**ISO/IEC 27035** is the formal international standard for information security incident management. It comes in multiple parts:
- 27035-1 (2023) — Principles and process
- 27035-2 (2023) — Guidelines to plan and prepare
- 27035-3 (2020) — Guidelines for ICT incident response operations
- 27035-4 (2025) — Coordination *(speculative on the 2025 date — check ISO catalog)*

Its lifecycle: **Plan & Prepare → Detect & Report → Assess & Decide → Respond → Learn**. The "Assess & Decide" stage is a deliberate refactoring — it pulls *decision-making about the incident* out of the response stage and gives it its own phase. This matters because in regulated industries (finance, healthcare, critical infrastructure) the decision to declare an incident has legal and disclosure consequences that warrant a deliberate stage.

ISO 27035 is the framework cited in most ISO 27001 audits, and shows up in contracts as "you will follow an ISO 27035-aligned incident response process."

### 2.5 Comparing them at a glance

| Stage concept | NIST 800-61r2 | SANS PICERL | ENISA | ISO 27035 |
|---|---|---|---|---|
| Get ready | Preparation | Preparation | Preparation | Plan & Prepare |
| Notice it happened | (in) Detection & Analysis | Identification | Detection & Reporting | Detect & Report |
| Decide it's an incident | (in) Detection & Analysis | Identification | Triage & Analysis | Assess & Decide |
| Stop the bleeding | Containment, Eradication, Recovery | Containment | Containment | Respond |
| Clean it up | Containment, Eradication, Recovery | Eradication | Eradication | Respond |
| Get back to normal | Containment, Eradication, Recovery | Recovery | Recovery | Respond |
| Learn from it | Post-Incident Activity | Lessons Learned | Post-incident | Learn |

The takeaway: the frameworks differ in *staging* but agree on *content*. A senior IR consultant moves fluidly between them, picking the framework that matches the audience (NIST for U.S. federal clients, PICERL in conversation with peers, ENISA when the regulator is European, ISO 27035 when the engagement is part of a 27001 audit response).

### 2.6 Where forensics fits in each stage

Forensics is not a separate stage. It is woven through:

- **Preparation** — building forensic readiness: configuring logging (Sysmon, PowerShell ScriptBlockLogging, Windows audit policy), pre-staging acquisition tooling (KAPE, FTK Imager, dd, the SIFT Workstation itself), defining what gets imaged when.
- **Identification / Detection & Analysis** — *initial* forensic triage to confirm whether the alert reflects real attacker activity. Memory snapshot, fast-disk artifacts (Prefetch, Amcache, MFT $J, USN journal), volatile network state. Goal: enough evidence to declare an incident with confidence.
- **Containment** — forensics keeps producing evidence even as you isolate hosts. Critical practice: image *before* you reboot or reset. The act of containing can destroy evidence.
- **Eradication** — forensics produces the IOC and TTP catalog that drives the eradication search ("where else does this attacker have a foothold?"). Without good forensics, eradication is whack-a-mole.
- **Recovery** — forensics validates that the recovered systems are clean (re-imaging, hash comparison against golden images).
- **Lessons Learned / Post-Incident** — the forensic findings are the *substance* of the final incident report and the lessons-learned briefing. This is the second pain point the SilentWitness wedge addresses.

The fact that forensics threads through every stage is why the discipline is named DF*IR* with the I in the middle: forensics is the *evidence layer* that incident response runs on top of.

---

## 3. Triage as a discipline

If you ask ten DFIR consultants what their job is, eight of them will say "triage" before they say "investigation" or "response." Triage is the discipline; investigation is what happens once triage has confirmed scope and direction.

### 3.1 What "triage" actually means in DFIR

The word comes from battlefield medicine and was imported to DFIR explicitly. In medicine, triage is the rapid sort that decides who gets treated first when resources are scarce. In DFIR, triage is the rapid sort that decides what evidence to look at first when time is scarce.

A common practical definition, paraphrased from SANS FOR508 course material: *triage is the focused application of forensic technique to determine the nature, scope, and direction of an incident in the minimum time necessary to make confident decisions.*

Key words:
- **Focused** — not comprehensive. Triage is deliberately not "examine everything."
- **Nature** — what kind of activity is this (commodity malware, targeted intrusion, insider, hardware fault, false positive)?
- **Scope** — how many hosts, accounts, data sets touched? (the blast radius question)
- **Direction** — where to look next? Triage produces the leads that drive the rest of the investigation.
- **Confident decisions** — triage outputs *decisions*, not findings. The decisions are usually "yes, this is real, escalate to full IR" or "no, this is benign, close the ticket" or "unclear, image more and re-triage."

Triage typically runs in the **minutes to hours** timeframe. Full investigation runs in **hours to weeks**. The triage / investigation distinction is what separates the first 90 minutes of an engagement from the rest of it.

### 3.2 The four questions triage answers

A common practitioner framing (consistent across SANS FOR508, the CrowdStrike Services Incident Response field guides, and the Mandiant M-Trends methodology):

1. **Real or false positive?** Does the alert / report / observation correspond to actual malicious activity, or is it benign noise? Roughly half of all SOC escalations to DFIR turn out to be false positives — a misbehaving application, a sysadmin doing maintenance, a vulnerability scanner, expected behavior the SOC didn't recognize. Every minute spent on a false positive is a minute not spent on the real attack happening elsewhere.

2. **Blast radius?** If real, how many systems, accounts, services, and data sets are involved? The blast radius determines containment strategy: a single compromised laptop is isolated and re-imaged; a compromised Tier-0 domain controller triggers a full Active Directory rebuild planning conversation. Practitioners use the term *scope* almost interchangeably with blast radius.

3. **TTPs?** What tactics, techniques, and procedures is the attacker using? The TTPs determine *capability* (commodity criminal vs. state-aligned), *intent* (smash-and-grab ransomware vs. long-dwell espionage), and *next steps* (what artifacts to hunt for on adjacent hosts).

4. **Active or past?** Is the attacker currently on the keyboard, or is this evidence of activity that has since stopped? Active attackers change everything: containment becomes more urgent, OPSEC matters (don't tip off the attacker by triggering their dead-man switches), and the investigation runs *adversarially*.

These four questions are the test of whether a triage step was worthwhile. A senior analyst running a tool asks themselves: *which of the four does this answer?* If the answer is "none," the tool run is not triage.

### 3.3 Kitchen-sink vs hypothesis-driven triage

Two stylistic approaches to triage exist, and the contrast between them is the conceptual core of the SilentWitness wedge.

**Kitchen-sink triage** — also called "shotgun triage" or "collect-then-analyze." The analyst runs every relevant forensic tool against the evidence, dumps all output to disk, and *then* sits down to read what came out. Variants of this are encoded in KAPE targets ("collect everything matching Triage"), in the standard usage of CyLR / Velociraptor's collect-everything offline collectors, and in the way most automation-first tools are designed.

Strengths:
- Predictable runtime — you know how long the collection will take.
- No upfront thinking required from the analyst at collection time — useful when you need a junior responder to acquire while you're still en route.
- Complete archival record — if you missed an artifact later, it's in the dump.

Weaknesses:
- Generates orders of magnitude more output than the analyst will read.
- Produces *no working hypothesis* — the analyst still has to sit down and form one before the output becomes useful.
- Often misses time-critical decisions because by the time everything has been collected and parsed, the incident has moved.
- Has no built-in pivot logic — the collection is the same whether the evidence is pointing at ransomware, BEC, or APT.

**Hypothesis-driven triage** — also called "directed triage" or "lead-driven triage." The analyst forms an explicit hypothesis at the start ("this looks like Qakbot, deployed via thread-hijack phishing, pre-positioning for ransomware"), runs the *specific* tools that would confirm or refute the hypothesis, and pivots when evidence breaks the hypothesis. The mental model is closer to a homicide detective than to a janitor.

Strengths:
- Time-bounded — the analyst stops when the hypothesis is confirmed or refuted, not when "everything" has been collected.
- Produces a narrative as a byproduct — the hypothesis log *is* the case story.
- Sharp pivots — a refuted hypothesis is information, and it actively reshapes the next step.
- Matches how senior analysts actually think (SANS FOR508 explicitly teaches this; David Bianco's threat-hunting essays formalize it).

Weaknesses:
- Requires senior judgment — a junior responder without good priors will form bad hypotheses.
- Risk of confirmation bias — the analyst becomes attached to the hypothesis and ignores disconfirming evidence (see §14).
- Tunnel vision — if the initial hypothesis is in the wrong family, the analyst can chase ghosts for an hour before noticing.
- Harder to automate — "run a hypothesis" is not a single command line.

In SANS doctrine the two approaches are not opposed; they are **layered**. Practical SANS guidance: do enough kitchen-sink work to populate a triage image (KAPE Triage compound target, an FTK Imager memory dump, a `volatility windows.pslist` snapshot), then *immediately* shift to hypothesis-driven analysis of that material. The kitchen-sink work is for *evidence preservation*; the hypothesis-driven work is for *decision-making*. The hour-zero distinction the wedge is built on is that most existing IR automation freezes at the kitchen-sink layer — collection without direction. The senior analyst's value-add is the hypothesis-driven layer on top.

### 3.4 What "good triage" looks like in deliverables

A successful triage round produces a small structured artifact, not a giant log. Common contents:
- **Working hypothesis** — one or two sentences naming the attacker profile, the suspected initial access vector, the apparent objective.
- **Confidence level** — low / medium / high, and *why*.
- **Scope estimate** — N hosts, M accounts, observed dwell time of T days.
- **Recommended containment** — what to isolate, what credentials to rotate, what to *not* touch.
- **Next-step lanes** — explicit list of investigation lanes to open, each with a time budget.
- **What was not checked** — explicit honest list of artifacts not yet examined and why.

That last bullet — *what was not checked* — is the discipline that separates senior triage from confident-sounding overstatement. It is also one of the explicit Rob T. Lee criteria for desirable AI behavior in DFIR ("epistemic honesty," see `stakeholders/12`).

---

## 4. The senior analyst mental model

Junior and senior DFIR analysts have access to the same tools. The difference between them is *not knowing more commands*. It is a small set of disciplined habits about how to think. This section is the load-bearing one for the SilentWitness wedge — the senior habits described here are the behaviors the agent is being asked to embody.

### 4.1 Hypothesis-driven investigation

Senior analysts work in *named hypotheses*. The hypothesis is held explicitly, not implicitly. A common pattern, documented across SANS FOR508 material and in Harlan Carvey's *Windows Forensic Analysis* blog and book series (windowsir.blogspot.com), looks like:

> **H1 (initial):** "User clicked a phishing attachment; macro dropped a downloader; downloader pulled commodity malware (likely Qakbot family based on observed scheduled task name); attacker has not yet pivoted to other hosts."
>
> **Predictions if H1 is true:**
> - Outlook will have recently-opened attachment in `OutlookSecureTempFolder`
> - `winword.exe` parent → child process anomalous (e.g., `winword.exe` → `regsvr32.exe`)
> - Scheduled task created in last N hours with a randomized name
> - Outbound connection to known Qakbot C2 IP range
> - No 4624 logon events on adjacent hosts with this user's credentials
>
> **If any prediction fails:** drop or revise H1.

This explicit framing is the difference between a senior analyst and a junior one running the same commands. The junior runs `volatility windows.pslist` and reads the output. The senior runs `volatility windows.pslist` because H1 predicts a specific parent/child anomaly, and reads the output *looking for that anomaly*.

The hypothesis can be wrong. The discipline is that *it is named*, so when evidence contradicts it the analyst notices.

### 4.2 Multi-artifact corroboration ("don't trust one source")

A senior DFIR rule, drilled in FOR508 and visible in every published DFIR write-up of quality: **a finding requires corroboration from independent artifacts.** One artifact is a *lead*; two or more agreeing artifacts is a *finding*.

Why: every forensic artifact has known failure modes. Prefetch can be disabled by the attacker. The MFT can be timestomped. Event logs can be cleared. The Registry can be tampered with. Memory can be poisoned by rootkits. Each artifact is unreliable in isolation. Confidence comes from the *agreement* of independent artifacts that record the same event through different mechanisms.

A worked example: confirming that a particular executable ran on a host.
- **Prefetch file** (`C:\Windows\Prefetch\PROG.EXE-XXXXXX.pf`) — created by the Windows Cache Manager the first ~10 seconds an EXE runs; records run count, last 8 run times, files referenced. Trustworthy unless Prefetch is disabled (SSDs often disable, ETW can disable, attackers can wipe).
- **Amcache** (`C:\Windows\AppCompat\Programs\Amcache.hve`) — registry hive recording EXE metadata (SHA1, size, path, first execution time inferred). Recorded for compatibility reasons; persists beyond program deletion.
- **UserAssist** (Registry under `NTUSER.DAT\Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist`) — records GUI-launched programs per user.
- **MUICache** — records executable paths interacted with via Explorer.
- **Sysmon Event ID 1** — process creation log entry with full command line, parent process, hashes.
- **Security log 4688** — process creation, if audit policy is on.
- **EDR telemetry** — CrowdStrike, Defender for Endpoint, etc., have their own process-creation records.
- **MFT entry** — proves the file existed on disk at some point.
- **USN journal** — records file creation / modification.
- **ShimCache** (AppCompatCache) — records EXE existence at startup (with controversial semantics — see `domain/02`).

If five of these agree on "PROG.EXE ran at 14:27 UTC under user ADMIN," that is a high-confidence finding. If only one source claims it, that is a *lead* — note it, but don't put it in the report as confirmed without finding corroboration or explaining why corroboration is absent.

### 4.3 Timeline-as-spine

A senior analyst's primary working artifact is almost always **a timeline**. Not a list of findings, not a list of IOCs — a chronological ordering of events. The timeline serves three functions:

1. **Causality** — what triggered what. If a registry persistence key was created at 14:27 and a suspicious process ran at 14:27:03, the timeline makes the *order* of events visible and therefore the *causal chain* inferable.

2. **Scope** — the timeline lets you see lateral movement at a glance. A login event on host A at 13:00 followed by login events on hosts B, C, D in the next ten minutes paints the lateral spread instantly.

3. **Anomaly detection** — gaps and bursts in the timeline are themselves findings. A normal user has events spaced across business hours. An attacker has events at 2 AM, or 200 events in 10 seconds.

Senior analysts build **super-timelines** (a term of art) that merge events from multiple artifacts into one chronologically-sorted stream. The canonical tools are `log2timeline.py` / `psort.py` from the Plaso project (https://plaso.readthedocs.io) which produces a CSV / database that can include MFT, Registry, event logs, browser history, prefetch, LNK files, $UsnJrnl entries, and dozens of other sources in one stream. The Carvey *Investigator's Tools* book and SANS FOR508 both spend significant time on super-timeline construction and analysis. The discipline of treating the timeline as the *primary* analytic artifact (rather than as one of many outputs) is a senior habit.

### 4.4 Known-good baseline subtraction ("know normal")

A foundational FOR508 / FOR500 teaching: **you cannot identify abnormal unless you have internalized normal.** Senior analysts know what a clean Windows 10/11 boot looks like, in detail, so deviations leap out:

- They know `csrss.exe` should run as Session 0 and Session 1 instances, parented by `smss.exe` (which exits immediately after spawning them — so `csrss.exe`'s parent appears as "non-existent process" in tools that resolve PPID).
- They know `lsass.exe` runs once, parented by `wininit.exe`, in `C:\Windows\System32\`. *Any* other `lsass.exe` is malicious by definition (this is the basis of `mimikatz`-impersonation detection).
- They know `svchost.exe` runs many instances, always parented by `services.exe`, always from `C:\Windows\System32\`, always with a `-k` group argument.
- They know `explorer.exe` is parented by `userinit.exe` (which exits immediately, so the parent often shows as gone).
- They know `wmiprvse.exe` is parented by `svchost.exe` (specifically the one hosting DCOM).

These facts are encoded in the SANS "Hunt Evil" / "Find Evil" poster (the famous SANS DFIR poster, currently maintained at https://www.sans.org/posters/hunt-evil/), in Mark Russinovich's *Windows Internals* (Microsoft Press), and in Carvey's blog. Internalizing them is the precondition for noticing the abnormal in §6.

The same baseline discipline applies to:
- Network — known DNS resolvers, known internal subnets, expected outbound destinations.
- Registry — what keys are populated on a clean install vs. what keys an attacker would populate.
- Scheduled Tasks — Windows ships with a known set; anything else is suspicious until justified.
- Services — same.
- Autoruns — Sysinternals' Autoruns has a known clean-system fingerprint; deviations matter.

The teaching point: senior analysts don't memorize "list of evil things." They memorize "what is normal" and notice the negative space.

### 4.5 Threat intel grounding

Senior analysts run their working hypothesis against *current* threat intelligence as a routine step. A given attacker's TTPs are documented:
- **MITRE ATT&CK** (https://attack.mitre.org) — the canonical taxonomy of attacker tactics, techniques, sub-techniques, and procedures, mapped to groups and software. The current version is v15 *(speculative — verify)*. ATT&CK gives every TTP a stable identifier (T1059.001 for "PowerShell," etc.) so analyst notes and detections can reference attacker behavior precisely.
- **Group profiles** — Mandiant (APT1, APT28, APT29, APT41, FIN-series, UNC-series), CrowdStrike (BEAR / PANDA / CHOLLIMA / SPIDER / KITTEN naming), Microsoft (Storm-, Forest, Mint, etc.), Recorded Future, Cisco Talos, Trend Micro, Kaspersky.
- **Commodity malware family profiles** — Qakbot, IcedID, Emotet (post-2021 resurrected), Trickbot, BumbleBee, PikaBot, the modern Initial Access Broker landscape.
- **Ransomware operator profiles** — Conti, LockBit (with the 2024 LockBit takedown), ALPHV/BlackCat, Cl0p, Royal/Blacksuit, Akira, Play.
- **OSINT sources** — DFIR Report (thedfirreport.com), Recorded Future Insikt Group blog, Microsoft Threat Intelligence blog, Mandiant blog, Unit 42 (Palo Alto), Talos blog.

The discipline: when a hypothesis names an attacker profile ("looks like Qakbot deployment"), the senior analyst pulls the most recent published TTPs for that profile and uses them as a *prediction set* to test. If their evidence matches 8 of the 10 documented Qakbot TTPs, confidence goes up; if it matches only 1, the hypothesis is probably wrong.

This is also the discipline that prevents premature attribution (see §14): TTPs first, attribution last, only if TTP signature is distinctive enough.

### 4.6 The pivot decision — when to stop digging in a lane

The hardest skill in senior triage is *knowing when to stop*. Junior analysts dig a lane to the bottom because they're afraid of missing something. Senior analysts stop when the marginal evidence is no longer worth the marginal time.

Practical pivot triggers documented across SANS and practitioner literature:

- **The hypothesis is confirmed beyond reasonable doubt.** Five corroborating artifacts agree. Diminishing returns. Stop and move to the next hypothesis.
- **The hypothesis is decisively refuted.** A predicted artifact is absent in a way that cannot be explained by anti-forensics. Stop and form a new hypothesis.
- **The time budget for this lane is exhausted.** Most engagements have explicit per-lane time budgets (e.g., 30 minutes on "lateral movement check," 45 minutes on "data exfiltration check"). When the timer rings, pivot or formally extend the budget.
- **A higher-priority signal has emerged elsewhere.** While checking one lane an analyst sees evidence pointing at a much larger problem. Pivot.
- **The lane is producing noise without signal.** After several pivots within one lane, no clean leads. Often a sign the original hypothesis is in the wrong family — zoom out, not in.

Junior analysts violate these in characteristic ways: they keep digging because they "haven't found anything yet" (failing to recognize that absence of evidence after sufficient depth *is* evidence), or they keep digging because they're avoiding the harder problem of forming the next hypothesis.

Time budgeting per hypothesis is taught explicitly in SANS courseware as a senior skill. Common heuristic: 60-90 minutes per hypothesis on a triage engagement; if you haven't confirmed or refuted in that window, the hypothesis was probably too vague (split it) or you're in the wrong family (back out).

---

## 5. The order of volatility (RFC 3227)

### 5.1 What it is

**RFC 3227**, *Guidelines for Evidence Collection and Archiving* (Brezinski and Killalea; IETF; February 2002; https://datatracker.ietf.org/doc/html/rfc3227) is a short, durable document that codifies the principle: **collect evidence in decreasing order of volatility**. Volatile evidence (memory, network connections, running process state) disappears unless collected immediately; stable evidence (disk contents, archived logs) can be collected later.

The RFC lists the canonical ordering, paraphrased:

1. CPU registers, CPU cache
2. Routing table, ARP cache, process table, kernel statistics, system memory
3. Temporary file systems
4. Disk
5. Remote logging and monitoring data relevant to the system in question
6. Physical configuration, network topology
7. Archival media

The ordering is now 23 years old but its operational logic is unchanged. Modern DFIR practice still teaches it as gospel.

### 5.2 Why it matters operationally

Every action the responder takes destroys some volatile evidence. The order of volatility tells you *what evidence is destroyed first*, which lets you make rational decisions under time pressure:

- **Pulling the plug** (literal or virtual) is sometimes necessary for containment, but it destroys everything in volatility classes 1–3. If memory acquisition has not already happened, this is a forensic catastrophe.
- **Logging in to the host** to investigate locally destroys evidence in classes 1, 2, 3 (your interactive session writes to memory and temp files). Modern practice: prefer remote acquisition over interactive login, or accept the contamination and document it.
- **Running tools on the host** (e.g., live response with KAPE) destroys some volatile evidence but acquires more than is lost. This is a tradeoff; senior responders make it consciously.
- **Reboot** destroys nearly all classes 1–3.
- **Time itself** is destructive: process tables change, network connections close, temp files get garbage collected. Volatility 3's `windows.netscan` plugin against a memory image taken at 14:00 will only show connections that existed at 14:00.

The operational rule: **memory first, then live volatile state (netstat, process list, logged-on users), then disk image, then logs, then archive material.** On modern engagements the EDR has often already captured most of the volatile telemetry, which inverts the pressure: the responder still wants a memory image but the time-pressure is lower because the EDR is acting as a continuous capture device.

### 5.3 Live response vs. dead-box

Two operating modes flow from the order of volatility:

- **Live response** — capture on a running system. Pros: gets volatile data. Cons: contaminates the system, time-pressured. Tools: KAPE (Kroll Artifact Parser and Extractor — https://www.kroll.com/en/services/cyber-risk/incident-response-litigation-support/kroll-artifact-parser-extractor-kape), Velociraptor (https://docs.velociraptor.app), CyLR (deprecated but still seen), GRR (Google Rapid Response, niche now), Sysinternals' Live KD.

- **Dead-box** (also "post-mortem" or "deadbox") — power off the system, image the disk, examine the image offline. Pros: forensically clean, time-unpressured. Cons: zero volatile data, slow.

Modern DFIR is almost always *both*: capture memory and a volatile-state snapshot live, *then* power off and image the disk. The relative emphasis depends on the case (a possible insider data exfil case might be dead-box-first; a live ransomware attack is live-response-first because the keys might still be in memory).

The order of volatility is also why memory acquisition tooling (FTK Imager, Belkasoft RAM Capturer, WinPmem, AVML for Linux, MacQuisition for macOS) is on every responder's jump bag (§12).

---

## 6. "Finding Evil" / "Hunt Evil" — the SANS doctrine

### 6.1 The poster and what it represents

The SANS Institute publishes a wall poster titled *Hunt Evil: Your Practical Guide to Threat Hunting* (with earlier editions titled *Find Evil — Know Normal*). Current edition lives at https://www.sans.org/posters/hunt-evil/. The poster has become a near-cult object in DFIR — printed and pinned in nearly every SOC and IR shop. It encodes a teaching that is more important than the artifact itself: **the path to hunting attackers is internalizing what normal looks like.** The title of this hackathon ("Find Evil!") is a deliberate reference to it.

The poster's content (across multiple editions, summarized):

- A canonical Windows process tree, with each system process annotated: expected parent, expected path, expected user, expected number of instances, expected command line.
- Sysmon configuration guidance and the most useful Sysmon event IDs.
- A list of common attacker techniques mapped to MITRE ATT&CK.
- A workflow diagram for hunt-driven analysis.
- "Know normal, find evil" — the slogan that captures the teaching.

The poster's most-quoted page is the process tree. It is the canonical reference for the next section.

### 6.2 The Windows boot-and-login process tree (canonical normal)

This is what senior Windows DFIR analysts have memorized. Knowing this is the *precondition* for recognizing the abnormal. Reproduced from Russinovich's *Windows Internals* 7th edition (Microsoft Press, 2017 / 2022 updates) and consistent with the SANS Hunt Evil poster:

- **System Idle Process** (PID 0) — synthetic placeholder, not a real process. No parent.
- **System** (PID 4) — the kernel-mode process hosting Windows kernel threads. Parent: none. Started at boot.
- **Registry** (recent Windows builds, ~Win10 1803+) — hosts the registry hive process. Parent: System.
- **Memory Compression** — parent: System.
- **smss.exe** (Session Manager Subsystem) — Parent: System. Path: `C:\Windows\System32\smss.exe`. Runs as SYSTEM. There is one *master* smss.exe; it spawns per-session smss.exe instances which exit after they finish session init, leaving their children (`csrss.exe`, `winlogon.exe`) parentless from a "ps tree" tool's perspective.
- **csrss.exe** (Client/Server Runtime Subsystem) — Parent: instance of smss.exe (which then exits). One instance per session — typically one for Session 0 (services), one for Session 1 (interactive). Path: `C:\Windows\System32\csrss.exe`. Runs as SYSTEM.
- **wininit.exe** — Parent: instance of smss.exe (which then exits). Session 0. Path: `C:\Windows\System32\wininit.exe`. Runs as SYSTEM.
- **winlogon.exe** — Parent: instance of smss.exe (which exits). Session 1+. Path: `C:\Windows\System32\winlogon.exe`. Runs as SYSTEM.
- **services.exe** — Parent: `wininit.exe`. Path: `C:\Windows\System32\services.exe`. Runs as SYSTEM. The service control manager. Spawns all Windows services.
- **lsass.exe** (Local Security Authority Subsystem Service) — Parent: `wininit.exe`. Path: `C:\Windows\System32\lsass.exe`. Runs as SYSTEM. **Exactly one instance.** Handles authentication. Mimikatz dumps memory from this process.
- **fontdrvhost.exe** — Parent: `wininit.exe` or `winlogon.exe`. One per session.
- **dwm.exe** (Desktop Window Manager) — Parent: `winlogon.exe`. Path: `C:\Windows\System32\dwm.exe`. Runs as DWM-N user.
- **svchost.exe** — Parent: `services.exe`. Path: `C:\Windows\System32\svchost.exe`. Many instances. Each instance runs as the user appropriate to its service group; the `-k` argument identifies the service group it hosts.
- **userinit.exe** — Parent: `winlogon.exe`. Path: `C:\Windows\System32\userinit.exe`. Spawns the user's shell (`explorer.exe`) and *exits*, leaving `explorer.exe` parentless.
- **explorer.exe** — Parent: `userinit.exe` (which exits). Path: `C:\Windows\explorer.exe`. Runs as the interactive user. The shell.
- **RuntimeBroker.exe**, **ApplicationFrameHost.exe**, **SearchHost.exe**, **StartMenuExperienceHost.exe**, etc. — Parent: `svchost.exe` (hosting DCOM) or `services.exe`. UWP runtime hosts.

Critical asymmetries that catch attackers:
- `lsass.exe` runs as a child of `wininit.exe`. If you see `lsass.exe` running as a child of `explorer.exe`, that is malicious.
- `svchost.exe` always runs from `C:\Windows\System32\` with a `-k` argument. A `svchost.exe` running from `C:\Users\` or with no `-k` argument is malicious.
- `csrss.exe` only ever runs from `C:\Windows\System32\`. Same for the other System32 processes.
- Process **count** matters: exactly one `lsass.exe`, exactly one `services.exe`, exactly one `wininit.exe`. Multiples are red flags.
- **Process spelling** matters: `scvhost.exe` (transposed letters), `Isass.exe` (capital i instead of lowercase L), `1sass.exe`, `csrss.exe ` (trailing space) are common attacker tricks.

### 6.3 What "Finding Evil" looks like in practice

Given the process tree above, the senior analyst's first pass on a memory image or process snapshot is to verify each system process matches expected parent, path, user, count, and command line. Any deviation is a finding-or-noted-anomaly. Volatility 3 plugins (`windows.pstree`, `windows.malfind`, `windows.psscan`, `windows.cmdline`) and Sysinternals' Process Explorer with VirusTotal lookups are the standard tools for this pass.

A common workflow:
1. Pull memory image with FTK Imager / WinPmem.
2. Run `volatility windows.pstree` and `volatility windows.pslist` — compare to the canonical tree mentally.
3. Run `volatility windows.malfind` to highlight injected code regions.
4. Run `volatility windows.cmdline` and look at command lines for known LOLBins (see §12).
5. Cross-reference with EDR process telemetry if available.

This Wave 1 process-tree analysis is often where the working hypothesis is first formed.

### 6.4 Beyond processes — the other "normals" worth knowing

The "know normal, find evil" doctrine extends to:
- **Network normal**: outbound destinations the org actually uses; expected ports; expected DNS resolvers. Modern attackers blend by using major cloud-provider IPs (AWS, Azure, GCP) for C2 — "normal" is harder to define, but the senior analyst still knows what *their environment* normally talks to.
- **Service normal**: the list of Windows services on a clean install of build X; anything else is at least worth noting.
- **Scheduled task normal**: Windows ships with a known set; attackers love the Scheduled Tasks subsystem (`schtasks.exe`, COM-based task creation) for persistence (T1053 in ATT&CK).
- **Persistence-mechanism normal**: the canonical list of "places a Windows program can be made to auto-run" is shown in Sysinternals' Autoruns. A senior analyst's baseline includes what Autoruns produces on a clean machine.
- **Account normal**: which accounts log in to which systems at which times. Anomalies (a service account doing interactive logon at 3 AM) leap out *only* if you know what normal account usage looks like.

This is why "Know normal" precedes "Find evil" in the slogan. Detection is fundamentally a *baseline comparison* operation, and the baseline lives in the senior analyst's head as much as it lives in the SIEM.

---

## 7. The Pyramid of Pain (David Bianco)

### 7.1 The model

**The Pyramid of Pain** is a model published by David Bianco on his Enterprise Detection & Response blog (detect-respond.blogspot.com, January 2013, with later updates; canonical post: http://detect-respond.blogspot.com/2013/03/the-pyramid-of-pain.html). It has become the most-cited diagram in threat hunting and detection engineering.

The pyramid orders types of indicators by how *painful it is for the attacker if the defender denies that indicator*. From bottom (trivial) to top (excruciating):

1. **Hash values** — MD5, SHA-1, SHA-256 of attacker tooling. *Trivial* for attacker to change (recompile, repack, single byte modification).
2. **IP addresses** — C2 servers, exfiltration destinations. *Easy* for attacker to change (spin up new VPS, rotate cloud IPs).
3. **Domain names** — C2 domains, phishing domains. *Simple* — attackers use DGAs, fast-flux DNS, or just register new domains.
4. **Network/host artifacts** — user agents, named pipes, registry keys, service names, file paths. *Annoying* — these require the attacker to alter their tooling.
5. **Tools** — actual binaries / scripts the attacker uses. *Challenging* — denying a tool forces the attacker to rebuild or find a replacement.
6. **TTPs (Tactics, Techniques, Procedures)** — the patterns of attacker behavior. *Tough!* — denying these forces the attacker to fundamentally change how they operate.

### 7.2 The teaching

The model's pedagogical point: blue teams who focus only on the bottom of the pyramid (hashes, IPs, domains) play perpetual whack-a-mole. Every time they block an IOC, the attacker rotates and continues, with minimal effort cost. Blue teams who detect at the top of the pyramid (TTPs) impose real cost on the attacker — they have to retrain, re-tool, change their playbook.

For DFIR triage this matters in two ways:

- **What to extract from a case.** A senior analyst extracts not just hashes / IPs / domains (low pyramid) but *behavioral patterns*: "the attacker used `wmic` for remote execution," "the attacker used `vssadmin delete shadows /all /quiet` before encryption," "the attacker created scheduled tasks named `\\Microsoft\\Windows\\Update\\NewMission` for persistence." These are the TTPs that survive across cases — the attacker rotates IPs between victims, but the *technique* often persists across years and groups.

- **How to communicate findings.** A report that says "we blocked these 47 hashes and these 12 IPs" is low pyramid. A report that says "the attacker exhibits this behavioral pattern, mapped to ATT&CK techniques T1059.001, T1003.001, T1071.001, T1486; blocking these techniques requires the following control changes…" is high pyramid. Senior IR consultants write the latter.

### 7.3 Implications for the wedge

The Pyramid of Pain matters for SilentWitness because the *reporting* gap the wedge addresses involves extracting and presenting high-pyramid findings. A kitchen-sink report dumps IOCs (low pyramid); a senior-quality report describes attacker behavior in MITRE ATT&CK terms (high pyramid) and explains what defensive change would impose cost. The judges who care about defensible findings (Steve Anson, Cheri Carr, Ovie Carroll) care about pyramid-top output. The judge who cares about senior-analyst sequencing (Rob T. Lee) cares about pyramid-top reasoning during the investigation, not just at the end.

---

## 8. Hypothesis-driven investigation in practice

This section unpacks how senior analysts actually form, test, and pivot off hypotheses. Material drawn from SANS FOR508 instructor notes, Harlan Carvey's blog (windowsir.blogspot.com), Andrew Case's DFIR Summit talks, Recorded Future's threat hunting playbooks, and the DFIR Report's case writeups (thedfirreport.com).

### 8.1 How hypotheses get formed

A hypothesis is a *named, falsifiable claim about what happened.* "There was an incident" is not a hypothesis. "An attacker gained initial access via Outlook phishing, executed Qakbot on host WS-014, and pivoted via RDP to host WS-022 to enumerate the file server" is a hypothesis.

Common triggers for hypothesis formation:
- **The alert itself.** SOC says "EDR flagged `regsvr32.exe` spawning from `outlook.exe` on WS-014." The alert names a TTP (T1218.010 + macro execution chain), which lets the analyst form an initial family hypothesis: phishing-into-execution.
- **The first artifact glance.** Memory pstree shows `lsass.exe` running as a child of `explorer.exe`. That single fact pulls the hypothesis toward "credential dumping in progress," because the senior analyst knows *only* malicious code produces that parent/child relationship.
- **Threat intel match.** The C2 IP from the alert appears in a Mandiant or CrowdStrike report from last week as a known Qakbot infrastructure node. The hypothesis is now Qakbot-specific.
- **Pattern recognition from prior cases.** Senior analysts have a mental library of "what cases look like." A specific combination of file paths and process names instantly cues "this is the Akira ransomware playbook."

The senior habit: *write the hypothesis down* before running tools to confirm it. Common formats:
- One-line working hypothesis at the top of the case notes.
- A list of "predictions if true" that the next tool runs will test.
- A list of "predictions if false" — counter-evidence to actively look for.

### 8.2 What triggers a pivot

Pivots are the second-most important moment in an investigation, after hypothesis formation. A pivot is a *change in working hypothesis* that follows from new evidence. Senior analysts pivot:

- **When a prediction fails decisively.** Hypothesis predicted a Qakbot scheduled task; the scheduled task list shows no Qakbot-style task; corroborating artifacts (Amcache, Prefetch) show no Qakbot binary; pivot off Qakbot.
- **When a stronger hypothesis emerges.** While checking lateral movement, the analyst sees evidence of a specific tool used by a specific group, which makes that group the new prime candidate.
- **When the scope reframes.** Initial hypothesis was "single host compromise." Network logs show 14 hosts beaconing to the same C2. The hypothesis pivots to "enterprise-wide intrusion, scope unknown."
- **When the timeline reframes.** Initial hypothesis was "intrusion started 3 days ago." A USN journal entry shows the malware was created 47 days ago. Dwell time is much longer than thought; pivot from "short-dwell ransomware" to "long-dwell access broker who recently sold to ransomware."

Pivots are *recorded explicitly*. The case notes show H1, then H1 refuted because of X, then H2 formed because of Y. The pivot record is what makes the investigation defensible afterward — and the artifact that allows the analyst (or a reviewer) to spot confirmation bias retroactively.

### 8.3 Time-budgeting per hypothesis

A SANS-taught discipline: assign a time budget to each hypothesis before starting work on it. Common per-hypothesis budgets on a triage engagement:
- Initial scoping hypothesis: 30-60 minutes.
- Initial-access hypothesis: 60 minutes.
- Persistence hypothesis: 30 minutes per identified mechanism.
- Lateral movement hypothesis: 60-90 minutes per traversal path.
- Exfiltration hypothesis: 90 minutes (this is often the hardest to confirm definitively).
- Attribution hypothesis (if any): 30 minutes max — attribution is intentionally time-limited because it slides easily into speculation.

The budget is a *trigger to pivot or escalate*, not a hard stop. When the budget rings without confirmation, the analyst makes an explicit choice: extend the budget (and document why), pivot to a different hypothesis, or stop and accept "unknown." The discipline is the explicit choice.

### 8.4 Dead-end discipline

A *dead end* — a hypothesis run to completion with no confirmation — is not a failure. It is a *finding*. Senior analysts record dead ends with the same rigor as confirmed findings, because:

- A future reviewer needs to know the analyst *looked* at that hypothesis.
- The next analyst on the case can skip re-checking the same thing.
- The dead-end record is what allows the investigation to honestly say "we did not see evidence of X" rather than the weaker "we did not look for X."

This dead-end discipline is also a Rob T. Lee criterion for desirable AI behavior — being able to say "I did not check Y" without making something up is part of "epistemic honesty." See `stakeholders/12` for the source statements.

### 8.5 The hypothesis log as the case spine

A well-run engagement produces a hypothesis log that reads roughly like:

> **H1 (10:14 UTC):** Phishing-induced commodity infection, likely Qakbot family, single host.
> Predicted: macro chain in Outlook temp; scheduled task with random name; outbound to Qakbot C2 IP range.
> Tested via: memory pstree, Amcache, schtasks, Sysmon EID 3.
> **H1 refuted (10:42 UTC)** — Amcache shows no Qakbot binary; Sysmon shows outbound to a non-Qakbot AS; macro chain absent (no Word/Excel activity in $UsnJrnl).
>
> **H2 (10:42 UTC):** Initial access via exposed RDP, brute-forced credentials, hands-on-keyboard activity.
> Predicted: 4625 brute-force pattern; 4624 type 10 logon from external IP; subsequent interactive console activity.
> Tested via: Security event log, ShellBags, MountPoints2, Jump Lists.
> **H2 confirmed (11:18 UTC)** — 247 failed 4625 events from 91.x.x.x in a 4-minute window followed by 4624 type 10 success from same IP; ShellBags shows interactive folder browsing in `\\fileserver\hr\compensation` starting 11:24.
>
> **H3 (11:18 UTC):** Active hands-on-keyboard attacker is enumerating file shares for data theft prior to ransomware deployment.
> …

This is the *spine* of the investigation. Tools are run in service of it. Findings hang off it. The final report is constructed from it. The wedge for SilentWitness is, in part, that this spine is currently *implicit in the analyst's head and notebook* and is the artifact that, made explicit and machine-readable, would close the senior-analyst sequencing gap that Rob T. Lee names as the desired AI behavior.

---

## 9. Multi-artifact corroboration patterns

This section catalogues the multi-source patterns senior analysts use to confirm specific kinds of activity. It is the reference list for "what does it take to be confident X happened?" Sources: SANS FOR508 instructor material, Carvey *Investigating Windows Systems* (Academic Press 2018), the DFIR Report's per-case writeups, and Volatility documentation.

### 9.1 "Process executed on host"

To confirm a specific executable ran:
- **Prefetch** (`%SystemRoot%\Prefetch\<name>-<hash>.pf`) — created on first execution of an EXE that is not on the noindex list. Records full run history of last 8 runs. Trustworthy if present.
- **Amcache.hve** registry hive — records EXE metadata (SHA1, size, path, language, install date, last modified). Persists across program deletion.
- **ShimCache / AppCompatCache** (Registry, `SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache`) — records EXE existence at boot/shutdown with last-modified timestamp. *Controversial semantics* — see `domain/02` for the long-running ShimCache analysis debate.
- **UserAssist** (NTUSER.DAT) — records GUI-launched programs per user, with ROT13-encoded keys.
- **MUICache** — records EXE paths interacted with via Explorer.
- **Sysmon Event ID 1** (if Sysmon deployed) — full process creation record with parent, command line, file hashes, user.
- **Security log 4688** (if audit policy is on, which is the rare default-on case) — process creation.
- **EDR process telemetry** — CrowdStrike, Defender, SentinelOne all log this.
- **MFT** — proves the file existed on disk; does *not* prove execution.
- **USN journal ($UsnJrnl:$J)** — records file creation, modification, deletion within its retention window.
- **BAM/DAM (Background Activity Moderator)** — registry, records app activity timestamps.

Senior confidence threshold: **Prefetch + Amcache + (Sysmon 1 OR Security 4688)** agreeing = high confidence. Add UserAssist for interactive launches. Disagreements → investigate the disagreement, often it's evidence of tampering.

### 9.2 "C2 communication established"

To confirm command-and-control traffic:
- **Volatility `windows.netscan`** (against memory image) — shows TCP/UDP connections present in memory at acquisition time, including process owner.
- **Sysmon Event ID 3** — network connection initiated, with process and destination.
- **Zeek `conn.log`** (if network capture available) — full bidirectional flow record with bytes, duration, history.
- **Firewall logs** — if egress firewall logs accepts and denies.
- **EDR network telemetry** — process-attributed network connections.
- **DNS logs** — queries that preceded the connection.
- **NetFlow / IPFIX** — at the edge router.
- **PCAP** — gold standard if available, definitive evidence of content.
- **Proxy logs** — HTTP/S transactions if proxied.

Senior confidence threshold: at least two of {Sysmon EID 3, Zeek conn.log, EDR netconn} attributing the connection to a specific process + DNS log of the prior resolution + the destination matching threat intel. **Beaconing patterns** (regular interval, low jitter, small request / large response asymmetry) detected in flow data is itself a high-pyramid TTP signal.

### 9.3 "Lateral movement via RDP"

To confirm an RDP-based lateral hop:
- **Source host Security log 4624** (logon) and **4648** (explicit credential use).
- **Destination host Security log 4624 Type 10** (interactive remote logon).
- **Destination host TerminalServices-RemoteConnectionManager Operational log 1149** — user authentication succeeded.
- **Destination host TerminalServices-LocalSessionManager Operational logs 21, 22, 25** — session connect, shell start, session reconnect.
- **Source host TerminalServices-RDPClient Operational log 1024 / 1102** — destination computer name connected to.
- **Destination host ShellBags** (NTUSER.DAT / UsrClass.dat) — folders browsed during the session.
- **Destination host Jump Lists** — files opened via taskbar.
- **Destination host Recent Items** (`%AppData%\Roaming\Microsoft\Windows\Recent`) — LNK files created by Explorer.
- **Network: Zeek `conn.log` on tcp/3389** between hosts.

Senior confidence threshold: source 4624 + destination 4624 type 10 + destination 1149 + destination ShellBags showing in-session browsing = lateral movement confirmed at high confidence. The destination ShellBags element is often the smoking gun because it proves the attacker did *something* in the session, not just authenticated.

### 9.4 "PowerShell-based execution"

To confirm and reconstruct PowerShell-based attacker activity:
- **Microsoft-Windows-PowerShell/Operational log Event ID 4104** — script block logging (if ScriptBlockLogging enabled — best practice but not default-on).
- **Microsoft-Windows-PowerShell/Operational Event ID 4103** — module logging.
- **Microsoft-Windows-PowerShell/Operational Event ID 400** — engine start.
- **Microsoft-Windows-PowerShell/Operational Event ID 600** — provider start (often used by attackers loading offensive modules).
- **PowerShell transcripts** — if transcription is enabled, full session history written to disk.
- **PSReadLine `ConsoleHost_history.txt`** (`%AppData%\Microsoft\Windows\PowerShell\PSReadLine\`) — interactive command history; persists between sessions; *attackers often forget to clear this*.
- **Sysmon EID 1** — captures invocation command line.
- **EDR script content capture** — modern EDRs capture script bodies.
- **AMSI logs** — Antimalware Scan Interface entries for blocked / scanned content.

Senior confidence threshold: 4104 entries + Sysmon EID 1 invocation + (EDR script body OR transcript) = full reconstruction of PowerShell execution. The `ConsoleHost_history.txt` file is the dark horse — sometimes the entire attacker interactive session is sitting there in plaintext because they used `cmd.exe` for some commands and PowerShell for others without disabling history.

### 9.5 "Credential theft via LSASS"

To confirm credential dumping from LSASS:
- **Sysmon Event ID 10** — process accessed, especially target image `lsass.exe` with specific granted access rights (PROCESS_VM_READ = 0x10, PROCESS_QUERY_INFORMATION = 0x400 — Mimikatz pattern is 0x1010 or 0x1410).
- **Windows Defender / EDR detection** — most EDRs detect LSASS reads heuristically.
- **MiniDump artifacts** — `lsass.DMP` files on disk indicate `procdump`-style dumping.
- **Sysmon Event ID 11** — file creation, looking for `.dmp` extensions in suspect directories.
- **Volatility `windows.modules`** — looking for injected modules in LSASS.
- **Security log 4688** — process creation, looking for `procdump.exe`, `comsvcs.dll`-based dumping (`rundll32 comsvcs.dll MiniDump`), or known offensive tools.

Senior confidence threshold: Sysmon EID 10 with Mimikatz access mask + accompanying suspicious process = high confidence credential theft. The `comsvcs.dll` MiniDump LOLBAS technique (T1003.001) is the modern Mimikatz alternative and is detected through 4688/Sysmon command-line analysis.

### 9.6 "Data exfiltration"

To confirm data was exfiltrated:
- **Network volume signatures** — Zeek `conn.log` showing outbound flow with bytes-out significantly exceeding bytes-in.
- **Proxy logs** — large POSTs / PUTs to external destinations.
- **DNS logs** — for DNS-tunneled exfil, long base32/64 encoded subdomains in query patterns.
- **Cloud storage access** — Office 365 / Google Workspace / cloud-provider logs showing mass downloads or uploads to attacker-controlled accounts.
- **Filesystem timestamps** — read-access timestamps on large files immediately preceding an outbound flow.
- **`robocopy` / `7z` / `rar` / `WinRAR` execution** — staging archive creation, captured in Sysmon and Prefetch.
- **`MEGAcmd`, `rclone`, `MegaSync`, `bitstaging`, `RcloneCLI`** — common exfil tooling.
- **Browser uploads** — browser history and POST data if captured.

Senior confidence threshold: staging tool execution + archive creation in known staging directory + corresponding outbound flow with matching byte volume = exfil confirmed. Exfil is one of the hardest things to prove definitively because the data leaves the environment; absence of network capture sets a confidence ceiling.

### 9.7 "Persistence established"

To confirm a persistence mechanism:
- **Autoruns** — Sysinternals Autoruns enumerates every Windows auto-start location. The output is large; senior analysts compare against a known-clean baseline.
- **Scheduled Tasks** — `\Windows\System32\Tasks\` directory + Registry `Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache`.
- **Services** — Registry `SYSTEM\CurrentControlSet\Services`.
- **Run / RunOnce keys** — Registry `Software\Microsoft\Windows\CurrentVersion\Run` and `RunOnce`, both per-machine and per-user.
- **Startup folders** — `%AppData%\Microsoft\Windows\Start Menu\Programs\Startup`, `%ProgramData%\Microsoft\Windows\Start Menu\Programs\Startup`.
- **Image File Execution Options** (IFEO) — `SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options` — Debugger value hijacks process execution.
- **WMI Event Subscription** — root\subscription namespace, especially `__EventFilter`, `__EventConsumer`, `__FilterToConsumerBinding`.
- **COM hijacking** — Registry CLSID entries with attacker-controlled paths in `LocalServer32` / `InprocServer32`.
- **AppInit_DLLs** — legacy, but still seen.
- **Boot Execute** — `Session Manager\BootExecute`.
- **Winlogon helpers** — `Notify`, `Shell`, `Userinit` registry values.
- **Office Add-ins** — for persistence inside Outlook / Word.

Senior confidence threshold: discovery of the persistence artifact + corroboration that it actually fires (next-boot evidence in Prefetch, Sysmon, event logs) = confirmed. A persistence artifact that has never triggered is still a finding but is operationally less urgent than one that has.

### 9.8 The general principle: disagreements ARE findings

When two artifacts that should agree don't, *that disagreement is itself a finding worth pursuing*. Examples:

- **Prefetch claims a program ran but the file is missing from disk** → program was deleted after running. Was it deleted by user, by the program self-deleting, or by anti-forensic action?
- **Amcache shows an EXE with SHA1 X, but the EXE on disk now has SHA1 Y** → the file was replaced. When? Why? Who?
- **Security log shows a 4624 logon but no corresponding 4634 logoff for hours** → session is still active, or logoff event was cleared.
- **ShimCache shows an EXE that has no Prefetch and no Amcache entry** → ShimCache fires for "seen at boot/scan" without execution, which is consistent with detection but not with execution. The disagreement is normal here, and knowing it is normal is itself part of the senior baseline.
- **The MFT shows a file created at time T but the $UsnJrnl shows no creation event at T** → either USN journal was truncated (very common) or the MFT timestamp was tampered with (timestomping).

A senior analyst chases these disagreements; a junior records them as anomalies and moves on. The chase often reveals anti-forensics, which is a high-pyramid finding (it implies attacker sophistication).

---

## 10. Chain of custody (operational view)

> This section covers the *operational* practice of chain of custody — what an analyst does to maintain it during an engagement. The *legal* and *court-admissibility* dimension (FRE 901, FRE 707, Daubert, Frye, the 2024 FRE 707 AI-evidence amendment, etc.) is covered in `stakeholders/12-judges-curriculum-and-legal-landscape.md`. The two are related but separable; this file is the technical/operational view.

### 10.1 What chain of custody means at the bench

**Chain of custody** (CoC) is the documented record of every person who has handled a piece of evidence, every action taken on it, and every transfer between custodians, from the moment of acquisition through the moment of presentation. The purpose is to allow a reviewer (peer, court, regulator) to verify that the evidence has not been substituted, altered, contaminated, or fabricated.

At the bench, CoC manifests as:
- **Acquisition documentation** — when, where, by whom, using what tool (with version), what was the source, what is the resulting hash.
- **Transfer documentation** — who moved the evidence container from where to where, when, signed by both parties.
- **Examination documentation** — every analyst who examined the evidence, when, what tools were used, what (read-only) operations were performed.
- **Hash verification at every transfer** — proof that the evidence is bit-identical to what was acquired.

The discipline is universal across DFIR. Even in cases that will never see a courtroom (internal investigations, regulatory disclosures, insurance claims), the CoC discipline is maintained because (a) the case might unexpectedly become legal later, and (b) it is the same discipline that produces *defensible findings* — findings that a peer reviewer or an opposing analyst cannot poke holes in. Steve Anson's Valhuntir was explicitly built around this discipline (see `competitive/11`).

### 10.2 What breaks CoC

CoC breaks in characteristic ways:

- **Acquisition without hashing.** A disk image acquired without recording the MD5 / SHA-1 / SHA-256 of the source and the image cannot be proven later to be unaltered. Even modern responders have re-acquired images they forgot to hash.

- **Modification of source evidence.** Writing to the original media — even accidentally, via an OS auto-mount on a host system, or via a forensic tool that wasn't run with `--read-only` — breaks CoC. The standard mitigation is **write-blocking**, either hardware (Tableau, WiebeTech, CRU) or software (mounting read-only, using `dd if=/dev/sdX of=image.dd` from a forensic boot environment).

- **Acquisition by an untrained party.** A sysadmin who pulled the disk and "took a quick look" before handing it over has likely contaminated mount timestamps, file access times, and possibly the MFT. The contamination is documentable and the case continues but the contamination *cost* must be recorded.

- **Untracked transfers.** Disk shipped via courier without signed handoff. Image dropped on a shared drive accessible to people not on the case team. Both break CoC.

- **Examination on the original.** The original (or a verified clone) is sealed; analysis happens on a *working copy*. If anyone analyzes the original media directly, CoC is contaminated.

- **Tool-introduced changes.** Some tools (older versions of certain commercial suites) silently wrote metadata. Modern forensic tools document their read-only behavior; the responder still verifies.

- **Time gaps.** Periods during which the evidence is unaccounted for. Even if nothing happened, the absence of a record is a CoC defect.

### 10.3 Hash verification

The bedrock CoC operation is **cryptographic hashing**. Practical conventions:

- **At acquisition** — compute and record the hash of the source media (or, if acquiring a logical image, the hash of the source filesystem state). Modern practice uses both MD5 and SHA-1 (MD5 for historical compatibility / older tool interop, SHA-1 for stronger collision resistance). Some shops add SHA-256. The hashes are recorded in the acquisition log and on the evidence container label.

- **At every transfer** — re-compute the hash on receipt, compare to the recorded value, sign the receipt with the result.

- **At every examination start** — re-compute the hash on the working copy, compare to recorded value, log the verification.

- **At final presentation** — re-compute and demonstrate equality with the acquisition hash.

A hash mismatch at any verification step is a case-altering event. It does not necessarily mean tampering — it can mean bit rot, media failure, or tool error — but it *does* mean the evidence's current state cannot be safely claimed to be identical to the acquired state, and the report must reflect that.

Modern practice has shifted toward SHA-256 as the primary hash for new acquisitions, with MD5/SHA-1 kept for legacy tool compatibility. The shift is driven by the collision attacks against MD5 (Wang et al., 2004; demonstrated in practice for years) and the SHAttered attack against SHA-1 (Stevens et al., 2017). For non-adversarial evidence integrity (the typical forensic use case) MD5 and SHA-1 remain practically adequate; for adversarial scenarios SHA-256 is the floor. *Speculative on whether SHA-256 is now mandated by FRE-aligned best practice — confirm via current ISO 27037 / NIST guidance before claiming.*

### 10.4 Write-blocking

**Write-blocking** is the mechanism that prevents any change to the source media during acquisition or examination. Two modes:

- **Hardware write-blockers** — physical devices inserted between the source media (disk, USB) and the acquisition host. The blocker passes read commands through and blocks all write commands. Tableau (now part of Opentext), WiebeTech (CRU), and Atola are the canonical brands. Hardware write-blockers are the gold standard because they cannot be bypassed by host OS behavior.

- **Software write-blockers** — OS / driver mechanisms that enforce read-only access. On Linux, mounting with `-o ro` or using a forensic boot environment (CAINE, DEFT, SIFT itself when properly configured) provides this. On Windows, registry settings can prevent USB writes; commercial tools (Tableau Imager, FTK Imager) provide software write-blocking. Software write-blockers are adequate for many cases but are bypassable by misconfiguration; hardware is preferred when the case might be court-bound.

The write-blocking discipline is the reason senior analysts almost never examine evidence on the host that acquired it — they image, hash, transfer the hash-verified image to an examination workstation, and work on a working copy of that image.

### 10.5 The CoC artifact

Operationally, a CoC artifact is a document (paper, digital, or both) that includes at minimum:

- Case identifier.
- Evidence identifier (per item).
- Description (make, model, serial, capacity for media; file path / hash for digital evidence).
- Acquisition record (date, time, location, person, tool, tool version, acquisition method, hashes).
- Custody log — table of transfers with date/time, from/to, signatures, purpose.
- Examination log — table of examinations with date/time, examiner, purpose, hashes verified.

Many shops maintain this in a structured form: paper for transfers, ticketing-system or case-management-tool entries for examinations, with the case management tool enforcing required fields. SIFT-using consultants often supplement with a `chain-of-custody.txt` in the case directory.

The CoC artifact is also a *byproduct of a well-instrumented DFIR pipeline*: every tool execution logged with parameters and hashes is, effectively, an automated examination log entry. This is one of the substantive reasons the SilentWitness wedge ("every claim verifiably linked to the tool execution") maps cleanly to defensible practice — though, per the wedge's deliberate framing, the verifiability is sold to the user as *engineering quality* rather than *court admissibility* (see `stakeholders/12` for why the latter framing is risky with the head judge).

---

## 11. The DFIR analyst's day (sketch)

The full version of this section is in `user/09-ir-consultant-reality.md`. The sketch here is just enough to ground the rest of this file.

A typical day for a senior IR consultant at a midsize firm (drawn from public practitioner accounts on the SANS DFIR Summit channel, the DFIR Diva blog (dfirdiva.com), the Hexordia blog, the 13Cubed YouTube channel, and the Belkasoft / Magnet Forensics user community):

- **Morning** — review overnight cases, check on retainer clients, respond to overnight alerts. Most days start in a known case; some days start with a 3 AM phone call that becomes the only thing the consultant does for the next 12-72 hours.
- **Case work** — alternates between live engagement work (containment guidance to client, evidence acquisition, triage) and report writing on previous cases. A senior consultant typically has 2-4 active cases at any time, with one being "hot" and the others in report or follow-up phases.
- **Tool work** — running KAPE / Velociraptor / Volatility / Plaso / EZ Tools / Sysinternals utilities. Most consultants describe themselves as spending more time running tools than thinking with them. Rob T. Lee's "command-line stenographer" line names this experience.
- **Writing** — case notes, interim status to client (often required hourly during active incidents), final report drafting. The report is what the client paid for; it is also what gets cross-examined if the case becomes legal.
- **Interruptions** — clients, other consultants, sales calls, training, internal reviews. The senior consultant is rarely uninterrupted for more than 90 minutes.

Three observations that matter for the wedge:

1. **The consultant's billable time is dominated by tool-running and report-writing.** Both are mechanical compared to the analytical thinking the consultant is actually paid for. This is the *gap* the SilentWitness wedge addresses.

2. **Reports are written *after* the investigation, in a second pass.** The consultant takes notes during the investigation, then sits down for 2-3 hours to convert notes into a structured report. This second pass is universally complained about and universally tolerated as "how the work is done." Producing the report *during* the investigation (the SilentWitness wedge framing) is the novel claim.

3. **Senior consultants explicitly value *defensibility* over *completeness*.** The report has to survive cross-examination by a peer or by counsel. This is why findings are required to corroborate, why CoC is maintained, and why "what I did not check" is honestly listed. Defensibility is also what distinguishes the judge-aligned framing of the wedge ("every claim verifiably linked to tool execution") from the saturated anti-hallucination framing ("the agent does not hallucinate").

For the full version — engagement archetypes, report anatomy with real section headings, the 3 AM call vignette — see `user/09`.

---

## 12. DFIR vocabulary glossary

Terms an outsider would not know, glossed in plain English. Definitions are practitioner-conventional, drawn from SANS course glossaries, NIST publications (notably the NIST glossary at csrc.nist.gov/glossary), and consistent usage across the DFIR Report, Mandiant M-Trends, and Carvey's books.

- **Artifact** — a discrete piece of digital evidence that comes from a known system mechanism. The Windows Prefetch directory is an *artifact source*; an individual `.pf` file is an *artifact*. Forensic tools "parse artifacts." The vocabulary is borrowed from archaeology and used consistently.

- **Evidence** — anything that contributes to a finding. Broader than "artifact": evidence includes interview statements, configuration documents, vendor reports. In a legal context, evidence is what is admissible; in a DFIR context, evidence is what supports a finding.

- **Finding** — a substantive conclusion about what happened, supported by evidence. "The attacker exfiltrated 14 GB of data via SFTP between 02:14 and 04:02 UTC on 2026-05-30" is a finding. Findings populate the report.

- **Observation** — a fact about the evidence, neutral as to interpretation. "Sysmon EID 3 records 247 outbound connections to 91.123.45.67 between 02:14 and 04:02" is an observation. Multiple observations support a finding.

- **Interpretation** — the analytical claim that turns observations into a finding. The interpretation is the part that can be wrong even when the observations are right. Senior reporting separates observation from interpretation explicitly.

- **Indicator** — a fact that, if observed in another environment, signals the same activity. Indicators are *exportable* — they leave the case and become reusable threat intelligence.

- **IOC (Indicator of Compromise)** — a low-pyramid indicator: hash, IP, domain, URL, mutex name, file path. Most threat-intel feeds traffic in IOCs. IOCs are perishable (attackers rotate them) and partial (matching an IOC tells you the file passed through but not what it did).

- **IOA (Indicator of Attack)** — coined by CrowdStrike. A *behavioral* indicator: "a child process of a Microsoft Office app spawning powershell.exe with an encoded command and outbound network connection" is an IOA. IOAs are mid-pyramid; they describe behavior rather than artifacts. The IOA / IOC distinction is now used widely.

- **TTP (Tactics, Techniques, Procedures)** — the high-pyramid layer. Tactics are *what the attacker is trying to do* (initial access, execution, persistence — ATT&CK's columns). Techniques are *how they do it* (PowerShell, scheduled task — ATT&CK's cells). Procedures are *how they do it in this specific case* — the actual commands, paths, names. The MITRE ATT&CK framework is the canonical TTP taxonomy.

- **Victimology** — the study of who is being attacked and why. Includes geographic, sectoral, organizational characteristics of the victim that match an attacker's targeting pattern. Threat intel groups maintain victimology profiles for tracked actors.

- **Attribution** — the claim that a specific actor (named group, named individual, named state) is responsible. Strongly *not* the first thing analysts do; attribution is one of the *last* things done in a case, with explicit confidence levels, and it is the most over-claimed part of the discipline. "Looks like APT29" is a hypothesis, not an attribution.

- **Dwell time** — the elapsed time between initial compromise and detection. The Mandiant M-Trends annual report tracks the median industry dwell time year over year (around 10 days in the 2024 report — *speculative, confirm*). Long dwell times are correlated with more sophisticated actors and with greater eventual impact.

- **Breakout time** — coined by CrowdStrike. The elapsed time between initial host compromise and lateral movement to a second host. The 2024 CrowdStrike Global Threat Report cited median breakout times of ~62 minutes for hands-on-keyboard intrusions *(speculative — confirm the current report)*. Short breakout times are what make the "containment race" matter.

- **ATT&CK (MITRE ATT&CK)** — the canonical taxonomy of attacker tactics, techniques, sub-techniques, software, and groups. Maintained by MITRE since ~2013, now the lingua franca of detection engineering. Tactics like *Initial Access* (TA0001), *Execution* (TA0002), *Persistence* (TA0003), …; techniques like *Spearphishing Attachment* (T1566.001), *PowerShell* (T1059.001), *Scheduled Task* (T1053.005). The ATT&CK Navigator (https://mitre-attack.github.io/attack-navigator/) visualizes coverage.

- **Kill chain** — the Lockheed Martin Cyber Kill Chain (Hutchins, Cloppert, Amin, 2011) decomposes attacks into seven stages: Reconnaissance, Weaponization, Delivery, Exploitation, Installation, Command & Control, Actions on Objectives. Predates ATT&CK and is coarser; still useful as a communication frame, particularly in executive briefings.

- **Diamond model** — Caltagirone, Pendergast, Betz (2013) — models intrusions as relationships between Adversary, Capability, Infrastructure, Victim. Used in threat intelligence analysis as a structuring frame.

- **Super-timeline** — a timeline of forensic events drawn from multiple artifacts and sources, merged and chronologically sorted. The canonical tool is Plaso (`log2timeline.py`, `psort.py`). Super-timelines are central to the SANS FOR508 methodology.

- **Side-channel** — in DFIR usage, an artifact that records evidence of activity without being the activity itself. Prefetch is a side-channel for execution; ShellBags are a side-channel for folder browsing; Jump Lists are a side-channel for file opening. Side-channels matter because they often survive when the *direct* evidence has been deleted.

- **Deadbox** — a forensic image taken after the system has been powered off. Synonymous with dead-box or dead-disk forensics. Contrast live-response.

- **Live-response** — forensic acquisition and examination performed against a running system. Captures volatile state at the cost of partial system contamination.

- **KAPE** — Kroll Artifact Parser and Extractor (Eric Zimmerman, originally; now maintained by Kroll). The dominant Windows triage collection tool. Uses *targets* (what to collect) and *modules* (how to process). Triage compound targets like `!SANS_Triage` collect a standard set of artifacts in minutes. https://www.kroll.com/en/services/cyber-risk/incident-response-litigation-support/kroll-artifact-parser-extractor-kape

- **Velociraptor** — open-source endpoint visibility and forensic collection platform. Rapid7-affiliated origin (Mike Cohen), now an independent project. Strength: scale (deploy across a fleet), query language (VQL) for ad-hoc hunts. https://docs.velociraptor.app

- **EZ Tools** — Eric Zimmerman's open-source Windows forensic parser collection (MFTECmd, RECmd, AmcacheParser, AppCompatCacheParser, RBCmd, JLECmd, LECmd, PECmd, RegistryExplorer, Timeline Explorer, etc.). The de facto standard for parsing individual Windows artifacts.

- **Plaso / log2timeline** — Python-based super-timeline construction. Parses dozens of artifact types into a unified Storage Media File. Maintained by Joachim Metz et al. https://plaso.readthedocs.io

- **SIFT (SANS Investigative Forensic Toolkit)** — the Ubuntu-based forensic workstation distributed by SANS, used as the reference platform for FOR508 and FOR500 courses. Includes Volatility, Plaso, EZ Tools (via Wine), and dozens of others, pre-configured. The hackathon explicitly requires building on or integrating with SIFT.

- **Jump bag** — the physical kit a responder takes to an on-site engagement: blank disks, write-blockers, cables, USB hubs, KAPE-on-USB, network taps, forensic boot media, paper CoC forms, business cards, snacks. The term comes from emergency medical response. Modern jump bags also include 4G/5G modems and starlink-style satellite kits for hostile-network environments.

- **Golden image** — the known-clean baseline image of an OS install used by an organization. Senior analysts compare suspect systems against the golden image to identify deltas. The discipline overlaps with configuration management.

- **Persistence** — ATT&CK tactic TA0003. Mechanisms by which an attacker survives reboot / logout / patching. The catalog is extensive (Autoruns hits ~200 categories) and the canonical reference is `domain/02-windows-artifacts-encyclopedia.md`.

- **Lateral movement** — ATT&CK tactic TA0008. Movement from one compromised host to another. Common techniques: RDP, SMB / admin shares, WMI / WMIC, PsExec, PowerShell remoting, scheduled tasks at remote, DCOM activation, service creation on remote.

- **C2 (Command and Control)** — ATT&CK tactic TA0011. The channel(s) the attacker uses to send commands and receive output. Modern C2 frameworks: Cobalt Strike (commercial / leaked), Mythic, Sliver, Havoc, Brute Ratel. Channels include HTTPS, DNS, named pipes, custom protocols. C2 detection is one of the highest-leverage SOC capabilities.

- **Beaconing** — the regular-interval, low-jitter, small-payload behavior of most C2 channels at idle. Even custom C2 channels usually beacon, and the beacon pattern is detectable in flow data even when the content is encrypted. Tools like RITA (Active Countermeasures) specialize in beacon detection.

- **Exfiltration** — ATT&CK tactic TA0010. The movement of stolen data out of the environment. Modern attackers exfiltrate via cloud storage (Mega, Dropbox, Google Drive), cloud apps (OneDrive, SharePoint abuse), `rclone` to attacker-controlled S3, or custom protocols.

- **Staging** — preparing data for exfiltration: collecting it from multiple sources, compressing it (often into encrypted archives), placing it in a staging directory. Staging artifacts (large 7z / RAR files in `\Users\Public\` or `%TEMP%\`) are often the first detectable sign of impending exfil.

- **Anti-forensics** — techniques attackers use to inhibit forensic analysis: log deletion, timestamp manipulation (timestomping), file deletion with secure overwrite, encrypted payloads, in-memory-only execution, living-off-the-land. The catalog is in `domain/05`. Detecting *absence* — the anti-forensic action itself — is its own discipline.

- **LOLBin / LOLBAS** — Living-Off-the-Land Binary / Living-Off-the-Land Binaries and Scripts. Legitimate Windows binaries that can be coerced into performing attacker objectives (download, execute, dump, encode/decode, bypass UAC). The canonical reference is the LOLBAS project (https://lolbas-project.github.io/). Examples: `regsvr32.exe` for code execution via remote .sct, `bitsadmin.exe` for download, `certutil.exe` for download and decode, `mshta.exe` for HTA execution, `installutil.exe`, `msbuild.exe`, etc.

- **BYOVD (Bring Your Own Vulnerable Driver)** — an attack technique in which the attacker installs a known-vulnerable, validly-signed driver to gain kernel-level execution and bypass EDR / AV. Many EDR products run in kernel space; BYOVD lets the attacker load their own kernel code via a legitimate-looking driver. Examples: `RTCore64.sys`, `gdrv.sys`, the leaked Procmon driver. Tracked in the LOLDrivers project (https://www.loldrivers.io/).

- **Hands-on-keyboard** — a live human attacker interacting directly with the compromised environment, as opposed to fully automated malware. Hands-on-keyboard attacks (used in most modern ransomware and APT operations) leave different forensic fingerprints (irregular timing, typo / correction patterns, human session behavior) than automated ones.

- **Dwell** — short for dwell time. Sometimes used as a verb ("the attacker dwelled for 47 days").

- **Blast radius** — the scope of impact. How many hosts, accounts, data sets touched. Determines containment strategy.

- **Runbook** — a structured operational procedure for handling a specific scenario. SOC runbooks for specific alert types. IR runbooks for specific incident types (ransomware runbook, BEC runbook, insider runbook).

- **Playbook** — broader than a runbook; usually a higher-level orchestration of multiple steps and actors. SOAR (Security Orchestration, Automation, Response) products execute playbooks.

- **MTTD (Mean Time To Detect)** — average time between initial compromise and detection across the SOC's incidents.

- **MTTR (Mean Time To Respond)** — average time between detection and containment / resolution.

- **EDR (Endpoint Detection and Response)** — agent-based endpoint security tooling that combines prevention (AV), detection (behavior monitoring), and response (kill, isolate, remediate). CrowdStrike Falcon, Microsoft Defender for Endpoint, SentinelOne, Cortex XDR, Carbon Black, Sophos Intercept X, ESET Inspect.

- **XDR (Extended Detection and Response)** — EDR + telemetry from other layers (email, identity, network, cloud). The market term is fuzzy; most XDR products are EDR plus integrations.

- **SOAR (Security Orchestration, Automation, Response)** — playbook-execution platform that fires actions across multiple security tools. Palo Alto XSOAR (Demisto), Splunk SOAR (Phantom), Tines, Torq.

- **SIEM (Security Information and Event Management)** — central log aggregation and correlation. Splunk Enterprise Security, Microsoft Sentinel, Elastic Security, Chronicle (Google), Sumo Logic, IBM QRadar.

- **Threat intel feeds** — sources of indicators and reports. Commercial (Recorded Future, Mandiant Advantage, CrowdStrike Falcon Intelligence, Intel 471, Flashpoint, Dragos for OT). OSINT (Abuse.ch — MalwareBazaar, URLhaus, ThreatFox; AlienVault OTX, now LevelBlue; ThreatMiner; Censys / Shodan for infrastructure pivoting). The DFIR Report (thedfirreport.com) publishes annotated case reports that are themselves consumed as intel.

- **MISP** — Malware Information Sharing Platform & Threats Sharing. Open-source threat-intel sharing platform widely used by CERT / ISAC communities. https://www.misp-project.org

- **Sigma rules** — a generic, SIEM-agnostic detection rule format (https://github.com/SigmaHQ/sigma). Sigma rules can be translated into Splunk SPL, Sentinel KQL, Elastic EQL, etc. The Sigma ecosystem is the closest thing to a community-maintained detection catalog.

- **YARA rules** — pattern-matching rules for malware classification (https://virustotal.github.io/yara/). YARA hits are *file-content* matches; widely used in IR for sweep-and-find across collected images.

- **PCAP** — packet capture, in the libpcap / pcap-ng file format. The gold standard of network evidence when available. Captured by Wireshark, tcpdump, Zeek, Suricata, network TAPs.

- **Zeek** — open-source network analysis framework, formerly Bro. Produces structured logs (`conn.log`, `dns.log`, `http.log`, `ssl.log`, etc.) from packet captures. The standard intermediary between raw PCAP and SIEM.

- **Suricata** — open-source network IDS/IPS, runs Snort-compatible rules + its own rule language. Often paired with Zeek (Zeek for visibility, Suricata for detection).

- **Sysmon** — Microsoft Sysinternals System Monitor. A free service that produces high-fidelity Windows endpoint event logs (process creation with full command line and hashes, network connections, file creation, registry modification, image load, named pipe activity, WMI subscription, DNS query, etc.). The single most useful free Windows EDR-replacement. Configuration is via XML and the standard community config is Olaf Hartong's `sysmon-modular`.

The glossary is partial. The full catalog of artifact-specific vocabulary lives in `domain/02`.

---

## 13. SANS DFIR doctrine in five bullets

The SANS DFIR curriculum is a family of week-long courses: FOR500 (Windows Forensic Analysis), FOR508 (Advanced Incident Response, Threat Hunting, and Digital Forensics), FOR526 (Memory Forensics), FOR572 (Advanced Network Forensics), FOR578 (Cyber Threat Intelligence), FOR610 (Reverse-Engineering Malware), and others. The courses are technically distinct but doctrinally consistent. The doctrine they collectively teach as "the right way" can be compressed to five bullets:

1. **Know normal, then find evil.** The precondition for detecting attacker activity is internalized fluency in what a clean system looks like. Process tree, persistence locations, network baselines, registry baselines, common LOLBins, expected file paths. Detection is baseline comparison. (Source: the Hunt Evil / Find Evil poster; FOR500; FOR508 day 1 material.)

2. **Corroborate before you claim.** No single artifact is trustworthy in isolation. A finding requires agreement across independent artifacts. Disagreements among artifacts are themselves findings — usually evidence of anti-forensics. (Source: FOR508; Carvey's books; widely echoed across the DFIR Report's case writeups.)

3. **Timeline is the spine.** Build a super-timeline early. Read the case along its timeline rather than along artifacts. Causality, scope, anomalies all surface through chronology. (Source: FOR508; Plaso documentation; the entire `log2timeline` ecosystem.)

4. **Hypothesis-led, time-budgeted, pivot-disciplined.** Form a working hypothesis, predict what artifacts you'd see if it were true, test those predictions, pivot when evidence refutes. Allocate time budgets per hypothesis. Record dead ends with the same rigor as confirmed findings. (Source: FOR508 instructor notes; FOR578 hypothesis-led intel; David Bianco's threat hunting essays; SANS Threat Hunting course material.)

5. **Defensibility over completeness.** A finding you can defend under cross-examination beats a finding you cannot. Chain of custody, hash verification, reproducible analysis, explicit statement of what you did *not* check. The report is the work product, not the tool output. (Source: FOR508; FOR500 reporting modules; Steve Anson's training corpus; the SANS GIAC Gold Paper expectations.)

These five aren't independent — they reinforce each other. Knowing normal is the precondition for hypothesis formation. Corroboration is what makes hypotheses confirmable. Timeline is the substrate on which corroboration happens. Hypothesis-pivot discipline is what makes the work efficient. Defensibility is what makes the work valuable. A senior analyst is identifiable by carrying all five in their hands at once.

---

## 14. Common analytical anti-patterns

The list of ways a DFIR investigation can fail analytically. Drawn from published case post-mortems (DFIR Report annual reviews, Mandiant M-Trends "what went wrong" sections), SANS instructor critique of student labs, and the small but quotable body of published peer-review studies of forensic reasoning (notably the NIST OSAC Digital Evidence subcommittee's analytical-bias work).

### 14.1 Confirmation bias

The analyst forms a hypothesis early and weights subsequent evidence according to whether it confirms the hypothesis. Disconfirming evidence is rationalized away or under-weighted. Confirming evidence is over-weighted.

Concrete manifestation in DFIR: the analyst decides "this is ransomware" within the first 10 minutes, then runs only ransomware-typical artifact checks, misses a long-dwell APT presence that *also* exists, and writes a report that names ransomware as the entire story.

Counter-discipline: name the hypothesis explicitly, *list the predictions if false*, actively look for the falsifying evidence. Carvey calls this "the negative hypothesis" — what artifacts *would* you see if your hypothesis is wrong, and do you see them?

### 14.2 Single-source claims

A finding is stated in the report on the basis of a single artifact, without corroboration. Two failure modes: the artifact is wrong (parsing error, tampering, mis-attributed timestamp) so the finding is wrong, or the artifact is right but the finding is over-interpreted (e.g., ShimCache fires for "seen at scan time" but the analyst writes "X executed").

Counter-discipline: §9 above. A finding requires multi-artifact agreement, or an explicit acknowledgment that it is single-sourced and an explanation of why corroboration is absent.

### 14.3 Ignoring the empty result

A run of a tool that returns nothing is recorded as "nothing interesting" and forgotten. But "I ran X and found Y" and "I ran X and found nothing" are *equally informative*; the empty result rules out a hypothesis just as definitively as a positive result confirms one.

Concrete manifestation: a junior analyst runs `volatility windows.malfind`, gets no hits, and moves on without recording the negative. A reviewer later asks "did you check for code injection?" and the analyst has to re-run because they didn't record the answer. Worse: the analyst implicitly remembers "no hits = nothing to worry about" and stops looking for injection-related artifacts when in fact the injection might be of a kind `malfind` doesn't catch.

Counter-discipline: log the absence with the same rigor as the presence. "Ran X at time T. Output: empty. Interpretation: hypothesis Z is refuted *for this artifact source*." The dead-end discipline of §8.4.

### 14.4 Kitchen-sink without hypothesis

Run every tool, collect every artifact, and *then* sit down to interpret. The output is unmanageable. The analyst either gets lost in the volume or implicitly forms hypotheses *after* seeing the output, in which case the work is no longer hypothesis-driven and confirmation bias is at maximum.

Concrete manifestation: KAPE Triage compound target run against 30 hosts, several hundred gigabytes of parsed output, analyst spends the next two days reading EZ Tools CSV exports trying to find something interesting. Some bad actor escapes containment in the meantime.

Counter-discipline: do enough kitchen-sink work to preserve evidence (the evidence-preservation justification for kitchen-sink is sound), then *immediately* shift to hypothesis-driven analysis. Don't wait until everything is collected to start thinking.

### 14.5 Attribution before evidence

The analyst names an attacker group early in the case, often based on a single matching TTP or a sensational news cycle, and the case narrative is built around the attribution. Later evidence is read through the lens of the named group. The attribution turns out to be wrong; the case is publicly embarrassing; insurers and lawyers are unhappy.

Concrete manifestation: case has obvious Mimikatz LSASS dumping in week one. Analyst says "looks like APT29." Final report attributes to APT29 with medium confidence. Six months later the attribution is revised to a financially-motivated criminal group; the public report has to be amended; client trust is damaged.

Counter-discipline: attribution is *the last thing* you do, *with explicit confidence levels*, *only* if the TTP fingerprint is distinctive enough to support it. Most engagements do not need to name an actor; "matches the TTP profile of financially-motivated ransomware operators in the LockBit-adjacent ecosystem" is more useful and more defensible than "LockBit." When in doubt, do not attribute.

### 14.6 Trusting the timeline blindly

The super-timeline is the spine of the investigation, but the super-timeline is *also* built from artifacts that can be tampered with. Timestomping (MITRE T1070.006) directly attacks the timeline. So does log clearing (T1070.001), event log gaps, BIOS / system-clock manipulation, NTP attacks.

Concrete manifestation: analyst reads the super-timeline at face value, concludes that initial access happened at 14:27 because that's when the malware's MFT $STANDARD_INFORMATION timestamp says it was created. In fact the attacker timestomped the file post-installation; the actual $FILE_NAME or $UsnJrnl entry shows creation 3 days earlier. The reconstructed attack timeline is wrong by 72 hours.

Counter-discipline: cross-check timestamps across artifact sources. NTFS $STANDARD_INFORMATION (timestomp-able) vs $FILE_NAME (much harder to timestomp). MFT vs $UsnJrnl. File timestamps vs registry timestamps vs event log timestamps. When two sources disagree on a timestamp, the disagreement is a finding (see §9.8).

### 14.7 Over-confidence in EDR

Modern EDRs (CrowdStrike Falcon, Microsoft Defender for Endpoint, SentinelOne) produce excellent telemetry, and the analyst comes to treat EDR's view of the host as authoritative. But EDRs have known blind spots: kernel-level rootkits via BYOVD (the EDR's own driver is bypassed), userland evasion via direct syscalls, AMSI/ETW patching, EDR-pause via signed-driver attacks. An attacker who has neutralized the EDR will produce *consistent-looking-but-incomplete* EDR records.

Counter-discipline: corroborate EDR's view with independent evidence — memory image, disk artifacts, network capture. When EDR says "nothing happened" on a host where other evidence says something happened, the EDR has been blinded.

### 14.8 Over-confidence in absence of memory

A memory image is the most volatile and time-sensitive evidence. If you didn't get it (because the host was rebooted, because containment came before acquisition, because the EDR isolated the host and you had no way to image), an entire class of findings is *forever* out of reach: in-memory-only malware, the parent-of-injected-process relationships, the credentials present in LSASS at the moment of acquisition, the unsaved attacker C2 state.

Concrete manifestation: analyst writes a report concluding "no evidence of credential theft" when in fact the host was rebooted before memory acquisition, so the entire class of *in-memory* credential-theft evidence was destroyed. The report should say "we did not have memory and therefore cannot rule out in-memory-only credential theft," not "no evidence."

Counter-discipline: the *what we did not check* discipline. The report must explicitly state which evidence categories were unavailable and which findings are therefore bounded.

### 14.9 Reading the wrong baseline

A senior analyst's "know normal" baseline is built from years of seeing clean Windows systems. But "normal" varies by Windows build, by organizational golden image, by installed enterprise agents (the org's EDR, MDM, RMM tools introduce their own processes and persistence entries that are normal *here* and would be malicious *elsewhere*).

Concrete manifestation: analyst sees a scheduled task `\Microsoft\Windows\<random-looking-name>` and flags it as suspicious. In fact the task is an Intune-pushed compliance check. Or, conversely, the analyst sees `RemoteRegistry` running and considers it normal — when in fact this organization disables it everywhere and its presence is a finding.

Counter-discipline: get the organization's golden image. Compare against it. When the org doesn't have one, build a reference list from a known-clean peer host before declaring anomalies.

### 14.10 Pattern-matching from one case to the next without reset

Senior analysts develop pattern libraries from prior cases ("looks like X" is mental short-hand for matched-against-prior-case Y). The shortcut accelerates the work and is usually correct. The failure mode: applying the pattern from case Y to case X when only some features match and the cases are actually different.

Concrete manifestation: analyst worked a Conti ransomware case last week, sees a vssadmin shadow-copy deletion in this week's case, jumps to "Conti." This week's case is in fact a different group reusing the same LOLBAS technique (T1490 is used by many actors). Pattern-matching pulled the analyst toward attribution that wasn't supported.

Counter-discipline: pattern-matching is a hypothesis generator, not a hypothesis confirmer. The hypothesis still has to be tested with its predictions on the current case. The senior habit is "looks like Conti — let me check the other six things that would be true if it were."

---

## End notes

- Citations in this file are inline. The most heavily-cited primary sources: NIST SP 800-61r2 (https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final); SANS Hunt Evil / Find Evil poster (https://www.sans.org/posters/hunt-evil/); RFC 3227 (https://datatracker.ietf.org/doc/html/rfc3227); David Bianco's Pyramid of Pain (http://detect-respond.blogspot.com/2013/03/the-pyramid-of-pain.html); MITRE ATT&CK (https://attack.mitre.org); Brian Carrier, *File System Forensic Analysis*, Addison-Wesley 2005; Harlan Carvey's blog and books (windowsir.blogspot.com); the DFIR Report (thedfirreport.com); Mandiant M-Trends annual reports; the SANS Reading Room (https://www.sans.org/white-papers/).

- Several factual claims in this file are marked *(speculative)* where the underlying date, version, or statistic should be verified before being cited in a deliverable. The substantive doctrinal claims (what senior analysts do, how the lifecycle is structured, how the Pyramid of Pain works) are not speculative — they are the well-documented consensus of the field. The speculative items are mostly version numbers and recent-year statistics that move year-to-year.

- This file is *domain knowledge only*. It contains no architecture decisions for SilentWitness. Downstream design phase agents reading this file should treat its content as ground truth about DFIR practice and own the architecture choices themselves.

- Adjacent files extend specific topics: `domain/02` for the Windows-artifact catalog the senior analyst's "know normal" rests on; `domain/03` for memory forensics; `domain/04` for disk/network/log forensics; `domain/05` for anti-forensics and ATT&CK-mapped attacker playbooks; `domain/06` for the SIFT toolchain; `user/09` for the IR consultant's day in full; `stakeholders/12` for the legal and judge-persona dimensions of the defensibility doctrine in §10 and §13.
