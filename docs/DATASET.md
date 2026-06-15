# Evidence Dataset Documentation

## What the agent was tested against

The judged case: the official SANS **Find Evil!** *Standard Forensic Case* — **"The Fred Rocba
Case" (ROCBA)**. One Windows 10 host, provided as:

- a **~22 GB E01 disk image** (87 GB uncompressed; single NTFS volume, no partition table), and
- a **~5.3 GB compressed memory capture**.

The scenario (from the SANS briefing deck): Fred Rocba, a remote engineer at **Stark Research
Labs (SRL)**, is suspected of stealing R&D intellectual property over remote access during a
work-from-home period. The investigation is scored against the case's **5 Key Questions**:
which projects/accounts were accessed, what was taken, where it was transferred, how the actor
got in, and when.

## Source of the data

The SANS Find Evil! evidence share, distributed by the hackathon organizers (Rob Lee / SANS)
via the official Egnyte link on the Protocol SIFT channel. The ROCBA case is the primary judged
dataset. SilentWitness is **case-agnostic** — it also runs against public DFIR datasets
(NIST CFReDS "Hacking Case", Nitroba) used during development to validate the harness; ROCBA is
the proof case for the submission.

## What the agent found

On a full end-to-end run (`register-evidence → prepare → index → investigate`) against the real
ROCBA disk, the agent recalled **all 10** ground-truth findings keyed to the 5 Key Questions
(headline run, gpt-5.5 + the enforced coverage gate). Concretely, it identified:

- **Subject & accounts (Q1):** `fredr` / the SRL O365 identity (`frocba@stark-research-labs`),
  and the targeted privileged `BACKUPADMIN` account.
- **What was taken (Q2):** SRL R&D project files — LNK Recent-folder targets
  `SRL-Projects - Airwolf / Gunstar / Blue Thunder`, plus an `F:\Key Data` collection folder.
- **Where it went (Q3):** exfiltration channels — `G:\My Drive\…\Exported-PST\SRL-EMAIL-EXPORT`
  (Google Drive + PST email export), OneDrive, and Dropbox sync paths.
- **How (Q4):** RDP remote access (`LogonType=10`), a `4625` failed-logon brute force, and
  **SDelete** anti-forensic secure-deletion tooling.
- **When (Q5):** the intrusion window across 2020-11-10 → 2020-11-13.

Recall depends on the model and varies run-to-run (gpt-5.2: 30–50%; gpt-5.5: 100%); the full,
honest measurement — including the failure modes and what we catch — is in
[`ACCURACY_REPORT.md`](ACCURACY_REPORT.md), and the finding→tool-execution traceability is in
[`THREE_CLAIM_TRACE.md`](THREE_CLAIM_TRACE.md).

## Ground truth

The 10 expected findings live in `harness/ground_truth/rocba.handcrafted.json`, derived from the
SANS briefing deck (the scenario narrative) — **not** from the disk the agent reads — so the
recall measurement is non-circular. SANS ships no formal answer key with the training case.
