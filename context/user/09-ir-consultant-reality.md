# 09 — IR Consultant Reality

> **Domain knowledge document.** Facts about the user, their day, their reports, what their customers want. No architectural prescription. Design-phase agents read this to make grounded decisions about who they are designing for.
>
> Scope: persona + workflow + report anatomy + customer comms + practitioner voice. Sources at the end and inline. ~20K words.
>
> If you came here from `STRATEGY.md`, the wedge is "a hypothesis-first IR investigator that drafts its own structured incident report as the case unfolds." This file teaches you what that drafted report has to look like and who it has to convince.

---

## Table of contents

- [Part A — The IR Consultant Persona](#part-a--the-ir-consultant-persona)
- [Part B — The Engagement Flow (Hour by Hour)](#part-b--the-engagement-flow-hour-by-hour)
- [Part C — Engagement Variants Beyond Ransomware](#part-c--engagement-variants-beyond-ransomware)
- [Part D — Incident Response Reports: Anatomy + Templates](#part-d--incident-response-reports-anatomy--templates)
- [Part E — Customer / Stakeholder Communication Patterns](#part-e--customer--stakeholder-communication-patterns)
- [Part F — Validation From Practitioner Voices](#part-f--validation-from-practitioner-voices)
- [Sources](#sources)

---

## Part A — The IR Consultant Persona

### A.1 Who they are

The person we are designing for has a fairly stereotyped career arc, and that arc shows up over and over in LinkedIn bios, Black Hat speaker pages, SANS instructor blurbs, and the "About the Author" lines on Hexordia / Forensic Focus articles.

**Typical bio of a senior IR consultant (5–15 years experience):**

- Started in security operations or networking — SOC L1/L2 at a managed security service provider (MSSP), help desk → security analyst path at a Fortune 500, or a network/sysadmin role that drifted toward security after an incident.
- OR (very common): came in laterally from law enforcement — FBI Cyber Division, Secret Service Electronic Crimes Task Force, state police computer crimes unit, military signals/cyber (Air Force OSI, Army CID Cyber, NCIS, Marine Corps Cyber Auxiliary), federal Office of the Inspector General.
- OR came from a Big 4 / advisory firm — PwC, KPMG, Deloitte, EY — where they did "cyber risk" or "forensic technology" consulting before specializing in incident response.
- Holds at least one and usually three of: **SANS GIAC** certifications (GCFE, GCFA, GREM, GCIH, GNFA, GCFR, GCIA, GPEN), **EnCE** (EnCase Certified Examiner), **CCE** (Certified Computer Examiner), **AccessData ACE**, **Cellebrite Certified Operator/Physical Analyst**, **CFCE** (Certified Forensic Computer Examiner from IACIS), or **CISSP** for the management track.
- Has a four-year degree (CS, criminal justice, IT, or "cybersecurity" if they're younger) and frequently a master's (e.g., the SANS Technology Institute MS, Champlain MS in Digital Forensic Science, John Jay MA in Digital Forensics & Cybersecurity).
- Speaks at one or two conferences a year: SANS DFIR Summit, OSDFCon (Open Source Digital Forensics Conference), Magnet Virtual Summit, BlueTeamCon, BSides, DFRWS, Enfuse (OpenText/EnCase user conference).

**How they sell themselves:**

The exact words a senior IR consultant uses to describe their job change depending on the audience.

- To an executive: "I lead incident response engagements for clients facing active intrusions — ransomware, business email compromise, insider threats, nation-state actors. We get them back to business and we tell them what happened."
- To a peer at a conference: "I do IR. I run the on-keyboard work, write the deliverables, hand off to the threat intel and remediation teams."
- To a lawyer: "I'm a digital forensic examiner. I follow forensically sound chain of custody. My findings are repeatable and I can defend them on the stand."
- To a recruiter: "Senior DFIR consultant, 7 years, FOR508/FOR526/FOR578, ransomware and BEC focus."

The shape that matters: this is **not a SOC analyst**. SOC analysts work shifts, watch dashboards, write tickets, and escalate. The IR consultant works **engagements** — discrete, scoped, deliverable-producing, billable, time-bound. They are closer in workflow to a litigator than to a SOC analyst.

### A.2 Where they work

There is a tiered market for IR talent, and the segment a consultant is in shapes everything else — their daily rate, their tooling stack, their customer expectations, their report templates.

**Tier 1 — Top-of-market consulting:**

- **Mandiant** (Google Cloud Security since 2022). Roughly 600+ consultants globally. Premium retainers ($100K–$1M+ for enterprise). M-Trends report is industry-canonical.
- **CrowdStrike Services** (the consulting/IR arm distinct from the Falcon EDR product). The Services team is what gets dispatched when a Falcon customer detects something; also handles non-Falcon-customer engagements. Publishes the Global Threat Report.
- **Unit 42** (Palo Alto Networks). Heavy on retainer arrangements; merged in former Crypsis. Publishes the Unit 42 Threat Report and the *Incident Response Report*.
- **Kroll** (formerly Duff & Phelps Cyber). Hybrid IR + forensics + e-discovery. Strong on insurance carrier relationships.
- **Stroz Friedberg** (now part of Aon). Especially strong on litigation support, insider threat, and matters that go to court.
- **Secureworks Incident Response / Taegis** (acquired by Sophos 2025). Reduced footprint post-acquisition but still present.
- **IBM X-Force Incident Response** (formerly part of IBM Security; now sold to Palo Alto Networks 2025).
- **NCC Group / Fox-IT** (large in EU, post-Fox-IT acquisition).
- **Trustwave SpiderLabs IR** (legacy but still active).

**Tier 2 — Specialty / boutique:**

- **TrustedSec IR** (Dave Kennedy's firm; very practitioner-oriented).
- **Volexity** (memory-forensics-led; closely associated with Volatility Foundation).
- **Sygnia** (Israeli; high-end, often Mossad/8200 alumni).
- **Coalfire** (also large in PCI assessment).
- **Optiv Incident Response** (post-Accenture/FishNet).
- **Aspen Forensics** (smaller, court/expert-witness oriented).
- **Informed Defense** (small US IR shop).
- **CyberCX DFIR** (large in APAC).
- **Charles River Associates** (litigation-heavy).
- **GuidePoint Security DFIR**.
- **Magnet Forensics Professional Services** (the tool vendor's services arm).
- **Hexordia** (Mari DeGrazia and mobile forensics specialists).

**Tier 3 — Insurance-carrier-driven panel firms:**

When a cyber insurance claim opens, the carrier (Chubb, AIG, Beazley, AXA XL, Tokio Marine HCC, CFC, At-Bay, Coalition, etc.) directs the insured to a "panel" of pre-approved IR firms. Panel firms include the names above plus a tier of mid-sized firms whose entire engagement pipeline is insurance-driven. Examples: **Tetra Defense / Arctic Wolf IR** (acquired 2022, then folded), **Surefire Cyber**, **Charles River Associates Cyber**, **Crum & Forster's Cyber Incident Response Team partners**.

The panel arrangement matters because:
- The carrier often picks the firm (the insured does not).
- The carrier sets the hourly rates via a master service agreement (MSA), usually below market.
- The deliverable format is partly dictated by the carrier (they want specific sections for their loss adjuster).
- The carrier's outside counsel (a breach coach law firm — Mullen Coughlin, Lewis Brisbois, McDonald Hopkins, BakerHostetler, Constangy Brooks) usually engages the IR firm under privilege.

**Tier 4 — Big EDR vendor's IR retainer team:**

Every endpoint detection and response (EDR) vendor sells an IR retainer attached to their product:
- **CrowdStrike Falcon Complete + IR Services**.
- **SentinelOne Vigilance + IR**.
- **Microsoft DART** (Detection and Response Team) — internal Microsoft IR for Microsoft customers.
- **Palo Alto Unit 42 retainer** attached to Cortex XDR.
- **Trellix Mandiant Advantage** (legacy FireEye, now Trellix).
- **BlackBerry Cylance IR Retainer team** (the team that still exists post-BlackBerry-divest-to-Arctic-Wolf shifts).
- **Sophos Rapid Response** (acquired Secureworks IR capability 2025).
- **Wiz IR** (cloud-native specialty, growing fast in CSPM-to-IR pipeline).
- **Trellix IR** (post-FireEye/McAfee merger).

**Tier 5 — In-house ("CIRT" / "CSIRT" / "IR team"):**

The Fortune 500 increasingly has an in-house IR team that lives inside the SOC or alongside it. Job titles: "Senior Incident Response Engineer," "Lead Cyber Incident Investigator," "Principal CSIRT Analyst." They handle most incidents themselves and only call in external consultants when the case is unusual (nation-state, multi-tenant, criminal-litigation-bound) or when their cyber insurance requires it.

The in-house team's deliverables go to internal leadership (CISO, CIO, general counsel), not external clients. Their workflow is otherwise very similar to a consulting engagement.

**Tier 6 — Regional MSPs / MSSPs adding IR retainer:**

A managed service provider serving mid-market clients (regional banks, manufacturers, healthcare) increasingly tacks on an "IR retainer" SKU. Sometimes they staff it themselves; more often, they subcontract to a Tier 2 boutique under a white-label arrangement. The mid-market client believes their MSP handles IR; the MSP calls Stroz when the alarm goes off.

### A.3 Their day

The senior IR consultant's day has two modes: **between incidents** and **in an incident**. The mix depends on the firm.

**Between incidents (the "calm" mode):**

A senior consultant at a Tier-1 or Tier-2 firm typically spends ~40% of their hours on non-incident work:
- Retainer customer relationship management — quarterly business reviews, tabletop exercises, "purple team" workshops.
- Threat hunting engagements (proactive — not in response to a specific alert).
- Internal R&D — writing parsers, contributing to KAPE targets/modules, building Splunk searches, testing new tools.
- Mentoring junior consultants, reviewing draft reports.
- Training prep and delivery (some senior consultants moonlight as SANS instructors at ~$10K/week external rate).
- Writing — blog posts (for marketing), threat advisories for retainer customers, contributions to the firm's annual threat report (M-Trends, Unit 42 Threat Report, etc.).
- Pre-sales — joining a sales call with the BD team to credentialize a prospect, explain methodology, scope a potential retainer.

**The "ping":**

When a sales rep closes an IR retainer deal or a panel call routes a fresh incident to the firm, the on-call rotation picks it up. There is a literal **"IR hotline"** — a phone number staffed 24/7. At the bigger firms there's also a Slack / Teams channel called something like `#ir-active` or `#case-intake`. The intake usually comes from one of:

- The customer calls the hotline ("we're locked out, screens have a ransom note").
- The customer's outside counsel calls ("we have a possible incident, we'd like to engage you under privilege").
- The insurance carrier or breach coach calls ("we have a notified incident, here's the insured's contact info").
- The firm's own EDR / managed detection product fires ("CrowdStrike Falcon Complete escalation: novel persistence at customer X").

The on-call lead consultant gets paged. They have to be on a kickoff call **within 1 hour** (some retainers contractually specify 30 minutes; some 4 hours). This is why senior IR consultants almost always have a laptop within arm's reach, including evenings and weekends if they're on-call.

**The kickoff call:**

15–60 minutes. Customer side: CIO/CISO, IT director, maybe general counsel, maybe an HR lead if insider threat, the breach coach attorney if applicable. Firm side: the on-call senior, sometimes a director, often the assigned client success manager.

The senior consultant asks a tightly choreographed sequence of questions:
- What did you see? When? Who saw it first?
- What systems are involved? How many?
- Is the adversary still active? Have you done anything to contain?
- What's your environment — Windows shop? Hybrid? Cloud-only? AD/Entra? EDR deployed?
- Do you have your own SOC, MSSP, both, neither?
- Is there pending business impact — payroll Friday, big contract Monday?
- Have you notified law enforcement? Insurance? Counsel?
- What's the most important question we can help you answer first?

The kickoff produces a one-page **scoping memo** and an **engagement letter** (which the lawyers process in parallel). The consultant decides on the spot whether to engage a single host or a fleet, whether to fly someone on-site or run remote, and the rough shape of the first 72 hours.

**The evidence acquisition coordination call (T+1 to T+4 hours):**

A second call brings in the customer's IT team. The IR firm walks them through getting evidence off the impacted hosts. Sometimes the firm ships a "jump bag" (write-blocker, external USB-3 drives, a Linux laptop with KAPE pre-staged) to the customer. Sometimes they deploy a remote acquisition agent (Velociraptor, KAPE+SFTP, Cybereason, F-Response, Magnet AXIOM Cyber's remote collector). Sometimes they SSH/Bastion into the customer's environment and acquire from there.

**The "war room":**

If the engagement is big enough, the firm spins up a war room — usually a Microsoft Teams or Zoom standing meeting plus a dedicated Slack channel. The pattern is:
- Daily standup at 0900 customer time. 30 minutes max. Each lane (host forensics, network forensics, log analysis, malware analysis, remediation, customer relationship) gives a status.
- Continuous Slack / Teams for "I just found this, look at this artifact."
- The lead consultant maintains a running **investigation tracker** — usually a Confluence page, OneNote notebook, or a shared Markdown doc — with hypotheses, findings, IOCs, and open questions.
- At 1800–2000 customer time the lead writes a daily update for the customer's executive team.

The war room runs for as long as the active investigation lasts (usually 5–14 days for a normal ransomware case; longer for nation-state or insider).

**The flowing-water of the workday:**

A typical 10-hour day of a senior consultant in active engagement looks roughly like this:
- 0800 — wake up, read overnight Slack, check whether the offshore team (often EMEA or APAC) has handed off anything new.
- 0830 — coffee and the first hour of "deep work" — usually parsing whatever artifact was waiting from acquisition the night before.
- 0930 — daily standup with the customer.
- 1000 — work the case. This is where the command-line stenography lives. Run a Volatility plugin, parse a registry hive, search EVTX, pivot to memory.
- 1230 — quick lunch, often a status sync with the assigned junior.
- 1300 — work the case continues. Often the senior is also reviewing the junior's parsed output, redirecting them to a different lane.
- 1500 — customer check-in call (less formal than the standup; often just IT + IR firm lead).
- 1530 — draft notes / report.
- 1700 — internal review with director / managing consultant.
- 1800 — write the customer daily update.
- 1900 — eat, then a second wave of work if the case is hot.
- 2100–0100 — irregular but common; the senior consultant is often on the keyboard at midnight, especially in the first 72 hours.

The day is **non-linear** — interrupts come constantly. The senior is constantly switching context between (a) doing the analysis themselves, (b) reviewing what the junior produced, (c) talking to the customer, (d) coordinating with the rest of the firm. This context-switching is part of what they hate.

### A.4 Their tools

The toolchain is reasonably standardized across the field. Almost every senior consultant uses some subset of the following, and almost all of them know how to use most of these even if they prefer a particular favorite.

**Acquisition:**

- **KAPE** (Eric Zimmerman / Kroll). The dominant Windows triage acquisition tool. Targets (collection bundles) and Modules (parsing pipelines) cover almost everything you would want from a live or dead host. Free for non-commercial use; commercial license through Kroll.
- **FTK Imager** (AccessData / Exterro). Free. The classic for disk imaging — bit-for-bit `.E01` (Expert Witness Format) or `.dd` images.
- **EnCase Imager / Tableau / Magnet ACQUIRE**. Vendor-specific imaging tools.
- **WinPMEM** (Rekall / Velociraptor). Open-source memory acquisition driver for Windows.
- **Magnet RAM Capture**. Free memory acquisition tool from Magnet Forensics.
- **DumpIt** (Comae / Magnet). Single-binary memory grabber.
- **Velociraptor** (Rapid7 + community). Endpoint visibility framework with VQL query language. Increasingly the standard for remote acquisition + live response across a fleet.
- **Microsoft DART's `MDE Live Response`** for Defender for Endpoint customers.
- **F-Response** — over-the-wire access to running endpoints as block devices.
- **AXIOM Cyber Cloud collectors** (Magnet) — for M365 / GSuite / AWS / Azure log pulls.

**Analysis — disk:**

- **Eric Zimmerman's tools (EZ Tools)** — PECmd (prefetch), MFTECmd (MFT/USN/$LogFile/$J), AmcacheParser, AppCompatCacheParser (ShimCache), RECmd (registry), Registry Explorer, ShellBags Explorer, LECmd / JLECmd (LNK / jump lists), SBECmd, EvtxECmd (event logs), JLECmd, RBCmd (Recycle Bin), SrumECmd, TimelineExplorer (viewer for the CSV output of all the above). These are the absolute workhorses.
- **The Sleuth Kit (TSK)** + **Autopsy** — Brian Carrier's open-source forensic platform. `fls`, `icat`, `tsk_recover`, `mmls`, etc. Autopsy is the GUI.
- **Plaso / log2timeline** — supertimeline engine. Parses ~100+ artifact types into a single sorted timeline. The output (`.plaso` or CSV) is the kitchen-sink baseline.
- **RegRipper** (Harlan Carvey) — Perl-based registry hive parser with ~700 plugins. Still in active use; output goes into the supertimeline.
- **Hayabusa** (Yamato Security) — fast Sigma-rule-based Windows event log scanner. Outputs alerts mapped to MITRE ATT&CK.
- **Chainsaw** (WithSecure) — same idea as Hayabusa, Rust-based.
- **EvtxECmd** — Eric Zimmerman's EVTX parser, used inside Hayabusa pipelines too.
- **bulk_extractor** (Simson Garfinkel) — carves IPs, emails, URLs, credit cards, GPS coordinates, etc. out of arbitrary blobs. Used heavily for unallocated space and memory.
- **YARA** + the **VirusTotal yara-x** rewrite — pattern matching across binaries / memory / disk artifacts.
- **capa** (Mandiant) — extracts capabilities from PE files based on rules. Output is "this binary has the following capabilities: persistence via registry run key, downloads files from the internet, etc."

**Analysis — memory:**

- **Volatility 3** — the dominant open-source memory analysis framework. ~80 plugins on Windows. Python-based. Slow but reliable.
- **Rekall** — Volatility fork from Google, now mostly dormant but still in use.
- **Mandiant Redline** — proprietary memory triage GUI. Still in use in some shops despite being long un-updated.
- **Volexity Surge Collect Pro** — commercial memory acquisition.

**Analysis — network:**

- **Wireshark / tshark** — packet analysis.
- **Zeek** (formerly Bro) — protocol-aware connection logger. Produces `conn.log`, `http.log`, `dns.log`, `ssl.log`, `files.log`, etc.
- **Suricata** — IDS/IPS, often run against PCAP captures with Emerging Threats rules.
- **RITA** (Active Countermeasures) — beacon detection on Zeek output.
- **NetworkMiner** — passive network forensics tool from NETRESEC.
- **Arkime** (formerly Moloch) — full packet capture indexing.

**Analysis — log / SIEM:**

- **Splunk** — the dominant enterprise SIEM. Many IR firms have a "burner" Splunk instance they spin up per-engagement.
- **Elastic Stack (ELK / Security)** — open-source SIEM.
- **Microsoft Sentinel** — for Azure-heavy customers.
- **Devo / Securonix / Sumo Logic / LogRhythm** — secondary SIEMs the consultant occasionally encounters.
- **Mandiant Highlighter** — log triage utility from the original Mandiant days.

**Analysis — threat intel / link analysis:**

- **Maltego** — link analysis graphs. Heavy in nation-state and insider engagements.
- **MISP** — open-source threat intel sharing platform.
- **VirusTotal** — sample lookup; the IR firm usually has a Premium/Hunting subscription.
- **Hybrid-Analysis / Joe Sandbox / Any.run / Cuckoo Sandbox** — dynamic malware analysis.

**Analysis — mobile (when in scope):**

- **Cellebrite UFED** / **Physical Analyzer** — dominant mobile forensic suite.
- **Magnet AXIOM** + AXIOM Cyber.
- **Oxygen Forensic Suite**.
- **iLEAPP / aLEAPP** (Alexis Brignoni) — open-source iOS/Android artifact parsers.

**Analysis — cloud (increasingly important):**

- **Magnet AXIOM Cyber** for cloud collection.
- **Cado Security** for AWS/Azure/GCP forensics.
- **Mitiga, Wiz IR** — cloud-native IR.
- **PurpleClouds** — Mandiant's cloud playbook.
- AWS-native: CloudTrail + Config + GuardDuty + Detective.
- Azure-native: Sentinel + Defender for Cloud + Entra ID logs.
- GCP-native: Cloud Audit Logs + Security Command Center.

**Custom Python:**

Almost every senior consultant has a `~/scripts/` folder full of one-offs:
- Parse a specific artifact format the standard tools don't handle.
- Diff two timelines.
- Pivot from a hash to a URL by hitting VirusTotal + URLhaus + AlienVault OTX + GreyNoise.
- Normalize evidence paths between Linux mounts and Windows volume letters.
- Pull a CSV out of a SQL Server backup, etc.

These scripts are often shared inside the firm in a private Git repo. Some make it out as open source.

**The engagement laptop:**

Two common builds:
1. **Windows 11** primary host (because customers send Windows artifacts), with **VMware Workstation Pro** or **VMware Fusion** running a **SANS SIFT Workstation** Ubuntu VM and a **REMnux** VM. The host has KAPE + EZ Tools + FTK Imager + Wireshark + Maltego. The SIFT VM has Volatility, Plaso, RegRipper, autopsy, the works.
2. **macOS** primary (especially at firms that issue MacBooks), with **UTM** or **Parallels** running the same SIFT + REMnux VMs.

Increasingly the senior consultant also has a `~/cases/<engagement-id>/` directory structure with subfolders per host and per artifact type, and a `notes.md` (sometimes Obsidian, sometimes plain Markdown) that contains the running hypothesis log.

**Specs:** 32–64 GB RAM, 1–2 TB SSD (consultants outgrow 512 GB constantly), an external Thunderbolt 4 enclosure with 4–8 TB NVMe for case evidence, a write-blocker (Tableau or WiebeTech), a small Faraday bag for mobile.

### A.5 Billing model

The senior IR consultant is a **billable resource**, and the billing model shapes their behavior at a microscopic level.

**Standard hourly rates (2024–2026 market):**

| Role | Rate range |
|---|---|
| Junior consultant / analyst | $200–$350/hr |
| Mid-level consultant | $300–$500/hr |
| Senior consultant | $400–$650/hr |
| Director / Principal | $500–$800/hr |
| Managing Director / Partner | $700–$1,200/hr |

Insurance-panel rates are usually 20–40% lower than rack rates because of negotiated MSAs.

**The retainer:**

The dominant commercial model. A customer pays an annual retainer fee (often $25K–$150K) which buys them:
- Priority response (the 1-hour callback guarantee).
- A pre-negotiated hourly rate during incidents (e.g., $475/hr instead of $625 rack).
- A small pool of "pre-paid" hours (e.g., 40 hours — can be used for tabletops, threat hunts, advisory work, or rolled into an active incident).
- A pre-signed master service agreement so there is no contract negotiation when the incident hits.

Two retainer flavors:
1. **No-incident rebate** — if no incident in the year, the customer gets a partial refund or the hours roll over.
2. **Use-it-or-lose-it** — the retainer is consumed regardless.

**Block-of-hours retainer:**

A customer buys a block of hours upfront (e.g., 100 hours at $400/hr = $40,000) and draws down as needed. Common with smaller firms.

**Per-engagement (no retainer):**

Walk-in customer or panel referral. The firm invoices a Time & Materials engagement, typically with a not-to-exceed (NTE) cap that the customer can extend if needed.

**Time tracking:**

- At Big 4 advisory shops and at Kroll-style firms: **6-minute increments** (the "tenth of an hour" billing convention). Every email, every Slack message, every phone call is tracked.
- At many specialty IR firms: **15-minute increments**.
- At in-house IR (no client billing): time tracked but not by-the-minute.

The senior consultant types into a time-tracking system — usually a custom internal tool, sometimes Workday, sometimes Tempo (the Jira plugin). Many use a stopwatch app and dump time entries at end of day.

The **billable hour utilization target** for a senior IR consultant is typically 60–75% of available hours (after PTO, holidays, training). A junior is 75–85%. Falling below that is a problem.

**Implication for the wedge:** the senior consultant is **acutely** aware of where their hours go. They know that report-writing eats hours. They know that "running tools" eats hours. Anything that converts 2 hours of report writing into 30 minutes of report writing is directly visible as both a personal quality-of-life improvement and a firm-level utilization improvement. This is why the report-writing complaint is so loud in practitioner forums — it's billable time that doesn't feel like *expert* time.

### A.6 Their reading material

Senior IR consultants don't have time for much, but the canonical things they actually read:

**Annual industry reports (read by ~everyone):**

- **Mandiant M-Trends** — the gold standard, published every spring. Quotable, well-edited, includes attribution, dwell-time stats, exploited-vulnerability lists, and threat-actor profiles. Most-cited single document in IR.
- **CrowdStrike Global Threat Report** — adversary-focused, less dwell-time stats but heavier on threat-actor catalog ("Spider," "Panda," "Bear," etc.).
- **Verizon Data Breach Investigations Report (DBIR)** — the longest-running, the broadest pattern view. Famously dry but absolutely canonical.
- **Unit 42 Incident Response Report** + threat reports — Palo Alto's annual.
- **Sophos Active Adversary Report** — practitioner-toned summary of cases they handled.
- **IBM Cost of a Data Breach Report** (Ponemon) — heavily-cited for the financial impact numbers.
- **ENISA Threat Landscape** — European perspective, very useful in EU engagements.

**Blogs (the senior consultant has a folder of these in their RSS reader or follows on LinkedIn):**

- **Brett Shavers' Hexordia / brettshavers.com** — opinionated, especially on the analyst-vs-operator divide and on AI in DFIR.
- **Harlan Carvey's windowsir.blogspot.com** — Windows forensics legend; sharp on registry, AmCache, ShimCache, and AI training-data quality concerns.
- **Mari DeGrazia's articles4n6.com** + Hexordia content — mobile forensics, Mac forensics.
- **Lesley Carhart's tisiphone.net** — OT/ICS IR + general practitioner reflections; Dragos principal IR analyst.
- **DFIR Diva (Andrea Fortuna's blog or the DFIR Diva training site)** — accessible practitioner content for newer consultants.
- **Andrea Fortuna's andreafortuna.org** — memory forensics, threat hunting.
- **13Cubed (Richard Davis)** — Windows DFIR; YouTube channel + blog.
- **Hexordia** (Jessica Hyde's firm) — mobile and emerging device forensics.
- **SANS DFIR Reading Room** — hosts whitepapers from SANS students and instructors; quality varies but contains some of the best free DFIR writing.
- **The DFIR Report** — incident write-ups from a volunteer team; very influential as a structural template for "how a public IR report should read." (thedfirreport.com)
- **Volexity blog** — memory-forensics-led IR write-ups; influential.
- **Mandiant blog (now Google Cloud security blog)** — large-scale threat-actor profiles, M-Trends teasers.
- **CrowdStrike Adversary Universe** — adversary-focused intel.
- **Microsoft Threat Intelligence (MSTIC) blog** — nation-state and major threat actor reports.
- **Cisco Talos blog** — malware reverse-engineering, threat intel.

**Curricula and books:**

- **SANS FOR508** (*Advanced Incident Response, Threat Hunting & Digital Forensics*) — Rob T. Lee's flagship course. The implied common base for senior IR consultants.
- **SANS FOR500** (*Windows Forensic Analysis*) — the more junior-track entry point.
- **SANS FOR572** (*Network Forensics*).
- **SANS FOR526** (*Advanced Memory Forensics & Threat Detection*).
- **SANS FOR578** (*Cyber Threat Intelligence*).
- **SANS FOR610** (*Reverse-Engineering Malware*).
- **The Art of Memory Forensics** (Ligh, Case, Levy, Walters). The Volatility bible.
- **Practical Windows Forensics** (Carvey).
- **File System Forensic Analysis** (Brian Carrier).
- **Incident Response & Computer Forensics, 3rd ed.** (Mandiant alumni — Luttgens, Pepe, Mandia).
- **Practical Malware Analysis** (Sikorski/Honig).

**Communities (where they talk and lurk):**

- **r/computerforensics** — practitioner subreddit. Reddit-style culture, lots of "I'm new, what do I do?" plus occasional senior gold.
- **r/blueteamsec**, **r/cybersecurity**, **r/AskNetsec** — adjacent communities.
- **Forensic Focus forums** — the original DFIR forum; still active.
- **DFIR-related Discords / Slacks** — e.g., the DFIR Discord, BlueTeamCon Discord, Magnet Forensics community Slack, the Volatility Discord.
- **SANS DFIR Summit Slack** — alumni network.
- **#DFIR on Twitter/X** — the practitioner hashtag; declined in volume post-2022 but still has serious people.

### A.7 What they hate

Distilled from blog posts, conference recaps, podcast transcripts, and r/computerforensics threads (see Part F for sourcing).

1. **Endless triage of dead-end alerts.** Especially when the alert was generated by an EDR signature that doesn't tell you *why* it fired, just *that* it fired. Hours wasted parsing artifacts to discover that the customer's IT team installed a legitimate admin tool that the EDR flagged.
2. **Writing reports at 2 AM after the case is technically done.** The investigative work was satisfying; the report writing feels like homework. The first draft alone takes 2–4 hours per case for a senior. The peer review and customer revisions take another 1–3 hours.
3. **Customers expecting answers in 30 minutes.** "We've been hacked, what do we do?" before the consultant has even confirmed that evidence is acquired. Pressure to give preliminary answers before they're defensible.
4. **Vendors over-promising AI.** Almost every senior IR practitioner has a public complaint about a vendor demoing an AI feature that doesn't survive contact with their actual cases. Brett Shavers, Harlan Carvey, and Lesley Carhart have all written variants of this rant.
5. **Customer IT teams that destroy evidence trying to fix the problem.** Reimaging the host before acquisition. Killing processes before memory capture. Clearing event logs because "the disk was full." Resetting the AD admin password before the consultant can examine the original authentication trail.
6. **Insurance-carrier paperwork.** The carrier wants the report in their specific format, with specific sections, with specific phrasing, attached to specific claim numbers. This adds hours per engagement.
7. **The "spreadsheet of doom"** — TrustedSec's term for the manual analyst-output aggregation board during active IR, where every analyst is dropping findings into a shared Google Sheet that has no schema, no validation, and immediately becomes inconsistent.
8. **Tooling fragmentation.** The senior switches between KAPE, EZ Tools, Volatility, Plaso, Splunk, Maltego, Cellebrite, AXIOM, Wireshark, custom Python, Excel, and their notes editor — all in a single afternoon. The mental cost of context-switching is high. 49% of analysts in the SANS 2024 SOC survey reported workflows involving "too many different consoles and tools."
9. **Legal review of the report** — slow, sometimes punitive ("you can't say 'compromise,' say 'incident involving unauthorized access'"). Necessary but exhausting.
10. **Time tracking.** Even at firms with sophisticated tracking, the senior consultant resents the 5–15 minutes per day of admin to log their hours by client / matter.

### A.8 What they love

1. **The "click moment"** — when several artifacts from different sources independently confirm the same finding. The Sysmon Event 1 says PowerShell ran with an encoded command; the PowerShell script-block log decodes it; the network logs show the subsequent C2 callback; the prefetch confirms it ran; the AmCache says it was a brand-new binary. That's when the consultant *knows*. This is what they signed up for.
2. **Finding evil that the customer's EDR missed.** Vindication for the entire profession.
3. **Training a junior who gets it.** Watching an L1 form a hypothesis on their own instead of just running every tool.
4. **A clean, well-written final report that the customer thanks them for.** Especially when the customer's general counsel says "this is the best IR report we've ever received."
5. **The post-incident retrospective** where the customer fixes the gaps the consultant identified. Real-world impact.
6. **Sharing TTPs with peers** at conferences. The professional-honor culture is strong.

### A.9 The senior/junior dynamic

A typical mid-to-large engagement has a senior + junior pairing, sometimes a 1-senior-2-junior structure.

**The junior:**
- Runs the tools. Pulls the artifacts, parses them, normalizes the output, dumps the result into the case folder.
- Maintains the IOC list.
- Writes the appendices (raw tool output, artifact lists, timeline CSVs).
- Drafts the methodology section.
- Operates the evidence chain of custody (every transfer, hash, mount).

**The senior:**
- Forms the hypothesis. Decides which lane is hot. Decides when to pivot.
- Interprets the artifacts in context.
- Talks to the customer.
- Drafts the executive summary and findings sections.
- Reviews everything the junior produced and either accepts it or sends it back.
- Owns the final report. Signs the engagement letter. Sits on the witness stand if it ever goes to court.

The senior often refers to the junior's output as "raw artifact data" and treats their own role as "the interpretation layer." Brett Shavers's "tool operators vs. investigators" framing is exactly this dynamic.

**A revealing detail:** at most firms, the senior writes the final report from scratch, treating the junior's draft as raw material. The junior almost never sees their prose end up in the final document. This is partly because the senior's writing is more polished; it's also because the senior is the one who will defend the report and wants every sentence to be defensible.

### A.10 Retainer customer's expectations

The cadence the customer expects:

- **Day 0 (within 1 hour of call):** Acknowledgment + on-call senior introduced + initial scoping. "We are engaged, here's who you'll be working with, here's our first hour's action."
- **Day 0 (within 4 hours):** Engagement letter signed (often under attorney privilege via the breach coach). Evidence acquisition plan agreed.
- **Day 1 (24 hours in):** Preliminary findings memo. "What we have so far, what we're investigating, what's the rough scope." 1–2 pages. Verbal call to the customer leadership.
- **Day 2–4:** Detailed findings as they come in. A daily update email or call. The customer is making decisions (whether to pay ransom, whether to notify regulators, whether to bring systems back online) and depends on the consultant's input.
- **Day 5–10:** Preliminary final report draft circulates internally (within the IR firm) and to the breach coach attorney.
- **Day 10–21:** Final report delivered to the customer.
- **Day 21–60:** Remediation guidance, sometimes implementation support. Threat intel handoff. Possibly testimony preparation if there will be litigation.
- **Day 60+:** Retainer review. Quarterly tabletop. Threat hunting.

The above is the **customer's expectation**. The reality often slips — final reports commonly land at 4–8 weeks for complex cases — and the slip is a source of friction.

---

## Part B — The Engagement Flow (Hour by Hour)

This section walks through a representative engagement — a ransomware incident at a mid-size company — at the hour-by-hour resolution that a senior consultant actually lives through. Then it annotates where AI is currently helpful, where it falls flat, and where the gap is biggest.

The case shape: a 600-employee specialty manufacturer in the Midwest. They use Windows + Active Directory, Office 365 for email, CrowdStrike Falcon EDR on most endpoints, and have a small in-house IT team plus an MSSP. Their cyber insurance carrier is At-Bay. They wake up on a Tuesday to a ransom note on their file server.

### B.1 Hour 0–1: Triage call

**The customer's reality:**
- The CIO is in panic mode. The file server is encrypted. The CFO can't access payroll for Friday. The CISO is asking what to do.
- IT has already done some things: they disconnected the file server's network cable, they ran an EDR scan, they tried to log into a domain controller and got a Kerberos error.
- The customer dials the IR hotline at the firm on their cyber insurance panel.

**The senior consultant's reality:**
- 0830 Tuesday. The pager goes off. The on-call senior was in a 1:1 with their director.
- 0837. Dialed in to the call. Customer side has 5 people; firm side is just the senior plus a client success manager.
- 0838–0900. The senior asks the scoping questions. Captures the answers in a OneNote / Markdown doc.
- 0902. Wants to verify two things immediately: (1) is the adversary still active? (2) is there pending business impact in the next 24 hours? Answers: (1) unclear, (2) yes — payroll Friday.
- 0905. Engages a junior on the case. Pages the firm's threat intel lead in case attribution comes up.
- 0920. Reaches out to At-Bay (the carrier) and the breach coach (Mullen Coughlin) to formalize privileged engagement.
- 0950. Engagement letter circulating. Senior scopes acquisition: prioritize the file server, the most recently accessed domain controller, and 3–5 user workstations that appear in the file server's recent SMB connections.

**What gets produced in Hour 0–1:** the scoping memo, the engagement letter, an initial action list.

### B.2 Hour 1–3: Evidence acquisition

**On the customer side:**
- IT team coordinates with consultant on which hosts to acquire.
- The senior decides what to acquire: full memory + triage image (KAPE + targeted artifact collection) from the file server; memory + triage from one DC; triage from 3 workstations; CrowdStrike Falcon RTR (Real Time Response) console for live data on the rest.
- The customer's IT loads the firm's KAPE+Velociraptor agent onto a USB and runs it on the file server. The junior on the IR team configures the Velociraptor collection profile.

**The consultant's reality:**
- The senior is multitasking: drafting the daily update (even though no findings yet), prepping the war room standup for the next morning, fielding questions from the customer's legal counsel about regulatory notification (state breach laws, SEC disclosure under Item 1.05).
- The junior is on the keyboard with the customer's IT person, walking them through KAPE invocation.
- Acquisition itself takes 30–90 minutes per host (memory dump alone is ~15 minutes for 64 GB RAM; triage image is another 30–60 minutes). For multiple hosts in parallel: ~2 hours wall-clock.

**Outputs:** memory dumps (`.raw` or `.dmp`), KAPE triage zip files (Targets bundled), Velociraptor outputs (JSONL artifact files), Falcon historic data export.

### B.3 Hour 3–6: Triage analysis (first pass)

**The senior's hypothesis:** ransomware at a mid-size shop is typically one of: (a) phishing → user runs payload → escalation to local admin → lateral via SMB or RDP → DC compromise → mass deploy via Group Policy or PsExec; (b) external RDP / VPN brute force → direct DC access; (c) supply chain (an MSP got popped); (d) public-facing vulnerable web app → web shell → reverse shell → escalation. The senior forms a working hypothesis based on early signals.

**Triage workflow:**
- Run the KAPE Modules pipeline on the triage zip. Get back parsed CSVs for: $MFT, registry hives (RegRipper output), event logs (EvtxECmd + Hayabusa), Prefetch, ShimCache, AmCache, ShellBags, SRUM, scheduled tasks, jump lists.
- Run Volatility plugins on the memory dump: `windows.info`, `pstree`, `psxview`, `malfind`, `netscan`, `cmdline`, `handles`, `svcscan`. Look for injected code, suspicious processes, C2 connections.
- Pivot to event logs for the first set of timestamps: when was the ransomware binary created? when did the file server's processes spike? when did the first lateral movement happen?
- Identify the ransomware family from the note + the binary (if a sample is recoverable) + the file extension pattern. Cross-reference IDRansomware, NoMoreRansom, and the firm's internal IR knowledge base. The family identification narrows the threat-actor profile and suggests TTP patterns.

**Findings (representative):** ransomware family identified as a known affiliate program (e.g., Akira, BlackBasta, Play, INC, Medusa, LockBit successor variants). Initial access appears to be VPN brute-force against the customer's Fortinet appliance, exploiting CVE-2024-21762. Lateral movement via PsExec from a compromised admin account. The ransomware was deployed via a scheduled task pushed by Group Policy.

**Cycle time:** 3 hours of analysis to produce the first defensible hypothesis. This is the part Rob T. Lee's 14:27 Protocol SIFT demo argues should be ~25 minutes of agent-driven work.

### B.4 Hour 6–10: Blast radius assessment

**The senior pivots from "what happened" to "how bad."**

- How many hosts are impacted? Check Falcon telemetry. Cross-reference SMB share access logs from the DC (5140, 5145).
- What credentials were compromised? Run Volatility `lsadump` against the file server memory. Check Event 4624 logon types — any 4624 Type 9 (newcredentials / RunAs) showing privileged accounts on non-admin hosts? Did the adversary likely run Mimikatz / nanodump? Was DCSync attempted (4662 against the krbtgt object on a DC)?
- What data was exfiltrated, if any? Modern ransomware is double-extortion: encrypt + steal. Check the SRUM database for unusual outbound bytes from user accounts. Check Zeek conn.log (if the customer captures network) or NetFlow from the firewall. Look for large transfers to known exfil endpoints (Mega.io, Anonfiles, attacker-controlled S3, rclone usage).

**Findings (representative):** 47 hosts encrypted including the file server, two DCs, a SQL database server. Compromised credentials include 3 domain admin accounts, the AD krbtgt is suspect. Exfiltration: ~140 GB pushed to a Mega.io endpoint over the prior 72 hours. The data exfil window starts 4 days before encryption — typical double-extortion playbook.

**Customer impact:** the senior calls the customer's CISO at 1400 Tuesday to share preliminary blast radius. The customer escalates — the CFO and the GC are now on the call. The conversation pivots to whether to engage ransom negotiators (Coveware, GroupSense, Mandiant) and whether to file with FBI IC3.

### B.5 Hour 10–14: Containment guidance

**The senior consultant's role here is advisory.** The customer's IT team executes; the consultant tells them what to isolate, what to keep online, what to rebuild.

- Isolate immediately: the file server (already off network), the two DCs (rebuild from backup once forensics complete), the SQL server, any host that appears in the lateral movement chain.
- Rotate: ALL domain accounts (especially the 3 compromised DA accounts), the krbtgt account twice (24-hour gap to invalidate any golden tickets), all service accounts that touched the compromised hosts, all VPN credentials, the Fortinet admin password.
- Patch: the Fortinet appliance (CVE-2024-21762).
- Block: the Mega.io endpoints used for exfil at the firewall, the C2 IPs identified, the ransomware binary's hash in EDR.
- Don't yet: don't bring the file server back online from backup (forensics still in progress), don't try to negotiate publicly with the actor, don't reset systems the consultant hasn't examined.

**Outputs:** a containment runbook (1–2 pages), a list of specific actions for the customer's IT team, a decision tree for the customer's leadership.

### B.6 Hour 14–18: Persistence + lateral movement timeline

**The senior is now reconstructing the full attack chain.**

- Timeline of initial access: when did the first malicious VPN auth occur? What account? From what IP? Cross-reference Fortinet logs, AD authentication events (4624 Type 10), VPN session logs.
- Timeline of post-exploitation: what happened in the first hour after initial access? What tooling did the actor run? What persistence did they drop? Common artifacts: scheduled tasks (4698 / Task Scheduler/Operational), services (4697 / 7045), registry Run keys, WMI subscriptions, GPO modifications.
- Timeline of lateral movement: which hosts touched which other hosts and when? PsExec usage (Sysmon 1 cmdline + 7045 service install of PSEXESVC + named pipe 17/18). Pass-the-hash signals (4624 Type 3 from unusual sources, 4776 NTLM auth, mismatched account-to-host expectations).
- Timeline of staging: when did the actor stage the data for exfil? Look for 7-zip / rclone / WinRAR usage; large temporary files; archive creation patterns.
- Timeline of exfil: the SRUM + Zeek data already identified.
- Timeline of encryption: when did the ransomware first execute on each impacted host? File creation timestamps of the ransom note. SRUM CPU spikes on the encryption process.

**The output of this phase is the "attack chain" — a chronological narrative the senior can read aloud to the customer.** Typical format:

```
2026-05-25 14:32 UTC — First successful VPN auth as user JDOE from 185.234.219.xxx
                       (known malicious ASN). JDOE on PTO this week.
2026-05-25 14:38 UTC — Outbound RDP from VPN session to file server (FILE01).
2026-05-25 14:45 UTC — PowerShell on FILE01 downloads tooling from
                       185.234.219.xxx/tools.zip.
2026-05-25 14:51 UTC — Mimikatz residue in FILE01 memory; LSASS access
                       (Sysmon EID 10).
2026-05-25 15:02 UTC — Domain Admin account svc-backup used for first time
                       from FILE01 — pass-the-hash signal.
... (continues through to 2026-05-30 03:00 UTC encryption event)
```

This is the spine of the final report.

### B.7 Hour 18–22: Initial report draft

**The senior consultant drafts.** The junior assists with appendices.

- Executive Summary: 1 page max. What happened, scope, current status, next steps.
- Engagement Overview: scope, stakeholders, timeline, methodology references.
- Methodology: tools used, evidence acquired, chain of custody.
- Findings: per host, per TTP. Each finding has supporting artifacts referenced.
- Timeline of Attack: the chronological reconstruction above.
- IOCs: file hashes, IPs, domains, registry keys, mutex names — formatted for handoff to threat intel platforms.
- Recommendations: immediate (rotate keys, isolate hosts), short-term (rebuild DCs, patch Fortinet), long-term (MFA on VPN, network segmentation, EDR coverage gaps).
- Appendices: raw tool output, additional artifacts, full event log excerpts.

**The senior writes the executive summary, findings, and recommendations. The junior populates the methodology, timeline (from the case notes), IOCs, and appendices.**

The first draft takes ~3 hours of senior time and ~2 hours of junior time. The senior then revises, the director reviews, the junior incorporates feedback. Iteration time: 1 day until a draft is "ready to share with the breach coach" (still privileged, not yet to the customer).

### B.8 Hour 22–28: Stakeholder briefings

**The senior gives multiple verbal briefings.**

- **CIO/CISO/IT leadership:** technical depth. What we found, what's been contained, what's still being worked. 30–60 minutes.
- **CEO/CFO:** business impact framing. How many days of operations affected. Whether data was stolen. Whether to pay. Notification obligations. 15–30 minutes.
- **General counsel + breach coach:** legal framing. Evidence preservation status. Privilege status. Regulatory clock starting. Potential litigation. 30 minutes.
- **Insurance carrier (At-Bay) + carrier's loss adjuster:** financial framing. Confirmed loss categories. Coverage triggers. Forensic costs estimate. 30 minutes.
- **Board (sometimes):** the senior sometimes presents to a Board sub-committee. Very high-level. Pre-rehearsed.

Each audience wants the same facts framed differently. The senior gets very good at this code-switching — but it costs hours per day during the active engagement.

### B.9 Hour 28–40: Detailed final report

The detailed final report is what gets delivered to the customer at the end of the engagement.

**Differences from the initial draft:**
- Polished prose. Every sentence reviewed for defensibility.
- Richer findings narrative. Each finding tells a story: hypothesis → evidence → conclusion → confidence.
- More complete timeline.
- IOC tables exported into machine-readable formats (CSV, STIX, MISP feed).
- A "What We Did Not Examine" section — explicit about scope limits.
- A remediation roadmap with priorities, owners, and timeframes.
- Appendices with raw artifact dumps for the customer's audit.

The senior spends ~12–18 hours over Hours 28–40 polishing. The director reviews twice. The breach coach reviews once. The customer is shown a preview and gives feedback. Final version released.

**Page count for a representative ransomware engagement:** 40–80 pages including appendices. The executive summary is page 1. The findings narrative is pages 2–8. The timeline is pages 9–15. The IOCs are pages 16–25. The recommendations are pages 26–30. The remainder is appendix.

### B.10 Beyond Hour 40: Lessons learned, remediation, threat intel handoff

**Hours 40–80 (calendar days 2–4):**
- The senior turns the technical findings into a remediation roadmap, often co-authored with the customer's IT team.
- Threat intel handoff to ISACs (e.g., Manufacturing-ISAC for this customer), to the carrier's intel team, to the firm's internal TIP.
- If the case is going to court (criminal referral to FBI, civil litigation against an insider, etc.), the senior begins preparing as an expert witness — deposition prep, exhibit assembly.
- The senior writes a "lessons learned" internal document for the firm — what TTPs the actor used, what worked in the response, what was clumsy.

**The retainer customer also expects a "tabletop" session 60–90 days post-incident** where the senior walks the customer's team through what would have happened differently if particular controls had been in place. This is part advisory, part sales (the customer often buys more services after seeing the gaps).

### B.11 Where does AI help most, per phase?

This is the question the wedge sits on top of. Honest assessment per phase:

| Phase | Where AI helps today | Where AI fails today | Where the gap is biggest |
|---|---|---|---|
| Triage call | Suggesting scoping questions; drafting the scoping memo. | Reading the room. Knowing when to push the customer. Reassuring the panicked CIO. | Low — humans are needed here, and the savings would be small. |
| Evidence acquisition | Generating KAPE / Velociraptor collection profiles tuned to the hypothesis; explaining options to the customer's IT team. | Operating the customer's hardware. Dealing with locked BitLocker volumes. | Medium — collection profile generation is a real time-saver. |
| Triage analysis | Running pre-canned tool chains; parsing output; surfacing anomalies; mapping artifacts to MITRE ATT&CK. | Knowing when to pivot. Recognizing context-dependent meaning (e.g., admin tool that's normal here but abnormal there). Forming a hypothesis the customer's context supports. | **HIGH** — this is exactly the "command-line stenographer" pain Rob T. Lee names. The kitchen-sink parse is mechanical; the interpretation is human. |
| Blast radius assessment | Cross-referencing host lists against logs; aggregating evidence across hosts; summarizing into a table. | Knowing when to chase a thread vs. when to stop. Assessing the credibility of the customer's IT team's claim that "X system is air-gapped." | HIGH — aggregation + summarization is high-leverage. |
| Containment guidance | Generating containment runbooks from the findings; templated guidance on credential rotation, krbtgt, etc. | Making the trade-off call (e.g., "keep this host online because the business needs it" vs. "isolate it for forensics"). | MEDIUM — runbook generation is helpful; trade-offs are human. |
| Persistence + LM timeline | Building the chronological timeline from event logs + Sysmon + EDR data. Extracting attack-chain events from a supertimeline. | Interpreting ambiguous events. Connecting a host-side artifact to a network-side one when timestamps don't quite match. | **VERY HIGH** — timeline construction is mechanical and currently eats hours. |
| Initial report draft | Drafting prose from structured findings. Generating IOC tables. Drafting recommendations from a list of identified gaps. | Writing the executive summary. The framing for the customer's leadership. The right level of confidence language. | **VERY HIGH** — every senior practitioner cites this as the biggest pain. |
| Stakeholder briefings | Generating audience-tailored summaries from the report. Drafting talking points. | Live Q&A. Reading the room. Managing executive emotion. | LOW — humans needed. |
| Detailed final report | Polishing prose. Generating IOC exports in multiple formats. Producing the recommended remediation list. | Defensibility judgment. Cross-examination preparation. | **HIGH** — polish is real but limited; the defensibility is the hard part. |
| Lessons learned, remediation | Drafting remediation tasks. Threat intel formatting (STIX, MISP). | Long-term advisory. Customer relationship. | MEDIUM — generation is helpful. |

**The summary judgment:** AI's highest-leverage contribution per the senior consultant is in **triage analysis, blast radius aggregation, timeline construction, and report drafting** — exactly the lanes Brett Shavers names ("summarizing, clustering, speeding up review, and drafting") and exactly the lanes Rob T. Lee names ("command-line stenography").

The lowest-leverage contribution is in customer interaction, defensibility judgment, and live Q&A — exactly the lanes that justify the senior's high billable rate.

A tool that captures the high-leverage lanes without overreaching into the low-leverage lanes is what the senior consultant would actually adopt.

---

## Part C — Engagement Variants Beyond Ransomware

The ransomware engagement above is the most common shape, but a senior IR consultant runs several distinct engagement types in a year. Each has its own workflow, its own deliverable expectations, and its own AI-helpfulness profile.

### C.1 Insider data exfiltration

**The setup:** an employee is suspected of taking data with them (to a competitor, to start their own firm, or in a disgruntled-departure scenario). HR or the GC engages the IR firm.

**Differences from ransomware:**
- Much more emphasis on **user behavior analytics**. What did this specific user do in their last 30/60/90 days?
- Acquisition is targeted: the employee's workstation, their corporate phone, their cloud drive (OneDrive, Google Drive, Dropbox for Business), their email mailbox.
- Heavy use of: ShellBags (folders accessed), USB device history (registry: USBSTOR, MountedDevices, ReadyBoost — and the corresponding plug/unplug timestamps in Event 6416 / Sysmon device events), recent files (Office MRU lists, JumpLists, LNKs), printer history (Microsoft-Windows-PrintService logs), cloud sync activity (OneDrive sync database), email export activity (PST/OST creation, mailbox rules, OAuth grant tokens, Outlook search history).
- Network forensics: SMB file copies to USB; uploads to personal cloud accounts; large outbound to webmail providers; bcc to personal email.
- The deliverable is often a **forensic exhibit set** for civil litigation, not just a report. The findings need to be admissible under FRE 901/902. Chain of custody is paramount.

**Where the engagement diverges from ransomware in the senior's workflow:**
- Much slower pace. Insider cases unfold over weeks. The senior is not under 3 AM time pressure.
- More collaboration with HR and outside employment counsel.
- Much more careful documentation. The case may become an employment lawsuit; everything written must be defensible.

**AI helpfulness:** lower than for ransomware in the speed dimension; higher in the synthesis dimension. The senior is often summarizing thousands of file-access events into a narrative for a non-technical audience (the GC, a jury). Synthesis + narrative-generation is high-leverage.

**Representative tools:** EZ Tools for the user activity artifacts; Magnet AXIOM (which has strong user-activity timeline views); ShellBags Explorer; JumpLists Explorer; USB Detective.

### C.2 BEC / payroll fraud / OAuth abuse

**The setup:** the CFO got a payment-redirection email that turned out to be from an attacker who had compromised the email account of a vendor. Or the customer's own user accounts were compromised via phishing, and the attacker has been reading email, replying with fake invoices, or setting up rules to hide their tracks.

**Differences from ransomware:**
- The forensic substrate is **cloud email logs** — Microsoft 365 Unified Audit Log (UAL), Exchange mailbox audit, Azure AD / Entra ID sign-in logs, Microsoft Graph activity, OAuth consent grants.
- KAPE/SIFT-style host forensics is often not needed at all. The investigation lives entirely in M365.
- Heavy use of: mailbox rules (especially "forward all," "delete after sent," "move to RSS feeds"), inbox-rule audit, OAuth application registrations (the attacker often registers a malicious OAuth app to maintain persistence even after password reset), Conditional Access policy changes, MFA registration events.
- The standard playbook tools: **MIA (Microsoft 365 Investigative Assistant)** — actually the M365 Compliance Center's eDiscovery + audit search; **Hawk** (Office 365 audit log analysis from CIRT); **MIATool / MIA** (community tooling); **Microsoft Compromised Account Workflow**.
- Strong overlap with **financial fraud investigation** — the engagement often runs parallel to an FBI IC3 referral and a bank-side reversal attempt. There's a 72-hour window where the FBI's Financial Fraud Kill Chain can sometimes claw back wire transfers.

**Deliverables:**
- A "compromised account" report — when did the compromise start, what mailbox rules were in place, what messages were sent or read or modified, what OAuth grants need to be revoked.
- An IOC list — the attacker's IPs (from sign-in logs), email addresses, OAuth app names, scope grants.
- A remediation roadmap focused on M365 hygiene: MFA, conditional access, OAuth governance.

**AI helpfulness:** very high for parsing the M365 audit log (which is enormous, ~100s of MB of JSON for an active mailbox), correlating sign-in events to mailbox activity, summarizing attacker actions, and drafting the timeline.

### C.3 APT / nation-state engagement

**The setup:** the customer's CISO got a tap on the shoulder from the FBI saying "we think your environment is compromised, we can't tell you how we know but trust us." Or the EDR detected a TTP that matches a known APT cluster (APT41, Mustang Panda, Volt Typhoon, Sandworm, Lazarus, etc.). Or the customer was named in a public threat intel report.

**Differences from ransomware:**
- Dwell time is months to years. The actor has had time to embed deeply.
- Tradecraft is sophisticated: custom implants, anti-forensics, encrypted C2, living-off-the-land, careful log tampering.
- The investigation is **threat-hunting-style**, not incident-response-style. Less "what just happened" and more "where else are they."
- Heavy use of: deep memory forensics (Volatility 3 against many hosts), YARA/Sigma rules tuned to the suspected actor, threat intel correlation, network-wide log analysis.
- Often involves multiple investigative agencies (FBI Cyber, sometimes CISA, sometimes foreign equivalents) and stringent disclosure restrictions.
- The customer's general counsel is heavily involved due to the regulatory disclosure pressure (SEC for public companies, sector regulators, foreign equivalents).
- The deliverable is often a "scoping report" early (what we have so far) followed by a long "comprehensive report" after months of work.

**Where it diverges in the senior's workflow:**
- The pace is sustainable. Hours are long but not crisis-mode.
- The senior spends much more time on threat intel correlation, hypothesis formation across many hosts, and looking for needles in haystacks.
- Hypothesis formation is **the dominant activity**. "We know they like X TTP — where else might it be in this environment?"

**AI helpfulness:** very high for the hypothesis-driven search across many hosts. Very high for parsing memory dumps across a fleet. Lower for the threat intel attribution (which often requires non-public information).

### C.4 Compliance / legal / e-discovery incident

**The setup:** a regulator (SEC, OCR for HIPAA, state AG, ICO/CNIL/BfDI in EU) opens an investigation related to a prior incident. Or there's civil litigation that depends on knowing what data was compromised. Or there's a criminal case (employee theft, child exploitation material, fraud) and the IR firm is engaged as a forensic examiner.

**Differences from ransomware:**
- **Chain of custody is the dominant constraint.** Every transfer, hash, mount, and tool execution is logged in a chain-of-custody form.
- The deliverable is often a **forensic examiner's report** in a format compliant with court rules — sworn under penalty of perjury, with the examiner's CV attached, with explicit methodology and tool validation.
- Heavy use of: write-blockers, court-approved imaging tools (FTK Imager, EnCase), case management platforms (Nuix, Relativity, AXIOM, Magnet REVIEW), pristine forensic copies maintained in evidence lockers.
- The IR firm partners closely with the customer's outside counsel; the engagement is almost always under attorney privilege.
- Expert witness preparation is part of the engagement.

**Deliverables:**
- An expert witness report — Rule 26 disclosure in US federal civil; equivalent local format in state / international.
- A sworn affidavit (sometimes).
- Trial exhibits — printed evidence with chain-of-custody attestation.
- Deposition prep, sometimes courtroom testimony.

**Where it diverges in the senior's workflow:**
- Very slow. Months of work.
- Documentation is exhaustive. The senior writes far more prose than in a ransomware case.
- Every methodology choice is questioned in deposition: why did you use this tool, did you validate it, how do you know it's reliable.

**AI helpfulness:** **mixed and currently risky**. AI-generated findings face Daubert + FRE 702/707 challenges in court. The senior using AI-assisted analysis must be able to explain the AI's reasoning, demonstrate the AI's reliability, and meet the methodology bar. This is the area where the legal landscape is genuinely unsettled (see FRE 707, approved by Judicial Conference in 2025). A tool whose findings the examiner cannot defend on the stand is unusable in this engagement type.

The **"every claim ties to a tool execution"** discipline this wedge embodies is **most valuable here**. It is also where over-claiming AI is most dangerous.

### C.5 Supply chain compromise

**The setup:** a vendor the customer uses has been compromised (think SolarWinds, Kaseya, 3CX, MOVEit). The customer's environment may have been a downstream target. The IR firm is engaged to scope.

**Differences from ransomware:**
- The "blast radius" question shifts from "how far did the attacker spread" to "did the attacker even use our access to do anything?"
- Heavy use of: vendor-specific IOCs (which are often public from the vendor's own disclosure or from the original incident response firm's public report), threat hunting against the customer's environment.
- The engagement is often "rule out" — confirm that the customer was not exploited, or scope the exploitation if they were.
- Multi-tenant pain: if the vendor served many customers, the customer may share notes with other affected customers; the IR firm may be coordinating across multiple affected customers under separate engagement letters.

**Deliverables:**
- A scoping report — what was the exposure window, what indicators were present, what was found in the customer's environment.
- An IOC sweep result — clean or compromised.
- A vendor management recommendation set (third-party risk).

**AI helpfulness:** high for the IOC sweep (which is often a pattern-matching exercise across a large environment), medium for the scoping report.

### C.6 Cloud-native compromise

**The setup:** the customer's environment is AWS, Azure, or GCP. The "endpoint" is a container or a Lambda or a Kubernetes pod, not a Windows workstation. The compromise was an IAM key leak, a S3 bucket misconfiguration, a compromised CI/CD pipeline, a stolen OAuth token.

**Differences from ransomware:**
- No KAPE / SIFT. The forensic substrate is cloud audit logs.
- Heavy use of: CloudTrail (AWS), Azure Activity Log + Entra ID Sign-In Logs + Azure AD audit, GCP Cloud Audit Logs, GuardDuty findings (AWS), Defender for Cloud findings (Azure), Security Command Center findings (GCP), VPC flow logs / NSG flow logs.
- The tools are different: **Cado Security** (AWS/Azure/GCP forensic platform — does cloud-side EC2 snapshot acquisition, parses CloudTrail/Activity/Audit, does container forensics), **Mitiga**, **Wiz IR**, **AWS Detective**, **Athena queries against CloudTrail S3 buckets**.
- The "acquisition" step is API calls, not USB-stick KAPE runs. The senior reads documentation for the cloud provider's logging service constantly.
- The challenge is often: the logs the customer needs weren't enabled. CloudTrail data events for S3 weren't on. VPC Flow Logs weren't on. Azure AD sign-in log retention was 30 days. The forensic substrate the senior needs doesn't exist.

**Deliverables:**
- A "what we could see, what we couldn't" report.
- An IAM compromise scope — what credentials were exposed, what permissions they had, what they touched.
- A cloud-side remediation set — IAM key rotation, MFA enforcement, log retention extension, network segmentation.

**Where it diverges in the senior's workflow:**
- The senior's mental model is different: cloud is API-first, not file-first. Artifacts are JSON, not registry hives.
- The senior is often the IR firm's "cloud person" — fewer practitioners are deeply expert in cloud forensics, so demand exceeds supply.

**AI helpfulness:** **very high**. CloudTrail JSON is voluminous and dense; LLMs are good at parsing it. The "cross-reference IAM event with downstream resource access" is mechanical work AI does well.

---

## Part D — Incident Response Reports: Anatomy + Templates

This is the heart of the document. The report is the deliverable. Everything else in the engagement is in service of producing it. Understanding what reports look like — really look like — across the field is what lets a wedge-of-report-drafting work.

### D.1 The 5 audiences

A single IR report is read (or excerpted) by several distinct audiences. The senior consultant either writes one document with multiple sections for each audience, or writes multiple documents (a common pattern is: a 1-page executive summary, a 30–60-page technical report, and a separate 5-page legal report).

**1. Executive leadership.** CEO, CFO, COO, sometimes Board. What they want:
- The headline: did we get breached, how bad, what's the impact, when can we go back to business.
- Plain English. No jargon. No tool names unless absolutely necessary.
- Risk framing. Financial impact estimate. Regulatory exposure.
- A clear recommendation set with owners and timelines.
- Confidence levels for the major findings.

Reading time: 5 minutes. Executive summary is what they actually read. The rest is delegated to the CIO/CISO.

**2. Technical team.** CIO, CISO, IT leadership, sometimes the SOC team. What they want:
- The complete attack chain.
- Per-host findings.
- IOC list they can ingest into their EDR / SIEM.
- Remediation actions they can execute.
- Detection gaps they can close.

Reading time: 1–3 hours. They read the whole technical body. They use the IOCs to hunt for residual compromise.

**3. Legal / insurance.** General counsel, outside counsel (breach coach), insurance carrier loss adjuster. What they want:
- Defensible findings with evidence trail.
- Chain of custody documentation.
- Specific facts that trigger or don't trigger regulatory notification obligations.
- Confidence levels — the lawyer needs to know what's "confirmed" vs. "suspected."
- A "what data was exposed" determination (drives notification scope under GDPR, state breach laws, HIPAA, etc.).
- A "what we did not examine" statement — important for liability framing.

Reading time: 2–4 hours, often paragraph by paragraph for the specific factual determinations they need.

**4. Regulatory.** The regulator may not see the IR report directly; they may see a summary or specific facts derived from it. But the IR report often gets filed (or excerpted) in:
- SEC 8-K Item 1.05 disclosure (since December 2023).
- HIPAA OCR breach notification (US).
- State AG breach notifications (US — 50 different requirements).
- GDPR Article 33 supervisory authority notification (EU — 72 hours).
- NIS2 Directive (EU — sector regulators).
- DORA (EU — financial services).
- CIRCIA reports (US — once final rules go into effect).
- Sector-specific filings: NERC CIP for utilities, FFIEC/FDIC/OCC for banks, etc.

The regulator wants: a clear chronology, specific facts about what data was affected, what was done in response.

**5. Public.** Sometimes the IR report (or excerpts) enters the public record — through a SEC filing, through a litigation document production, through a journalist's FOIA request, or through the customer's own press release. The report has to read well for an audience that doesn't trust the customer's framing.

### D.2 Report sections universal across templates

Despite stylistic variation, the same skeleton appears in nearly every senior IR consultant's report.

**Executive Summary.** 1 page maximum. Mandatory sections:
- What happened (1–2 sentences).
- Scope (which systems, when, how many users affected).
- Impact (data exposure, business disruption, financial estimate).
- Current status (contained, remediated, ongoing).
- Next steps (top 3–5 actions for leadership).

Usually written last, by the senior, in the senior's own voice.

**Engagement Overview.** Scope, timeline, stakeholders, methodology references.
- Scope statement: what was in scope, what was out of scope.
- Engagement timeline: when engaged, when evidence acquired, when findings communicated, when report delivered.
- Stakeholders: customer roles, IR firm roles, third parties involved.
- Privilege statement: usually attorney-client privileged through outside counsel.

**Methodology.** Tools used, evidence acquired, chain of custody.
- Tools used: KAPE 1.3.x, Volatility 3 v2.x, EZ Tools (specific versions), Wireshark x.x.x, Splunk Enterprise (customer-owned), VirusTotal Premium.
- Evidence acquired: per-host evidence inventory with hashes (SHA-256 of every image and triage zip), acquisition date/time, acquisition method, custody.
- Chain of custody: signed transfers, evidence locker numbers, custodial individuals.
- Methodology validation: references to industry standards (NIST SP 800-86, NIST SP 800-61, SANS PICERL, ENISA Good Practice Guide).

This section is critical for defensibility. Every tool and every method should be traceable to a documented procedure.

**Findings.** The meat of the report. Per-host, per-TTP, per-incident-element.

Each finding follows a consistent shape:
- Finding ID (e.g., FIND-001).
- Title (e.g., "Initial access via Fortinet VPN credential brute force").
- Severity (Critical / High / Medium / Low).
- Confidence (Confirmed / Highly Likely / Likely / Possible / Inconclusive).
- Affected systems.
- Affected users / accounts.
- Description (narrative — 1–3 paragraphs).
- Supporting evidence (specific artifacts with references).
- MITRE ATT&CK mapping (technique IDs).
- Recommended actions.

A representative report has 20–80 findings. Each finding is usually 0.5–2 pages.

**Timeline of Attack.** Chronological reconstruction. Often a table with columns: Timestamp (UTC), Source System, Event Description, Supporting Evidence Reference, Finding ID. Some reports use a narrative timeline; some use a Gantt-style visualization for parallel attacker actions.

**Indicators of Compromise (IOCs).** Tables of:
- File hashes (MD5, SHA-1, SHA-256).
- IP addresses (with ASN, geolocation, attribution).
- Domain names (with registration date, registrar, hosting).
- URLs.
- Email addresses (sender, sender domain).
- Registry keys (full path + value).
- File paths (the malware's drop locations).
- Mutex names.
- Yara rule hits.
- Certificate fingerprints (JA3, JA3S).
- User agent strings.

The IOC tables are exported in machine-readable formats (CSV, STIX 2.1 JSON, MISP feed, OpenIOC XML) for ingestion into the customer's tooling.

**Recommended Remediation.** Three time horizons:
- Immediate (0–7 days): containment validation, credential rotation, urgent patches.
- Short-term (7–90 days): rebuild compromised systems, deploy missing controls, close known gaps.
- Long-term (90+ days): strategic improvements — architecture changes, training, policy.

Each recommendation has: owner (customer role), priority, effort estimate (rough), dependencies.

**What We Did Not Examine.** Increasingly common section, especially in privileged reports. Explicit list of:
- Systems not in scope.
- Time periods not examined.
- Tools not run.
- Hypotheses considered but not pursued (with reasoning).

This section protects the IR firm by being explicit about scope limits and protects the customer by being explicit about what residual investigation might be warranted.

**Appendices.** Raw tool output, additional artifacts, full event log excerpts, detailed methodology references, IOC export formats.

### D.3 Real template breakdowns

Sources for these templates are publicly available (NIST, ENISA, FIRST.org) or describable from public examples (Mandiant's M-Trends format, Verizon DBIR format).

**Template 1 — Mandiant M-Trends style.**

Mandiant's annual M-Trends report (and by extension, Mandiant individual-engagement reports follow a similar voice) is **narrative-heavy** with strong threat-actor attribution. Characteristics:
- Each finding is told as a story — "the attacker did X, then Y, then Z, leading to outcome A."
- Threat actor naming is prominent (UNC#### tracker numbers; named groups like APT29, FIN7, UNC4393).
- TTPs are mapped to MITRE ATT&CK explicitly with technique IDs.
- Dwell time is highlighted prominently.
- Visualizations: timeline diagrams, attack-chain flowcharts, geographic maps of victim distribution.

**Template 2 — CrowdStrike OverWatch / Threat Hunting style.**

CrowdStrike's threat-hunting reports (OverWatch is their managed hunting service) lean **detection-focused**:
- Each finding emphasizes "what behavior we observed" rather than "what tool we used."
- TTPs are tightly mapped to Falcon EDR's own detection categories.
- IOCs are heavily curated and ranked.
- Adversary attribution is prominent (the "[X] Spider" / "[X] Panda" naming).

**Template 3 — SANS GIAC GCFA / GCFR practical report style.**

SANS GIAC practical exam reports (e.g., the FOR508 / FOR526 / GCFR practical assignments) are **pedagogical and methodology-explicit**. Characteristics:
- Detailed walkthrough of methodology — every step described as if the reader is learning.
- Tool commands quoted verbatim with their output.
- Confidence levels and alternative hypotheses discussed.
- Explicit references to course material (ATT&CK techniques, MITRE D3FEND, NIST SP 800-61).

The SANS practical style influences how many GIAC-certified senior consultants write their professional reports.

**Template 4 — Verizon DBIR style.**

Verizon's Data Breach Investigations Report is **pattern-clustering across many cases** rather than a single-incident report. But the DBIR vocabulary (VERIS framework) heavily influences how individual reports are written:
- "Action" (what the attacker did).
- "Asset" (what was affected).
- "Attribute" (CIA triad — confidentiality, integrity, availability).
- "Actor" (who did it).
- "4 A's" framework: Actor, Action, Asset, Attribute.

Many IR consultants use the VERIS taxonomy in their findings even without naming it.

**Template 5 — Stroz Friedberg / Aon style.**

Stroz Friedberg's reports lean **courtroom-ready** — designed to be admissible as expert evidence. Characteristics:
- Heavy chain-of-custody documentation.
- Explicit methodology validation against industry standards.
- Conservative confidence language.
- Sworn affidavit attached for litigation engagements.
- CV of the examiner attached.

**Template 6 — NIST SP 800-61 Annex A.**

NIST's SP 800-61 rev 2 (Computer Security Incident Handling Guide) Annex A provides government-issue incident report skeleton. Characteristics:
- Highly structured field-based format.
- Specific fields for: incident identifier, contact information, incident summary, incident type (DoS, malicious code, unauthorized access, inappropriate usage, multiple component), timeline, sources, technical details, impact.
- Used by federal agencies under FISMA and by US-CERT.

Many regulated-industry reports inherit this skeleton even when not strictly government.

**Template 7 — ENISA Good Practice Guide for IR Reporting.**

ENISA's Good Practice Guide ("Good Practice Guide for Incident Management") and related ENISA reports provide an EU-flavored template. Characteristics:
- Strong GDPR alignment — explicit sections on data subject impact.
- 72-hour notification framing.
- NIS2 and DORA alignment for sector-specific reports.

**Template 8 — FIRST.org IR / CSIRT templates.**

FIRST (the Forum of Incident Response and Security Teams) publishes templates for CSIRT-to-CSIRT communication. Less of a customer-deliverable shape and more of an inter-CSIRT information-sharing shape. Notable for TLP (Traffic Light Protocol) labeling and standardized IOC sharing.

**Template 9 — The DFIR Report (public)**

The DFIR Report (thedfirreport.com) publishes public, anonymized incident write-ups. Their format has become an informal industry standard for "how a technical IR report should read":
- Case ID + summary.
- Timeline.
- Initial Access → Execution → Persistence → Privilege Escalation → Defense Evasion → Credential Access → Discovery → Lateral Movement → Collection → Command and Control → Exfiltration → Impact (the ATT&CK tactics, used as section headers).
- IOCs.
- Detection opportunities (Sigma rules).
- MITRE ATT&CK navigator layer.

Many IR consultants use The DFIR Report's structure as inspiration for the "Findings" section of their reports.

**Template 10 — Insurance-carrier-specific templates.**

Cyber insurance carriers often have their own preferred report formats. Carrier-specific sections:
- Coverage trigger mapping (which findings trigger which coverage parts).
- Forensic costs subtotal (used for sublimit calculations).
- Subrogation analysis (whether a third party — vendor, MSP — may share liability).
- Restoration scope (what's covered for restoration).
- Notification analysis (what regulatory notifications are triggered).

The carrier's preferred format often constrains the IR firm's narrative.

### D.4 Common report failure modes

Drawn from practitioner critiques (Brunty's primer, SANS' "Report Writing for Digital Forensics," various Brett Shavers and Harlan Carvey rants).

**1. Too long.** Death by appendix. Customer receives a 200-page document where the actionable content is on page 3. Common when the IR firm bills hourly and the junior padded the appendices.

**2. Too short.** A 5-page summary with no supporting evidence. Customer can't act on it; lawyer can't defend it.

**3. Jargon-dense executive summary.** "We observed lateral movement consistent with TTP T1021.002 leveraging compromised credentials of a privileged service account, resulting in DCSync activity against the krbtgt." The CEO has no idea what any of that means. The fix: write the executive summary for a 12-year-old.

**4. No chain of custody.** Findings are described but the evidence trail isn't. If the case goes to litigation, the report can't be authenticated as the source of the facts.

**5. Confidence overclaim.** Saying "the attacker did X" when the evidence only supports "X appears to have occurred, consistent with attacker behavior, although [alternative hypothesis] cannot be ruled out." Senior consultants discipline their language; junior-drafted reports often don't.

**6. Confidence underclaim.** Hedging everything to the point of uselessness. "We observed activity that may or may not be malicious; further investigation may be warranted." The customer needs the consultant to make a call.

**7. Missing remediation.** Findings without actions. The customer doesn't know what to do.

**8. Wrong audience-targeting.** Writing the executive summary for the SOC team. Writing the technical body for the CEO.

**9. Missing "what we did not examine."** Implicit overclaim — the report reads as if it covered the entire environment when it didn't.

**10. Tool output cut-and-paste.** Pages of raw Volatility output or EZ Tools CSV pasted into the report body. Should be in the appendix at most. Often a junior-draft pattern that the senior didn't catch.

**11. Inconsistent finding format.** Findings vary in shape — some have severity, some don't; some have confidence, some don't; some have MITRE mapping, some don't. The reader can't compare findings.

**12. Hashes that don't match.** Critical failure. A hash listed in the IOC table doesn't match the hash referenced in a finding. Either typo (low severity) or evidence corruption (high severity). Either way, undermines the report.

### D.5 The handoff moment

When is a report "ready"?

Three tests senior consultants apply:

1. **The customer can act.** Every finding has a recommendation. Every recommendation has an owner and a priority. The customer doesn't need to ask "so what do we do?"
2. **The lawyer can defend.** Every claim is supported by referenced evidence. The methodology is documented. Chain of custody is intact. The findings are explainable to a non-technical jury.
3. **The executive can decide.** The executive summary tells them what they need to know in 5 minutes. The risks are quantified. The recommendations are prioritized.

If all three are true, the report ships. If any is missing, it gets revised.

**Sign-off cascade:** the senior signs (often literally — many reports include a signed examiner declaration), the director countersigns, the firm's quality reviewer signs off, the breach coach reviews for privilege and disclosure framing, the customer's CISO/GC signs off on accuracy. Then it goes to the customer's leadership.

### D.6 Three artifacts at three stages

Most engagements produce **three distinct written artifacts**:

**1. Preliminary findings memo.** 1–3 pages. Delivered within 24–48 hours. What we have so far. Not a polished report. Often informal — sent as a Word document or even an email body. Privileged.

**2. Detailed final report.** 30–80 pages. Delivered 2–6 weeks after engagement start. The deliverable described above. Privileged.

**3. Incident write-up / lessons-learned document.** 5–15 pages. Sometimes shared internally (firm-side) or with the customer's broader security team for awareness. Often anonymized and published (with customer permission) for thought leadership. Sometimes contributed to ISAC / threat intel sharing.

These three artifacts have different voices, different audiences, different defensibility bars. A wedge that produces "the report" should be clear about which artifact it's producing.

### D.7 Where AI fits today

Per Brett Shavers' framing: "AI is good at exactly summarizing, clustering, speeding up review, and drafting." Mapped to report-writing:

**Summarizing:** generating the executive summary from the body of findings; condensing a 60-page report to a 1-page memo for the CFO; pulling key facts for the legal team's review.

**Clustering:** grouping related findings; identifying the dominant attack pattern; mapping individual artifacts to the MITRE ATT&CK matrix; generating the IOC tables.

**Speeding up review:** initial pass through tool output to surface high-priority items; cross-referencing findings against other findings for consistency; flagging confidence overclaims.

**Drafting:** the first draft of any narrative section. Methodology sections from a tool list. Recommendations from a findings list. Methodology sections from a tool inventory.

**What AI is bad at, currently:**

- Defensibility judgment (whether a finding will survive cross-examination).
- Confidence calibration in context (knowing when "highly likely" overclaims vs. underclaims).
- Customer-relationship-aware framing (how to phrase a finding for THIS specific customer's leadership).
- Live Q&A in stakeholder briefings.
- Knowing what to leave OUT of the report.

### D.8 The IOC export side

IOCs from the report often need to be exported in machine-readable format for downstream tooling.

**Formats:**

- **STIX 2.1** (Structured Threat Information eXpression). JSON-based. The OASIS standard. Used by most modern Threat Intelligence Platforms (TIPs). Has objects for Indicator, Observed-Data, Threat-Actor, Attack-Pattern, Course-of-Action, etc.
- **OpenIOC** (Mandiant-originated XML format). Older, still in some tools.
- **MISP feed** (CSV or JSON). MISP is open-source TIP with broad community adoption.
- **Plain CSV** with columns: indicator-type, value, first-seen, last-seen, confidence, severity, context.
- **YARA rules** for binary indicators (file content patterns).
- **Sigma rules** for log-pattern detection (cross-SIEM).
- **MITRE ATT&CK Navigator layer JSON** for visualization of observed TTPs.

The senior often hand-curates these (especially STIX) because automated exports tend to include too much (every indicator) when the customer wants only the high-confidence subset.

**Common downstream destinations:**
- Customer's EDR (CrowdStrike Falcon, SentinelOne, Microsoft Defender for Endpoint, Carbon Black).
- Customer's SIEM (Splunk, Sentinel, Elastic, QRadar).
- Customer's TIP (MISP, Anomali, Recorded Future).
- ISAC sharing (sector-specific — FS-ISAC for financial, H-ISAC for health, Manufacturing-ISAC, etc.).
- CISA / national CERTs (US-CERT, EU-CERT, JPCERT).

### D.9 Threat intel handoff

The "threat intel handoff" is a distinct deliverable that sometimes accompanies the IR report.

- **TLP-labeled IOC bundle** (TLP:CLEAR, TLP:GREEN, TLP:AMBER, TLP:RED, TLP:AMBER+STRICT).
- **Threat actor profile** (if attribution was attempted) — TTPs, infrastructure patterns, target verticals.
- **Sigma rules** for log detection of the observed TTPs.
- **YARA rules** for binary detection.
- **Detection opportunities document** — for the customer's SOC to implement.
- **Hunt queries** — Splunk SPL, Sentinel KQL, Falcon Event Stream queries, Elastic ES|QL.

This handoff sometimes goes back to the firm's own threat intel team (which feeds the next M-Trends-style annual report) and sometimes to the customer's TIP.

---

## Part E — Customer / Stakeholder Communication Patterns

The IR consultant's report is one artifact in a much larger communication flow. Understanding the surrounding communications is necessary because the report inherits framing constraints from them.

### E.1 CIO/CISO briefing

**What they want:**
- The technical truth, framed for someone who already speaks the language.
- A defensible recommendation set they can take to their CEO and the Board.
- Detection gaps in their own environment they can close.
- A reason to trust the IR firm with the next engagement.

**What they don't want:**
- Embarrassing language that makes their team look incompetent.
- Recommendations that imply they should have known better.
- Hedging that prevents them from making a decision.

**Briefing format:** typically a 30–60 minute meeting at the end of the engagement, often with the IR firm's director joining the senior consultant. The CIO/CISO brings their own technical leads. There is a slide deck (10–20 slides) but the conversation drives the meeting.

**Key moments:**
- The CISO will ask: "could we have prevented this?" The senior must answer honestly without throwing the customer's team under the bus.
- The CISO will ask: "what's the residual risk?" The senior must give a calibrated answer.
- The CIO will ask: "when can I tell the CEO this is over?" The senior must give a defensible call.

### E.2 Legal / GC briefing

**What they want:**
- Specific factual findings they can rely on for regulatory determinations.
- Confidence language they can quote to outside counsel and to regulators.
- Privilege protection — the IR firm engaged under privilege, the report stays privileged.
- A clear statement of what the IR firm did and did not examine.
- An understanding of what evidence is preserved and for how long.

**What they don't want:**
- Speculation that exceeds the evidence.
- Forward-looking liability statements ("the customer should have prevented this").
- Language that compromises privilege.

**Briefing format:** typically with the breach coach attorney present. The breach coach drives much of the line of questioning. The senior consultant answers factually and lets the coach handle legal framing.

**Key moments:**
- The GC will ask: "what data was exposed?" — drives notification scope under state breach laws, GDPR, HIPAA, etc. The senior must give the most accurate answer possible while being explicit about limits ("we have evidence that X was accessed; we have not been able to determine whether Y was exfiltrated").
- The breach coach will ask: "is there a regulatory clock?" — answer determines whether 72-hour notification or 4-business-day SEC notification has started.
- The GC will ask: "would you testify to this?" — the senior must be honest.

### E.3 Insurance carrier briefing

**What they want:**
- Confirmed loss categories (forensic costs, business interruption, ransom payment if any, restoration, legal, notification, credit monitoring).
- Coverage trigger mapping — which policy provisions are engaged.
- Subrogation potential — was a third party (MSP, vendor, software supplier) at fault.
- Lessons-learned recommendations for the insured to reduce future claims.
- A clean report for their loss adjuster's claim file.

**What they don't want:**
- Findings that broaden the loss beyond the carrier's expectation.
- Findings that suggest the insured violated policy conditions (e.g., misrepresented their controls in the application).
- Language that triggers exclusions inadvertently.

**Briefing format:** depending on the carrier and claim size, can range from a 30-minute call with the loss adjuster to a formal claim review meeting with the carrier's senior leadership.

**Key moments:**
- The carrier will ask: "are the controls the insured represented in their application in place?" — this is the warranty / misrepresentation question. The senior must answer factually.
- The carrier will ask: "what's the total estimated loss?" — drives reserve setting.
- The carrier's outside counsel may ask about subrogation potential.

Cyber insurance drives a huge share of IR engagements. As of 2024–2026, the insurance carrier is often the one that picks the IR firm (from the panel) and pays the bill. The carrier's expectations shape the report format more than the customer's preferences do.

### E.4 Regulatory disclosure

The current (2024–2026) regulatory landscape requires the customer to disclose materially-impactful cybersecurity incidents in multiple jurisdictions.

**SEC 8-K Item 1.05** (since December 2023): US public companies must disclose material cybersecurity incidents within 4 business days of materiality determination. The IR report drives the materiality determination (with legal counsel's framing). The 8-K filing is typically 200–500 words, not a paste of the IR report — but the IR report's specific factual findings inform what gets disclosed.

**GDPR Article 33 / 34** (EU): the controller must notify the supervisory authority within 72 hours of becoming aware of a personal data breach. Article 34 requires notification to data subjects if there's a high risk to their rights. The IR report determines whether personal data was affected and the nature of the risk.

**State breach notification laws** (US — 50 different statutes): each state has its own timing, content, and triggering thresholds. California (CCPA), New York (SHIELD Act), Massachusetts (201 CMR 17), Texas, etc. The IR report's findings about what data was accessed/exfiltrated determines notification scope per state.

**HIPAA Breach Notification Rule** (US healthcare): notification to OCR (Department of Health and Human Services Office for Civil Rights), to affected individuals, and (if >500 individuals) to media. The IR report's findings about PHI exposure drive the determination.

**NIS2 Directive** (EU, applicable 2024 onward): sector-specific notification to national CSIRTs / competent authorities. Early warning within 24 hours, incident notification within 72 hours, final report within 1 month.

**DORA** (EU financial services, applicable January 2025): incident classification and reporting to financial regulators.

**CIRCIA** (US — Cyber Incident Reporting for Critical Infrastructure Act): when the implementing rule is final (CISA published proposed rule in 2024), covered entities must report covered cyber incidents to CISA within 72 hours and ransom payments within 24 hours.

**Sector-specific:** NERC CIP for power utilities, FFIEC for banks, FINRA for broker-dealers, FAA for aviation, FCC for telecom.

The IR consultant's role: provide the **specific factual findings** that the customer's legal team uses to assess each notification obligation. The IR consultant is generally NOT the one who decides whether to notify; the customer's GC and outside counsel decide. But the IR consultant's findings are the predicate.

### E.5 Customer / public communications

If the incident becomes public (through SEC disclosure, customer press release, media leak, ransomware actor's leak site), the customer engages PR and crisis communications.

**The customer's PR firm asks the IR firm for:**
- "Approved facts" — specific findings the customer can publicly say.
- "Holding statements" — language the customer can use in a press release that's accurate but doesn't overcommit.
- Q&A prep for executives — likely media questions and defensible answers.

**The IR consultant generally does NOT speak to media directly.** The firm's policy is that all media questions go through the customer's PR or the firm's own communications office. But the IR consultant's findings drive what the customer can credibly say.

**Common public communications artifacts:**
- Press release (the customer's initial statement).
- FAQ document for customers/employees.
- Notification letter to affected individuals (mandated by state laws).
- Website notice (mandated in some jurisdictions).
- Class-action complaint defense statement (if litigation follows).

The "story" the customer tells publicly is constrained by the IR consultant's specific factual findings. Overclaiming in public (e.g., "no data was stolen" when the IR report says "we could not determine whether data was exfiltrated") creates legal exposure.

---

## Part F — Validation From Practitioner Voices

This section quotes real practitioners with citations. Sources include blogs, podcasts, conference talks, recent r/computerforensics threads (sourced via SERP snippets where direct Reddit access was blocked during research). The themes the practitioners articulate validate the wedge.

### F.1 The report-writing pain

> "It's easy to use a documentation system before you begin working a case. It's impossible to start one after your case is done."
> — Brett Shavers, quoted in Josh Brunty's *Writing DFIR Reports: A Primer*, joshbrunty.github.io/2021/01/27/reporting.html

> "A process that should have taken a few weeks took months and hours of fruitless searches… everything should be distilled down to make sense to 'your 80 year old grandmother.'"
> — Josh Brunty, *Writing DFIR Reports: A Primer*

> "Explaining certain forensic terminology in a non-technical manner can be difficult even for the most seasoned examiner."
> — SANS Blog, *Report Writing for Digital Forensics Part II*, sans.org/blog/report-writing-for-digital-forensics-part-ii

> "The deliverable IS the analysis from the customer's perspective. The investigative work that produced it is invisible to them. The hours of brilliant analysis show up as a 30-page Word document. If the document is bad, the customer thinks the analysis was bad."
> — William Oettinger, LinkedIn essay (paraphrased from his frequent posts on DFIR report quality).

> "I have seen reports from very expensive firms that read like a Volatility output dump. The customer pays $400/hour and receives a CSV with comments. That's not a deliverable, that's a receipt."
> — anonymous senior IR consultant quoted in Forensic Focus podcast *DFIR in 2025 — AI, Smart Devices and Investigator Well-Being*.

### F.2 The command-line stenography pain

> "Defensive OODA loops are measured in hours while offensive loops are now measured in seconds. We've trained analysts to be command-line stenographers instead of investigators."
> — Rob T. Lee, *Introducing Protocol SIFT*, robtlee73.substack.com.

> "Today, an adversary can move from initial intrusion to full domain admin in just 8 minutes. Responders face immense pressure to analyze massive volumes of memory captures, log streams, endpoint artifacts, and cloud telemetry at scale."
> — SANS, *Protocol SIFT: An Experimental Research Initiative for AI-Assisted DFIR*.

> "Two-thirds of an investigation is typing commands. The actual judgment moments — when you realize what the artifact means — are 30 minutes out of 8 hours."
> — paraphrased from Brett Shavers' "Tool Operators vs. Investigators" framing in *Raising the Bar*, brettshavers.com.

> "Plenty of practitioners can operate tools, generate timelines, and produce reports that look professional while still being a liability to the case."
> — DFIR Training editorial, dfir.training/blog/a-word-on-dfir-credentials.

> "Tools do not equal analytical knowledge."
> — Tony Knutson, SANS DFIR Summit 2025 keynote, recapped at sans.org/blog/2025-sans-dfir-summit-recap-human-element.

### F.3 What they wish AI did

> "AI is good at summarizing, clustering, speeding up review, and drafting."
> — Brett Shavers, *Why AI Will Replace Every DFIR Tool Operator by 2027*, brettshavers.com.

> "If we had a tool that could take my case notes and produce the first draft of the executive summary, I would buy it tomorrow. I would buy it twice."
> — paraphrased senior IR consultant in Magnet Cache Up podcast, Q4 2024.

> "AI handles volume and pattern. Investigators make judgment calls. The right division is: AI does the volume, the human does the judgment, and the report attributes every claim to the underlying evidence."
> — Magnet Forensics blog, paraphrased from *Evaluating the use of AI in digital evidence and courtroom admissibility*, magnetforensics.com.

> "What I want is an associate. Someone who runs the tools I tell them to run, organizes the output, drafts the boring parts of the report, and asks me intelligent questions when something is ambiguous. I do not want an oracle that tells me what happened."
> — paraphrased from a r/computerforensics top-of-2024 thread sourced via SERP snippets.

### F.4 What they distrust about AI tools

> "AI accelerates confident mistakes… It can't be accountable… What it can't do is reliably decide what artefacts mean in context, or whether the story it is telling matches the evidence at all."
> — Brett Shavers, *Why AI Will Replace Every DFIR Tool Operator by 2027*.

> "In forensics, fabricated evidence isn't just unhelpful but potentially career-ending and legally catastrophic."
> — Rob T. Lee, Protocol SIFT substack.

> "If sources such as these, which are very often incomplete and ambiguous… are what constitutes the 'training set' for an AI/LLM, then where is that going to leave us when the output of these models is incorrect? And at this point, I'm not even talking about hallucinations, just models being trained with incorrect information."
> — Harlan Carvey, windowsir.blogspot.com/2025/02/the-role-of-ai-in-dfir.html.

> "If an AI-enabled tool does not disclose how it came to a result in the way an end user can explain in court, the use of that tool may be inadmissible in legal proceedings."
> — Magnet Forensics, *Evaluating the use of AI in digital evidence and courtroom admissibility*.

> "What [AI] can't do is reliably decide what artefacts mean in context, or whether the story it is telling matches the evidence at all… It cannot properly weigh up competing explanations, spot when something does not quite fit, or decide how much confidence to place in a conclusion when the evidence is messy."
> — Pen Test Partners, pentestpartners.com.

> "Any digital forensic examiner worth their salt would verify and validate the findings, as forensic tools' image categorization features are not always 100% accurate."
> — ACEDS, *Digital Forensics: The Good, the Bad, and the AI-Generated*, aceds.org.

> "I do not want an AI that learns. I want one that is predictable, deterministic, and explainable in court. If it 'gets better over time,' it also gets harder to validate."
> — paraphrased from a Lesley Carhart tisiphone.net post on AI in OT IR.

### F.5 What the field's senior voices have said about the workflow

**Dan Pullega (Mandiant, now Google Cloud):**

In conference talks and blog posts, Pullega has emphasized that "the timeline is the deliverable, not the appendix." The senior consultant's value is in producing a chronologically coherent attack narrative; the artifacts are inputs. He has spoken about the manual labor of timeline construction at multiple SANS DFIR Summit events.

**Mari DeGrazia (Hexordia):**

DeGrazia's articles and conference talks repeatedly emphasize **methodology validation** — every tool used should be tested against a known data set, with the test results documented. This connects directly to the "defensibility" thread: a finding is only as defensible as the method that produced it.

**Harlan Carvey:**

Carvey's blog and books emphasize the **context-dependent meaning of artifacts**. An AmCache entry for `C:\Users\Public\update.exe` means one thing in one customer environment and a different thing in another. The senior's judgment is in the contextual interpretation. AI's struggle is precisely here.

**Lesley Carhart (Dragos):**

In her tisiphone.net posts, Carhart has emphasized the **human-relationship dimension** of IR: the customer's panic, the politics inside the customer's organization, the trust the IR firm needs to build. AI can't do this part, and trying to do it badly damages the engagement.

**Brett Shavers (Hexordia):**

The most-cited senior voice on AI in DFIR. His framing — "AI replaces tool operators, not investigators" — captures the current consensus. His "AI is good at summarizing, clustering, speeding up review, and drafting" framing is exactly the report-writing wedge.

**Brian Carrier (Sleuth Kit Labs / Cyber Triage):**

Carrier's 7-principle AI doctrine for Cyber Triage:
1. AI is a tool, not a substitute for analyst judgment.
2. Outputs must be reproducible.
3. Outputs must be explainable.
4. Non-determinism must be disclosed.
5. Source data is the ground truth.
6. Verify generative AI by cross-checking against source evidence.
7. AI should attempt to both refute and support its hypotheses.

This doctrine is the **closest public articulation of what a defensible AI-assisted IR workflow looks like.** The hypothesis-first wedge in `STRATEGY.md` resonates with principle 7 in particular.

### F.6 r/computerforensics sentiment (sourced via SERP snippets)

Direct Reddit access was blocked during research (Reddit blocks WebFetch + niche subreddits are poorly indexed by SERPs), but search-engine snippets of top-of-2024 and 2025 threads on r/computerforensics surface the following themes:

- **"My biggest pain is writing reports"** appears in multiple posts, top-voted, with junior consultants asking how to get faster and senior consultants confirming "it never gets less painful, just less slow."
- **"How do you organize case notes?"** is a recurring question. Tools mentioned: Obsidian, OneNote, Notion, plain Markdown, CherryTree, custom Word templates. No standard exists.
- **"What's the right way to handle confidence in findings?"** — debate about hedging language vs. assertive language. Consensus: be specific about evidence base, conservative about claims that can't be supported.
- **"My boss asked me to use ChatGPT for report drafting"** — mixed responses. Some say it works for the appendix and methodology sections; some warn about confidentiality risk; some warn about hallucination.
- **"How do you bill report-writing time?"** — practitioners commonly note that report-writing is full-rate billable but feels less "valuable" than analysis time. There's discussion about firms that try to underbill report-writing and the friction it creates with juniors.

### F.7 Common misconceptions practitioners want to correct

When senior practitioners are asked what outsiders (vendors, marketers, junior practitioners) get wrong, common themes:

**1. "AI hallucination is the problem."** Not quite. The problem is that AI **interprets** artifacts incorrectly even when not hallucinating. An artifact-cited finding can still be wrong about what the artifact means. (Carvey, Shavers, Pen Test Partners.)

**2. "Speed is the problem."** Speed matters, but not as much as defensibility. A 14-minute report that doesn't survive cross-examination is worse than a 4-hour report that does. (Rob T. Lee himself has nodded to this in his framing of Protocol SIFT.)

**3. "The investigation IS the deliverable."** No — the **report** is the deliverable. The investigation produces facts; the report produces understanding. Confusing the two leads to investigations that produce great evidence and bad reports.

**4. "Junior analysts can be replaced by AI."** Mixed view. Junior tool-operators may be at risk. Junior judgment-developers (the ones being trained to become senior consultants) are not — and replacing them eliminates the pipeline for the next generation of seniors.

**5. "Court-admissibility is just having an audit log."** No. Court-admissibility requires methodology validation, expert qualification, chain of custody, and the ability to explain HOW the conclusion was reached, not just THAT it was reached. An audit log helps but is not sufficient.

### F.8 What practitioners say in private

The public discourse on AI in DFIR is more measured than the private conversations. Private themes from podcasts, panel discussions, and Slack/Discord channels:

- **Excitement** about AI doing the boring parts. Most seniors want to do less of the mechanical work.
- **Anxiety** about juniors being replaced before they develop into seniors — and the long-term skill pipeline collapsing.
- **Frustration** with vendors over-promising on AI features that don't survive real cases.
- **Cautious optimism** about AI as a "co-pilot" or "junior associate" model — where the AI does the work the senior tells it to do, and the senior reviews.
- **Skepticism** about fully-autonomous AI investigators. "I am not going to bet my reputation on a model I don't understand."
- **Anger** at AI tools that don't show their work. The "black box" framing is the most-cited deal-breaker.

### F.9 The wedge in the practitioner's own words

The wedge in `STRATEGY.md` ("hypothesis-first IR investigator that drafts its own structured incident report as the case unfolds, with every claim verifiably linked to the tool execution that produced it") can be re-spoken in the practitioner's vocabulary:

- "An associate that runs the tools you'd run, in the order you'd run them, and writes the first draft of the report while doing it."
- "AI as the L1 you actually want — not because it's a replacement, but because it does the boring half and asks you about the interesting half."
- "Something that turns 8 hours of command-line stenography + 4 hours of report drafting into 2 hours of analyst-led directing + 30 minutes of report polishing."
- "An audit trail that's actually defensible — every claim in the report shows you the command that produced the evidence."

The wedge speaks in their language without using either the over-claimed lane ("we prevent hallucinations!") or the under-recognized lane ("we automate everything!").

---

## Sources

### Primary IR / DFIR practitioner sources

- Brett Shavers, *Raising the Bar: Establishing a Common Baseline in DFIR*, brettshavers.com/brett-s-blog/entry/raising-the-bar-establishing-a-common-baseline-in-dfir
- Brett Shavers, *Why AI Will Replace Every DFIR Tool Operator by 2027*, brettshavers.com (full title varies in the cited blog post)
- Harlan Carvey, *The Role of AI in DFIR*, windowsir.blogspot.com/2025/02/the-role-of-ai-in-dfir.html
- Harlan Carvey, *Windows IR Blog*, windowsir.blogspot.com
- Mari DeGrazia, articles4n6.com (and Hexordia content at hexordia.com)
- Lesley Carhart, tisiphone.net
- Josh Brunty, *Writing DFIR Reports: A Primer*, joshbrunty.github.io/2021/01/27/reporting.html
- DFIR Training, *A Word on DFIR Credentials*, dfir.training/blog/a-word-on-dfir-credentials
- William Oettinger, LinkedIn essays on DFIR report writing (search "Oettinger DFIR report writing").

### Annual industry reports

- Mandiant, *M-Trends 2024* and *M-Trends 2025*, mandiant.com/m-trends
- CrowdStrike, *2024 Global Threat Report* and *2025 Global Threat Report*, crowdstrike.com/global-threat-report
- Verizon, *2024 Data Breach Investigations Report* and *2025 DBIR*, verizon.com/business/resources/reports/dbir
- Palo Alto Unit 42, *Incident Response Report* (annual), unit42.paloaltonetworks.com
- Sophos, *Active Adversary Report* (semi-annual), news.sophos.com/active-adversary-report
- IBM / Ponemon, *Cost of a Data Breach Report* (annual), ibm.com/security/data-breach
- ENISA, *Threat Landscape* (annual), enisa.europa.eu/topics/threat-risk-management/threats-and-trends

### Standards and templates

- NIST SP 800-61 rev. 2, *Computer Security Incident Handling Guide*, nvlpubs.nist.gov
- NIST SP 800-86, *Guide to Integrating Forensic Techniques into Incident Response*
- NIST SP 800-184, *Guide for Cybersecurity Event Recovery*
- ENISA, *Good Practice Guide for Incident Management*, enisa.europa.eu
- ENISA, *Reference Incident Classification Taxonomy*
- FIRST.org, *CSIRT Services Framework* + IR templates, first.org
- VERIS Framework (Verizon), veriscommunity.net
- MITRE ATT&CK Framework, attack.mitre.org
- MITRE D3FEND Framework, d3fend.mitre.org

### Legal landscape

- Federal Rule of Evidence 707 (Judicial Conference 2025; AI-generated evidence)
- Federal Rule of Evidence 702 (Expert testimony; Daubert successor)
- *Daubert v. Merrell Dow Pharmaceuticals* (1993)
- SEC Final Rule, *Cybersecurity Risk Management, Strategy, Governance, and Incident Disclosure* (effective December 2023)
- GDPR Articles 33 and 34 (EU)
- NIS2 Directive (EU 2022/2555)
- DORA Regulation (EU 2022/2554)
- CIRCIA (Cyber Incident Reporting for Critical Infrastructure Act, US 2022)
- Magnet Forensics, *Evaluating the use of AI in digital evidence and courtroom admissibility*, magnetforensics.com

### Conference talks and proceedings

- SANS DFIR Summit 2024 and 2025 (recaps at sans.org/blog/)
- SANS DFIR Summit 2025 recap "The Human Element", sans.org/blog/2025-sans-dfir-summit-recap-human-element
- Magnet Virtual Summit 2024 and 2025
- OSDFCon (Open Source Digital Forensics Conference) recent proceedings, osdfcon.org
- DFRWS USA and DFRWS EU (academic + practitioner), dfrws.org
- BSides DFIR-track sessions (regional, varies)
- BlueTeamCon proceedings, blueteamcon.com

### Vendor / firm references

- AppliedIR / Valhuntir reference architecture, github.com/AppliedIR/Valhuntir
- Sleuth Kit Labs / Cyber Triage AI principles, cybertriage.com
- Mandiant publications, cloud.google.com/security/resources
- CrowdStrike OverWatch reports
- Volexity blog (volexity.com)
- The DFIR Report (thedfirreport.com) — public IR write-ups

### Tools (canonical references)

- KAPE (Kroll Artifact Parser and Extractor), kroll.com/kape and ericzimmerman.github.io
- Eric Zimmerman's tools, ericzimmerman.github.io
- Volatility 3, volatilityfoundation.org
- The Sleuth Kit / Autopsy, sleuthkit.org
- Plaso / log2timeline, plaso.readthedocs.io
- Hayabusa, github.com/Yamato-Security/hayabusa
- Chainsaw, github.com/WithSecureLabs/chainsaw
- RegRipper, github.com/keydet89/RegRipper3.0
- Velociraptor, docs.velociraptor.app
- Wireshark, wireshark.org
- Zeek, zeek.org
- bulk_extractor, forensicswiki.xyz/page/Bulk_Extractor
- YARA + capa, virustotal.github.io / github.com/mandiant/capa

### Academic and peer-reviewed sources

- Sayakkara, A. P. & Le-Khac, N.-A. (2023). *ChatGPT for Digital Forensic Investigation: The Good, the Bad, and the Unknown*. Forensic Science International: Digital Investigation.
- arXiv 2504.02963, *Digital Forensics in the Age of Large Language Models* (2025 survey).
- arXiv 2601.06048, *Reliability and Admissibility of AI-Generated Forensic Evidence*.

### Books

- Luttgens, Jason; Pepe, Matthew; Mandia, Kevin. *Incident Response & Computer Forensics, 3rd Ed.* McGraw-Hill.
- Carvey, Harlan. *Practical Windows Forensics*. Multiple editions.
- Carrier, Brian. *File System Forensic Analysis*. Addison-Wesley.
- Ligh, Case, Levy, Walters. *The Art of Memory Forensics*. Wiley.
- Sikorski, Michael; Honig, Andrew. *Practical Malware Analysis*. No Starch Press.

### Sources for Reddit content

Reddit (r/computerforensics) content was sourced via SERP (Google, Bing) snippets and via cached threads cited in DFIR Diva and Forensic Focus aggregations. Direct Reddit access was blocked during research as noted in `research/protocol-sift-2026/.raw/06-user-pain-landscape.md`. Specific threads should be cross-referenced via title search if a downstream agent needs verbatim quotes.

### Cyber insurance landscape

- Marsh, *Cyber Insurance Market Trends* (annual), marsh.com
- Aon, *Cyber Resilience Report* (annual), aon.com
- Beazley, *Cyber Services Snapshot* (quarterly), beazley.com
- Coalition, *Cyber Claims Report* (annual), coalitioninc.com

---

**End of file.** Domain knowledge complete. Next file in the user-folder series, if needed, would be the deeper deliverable-format reference (sample report excerpts, sample IOC exports, sample executive summaries) — but the wedge does not require that level for design-phase decisions. The design-phase agent has enough here to know who the user is, what the user does, what the report has to look like, and what AI is and is not useful for in their workflow.
