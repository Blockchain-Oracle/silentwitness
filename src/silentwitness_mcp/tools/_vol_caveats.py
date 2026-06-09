"""Per-plugin caveat catalogue for the Vol3 memory family.

Each caveat is one ``ResponseEnvelope.caveats`` line. Ordering inside
each tuple matters: action-shaping (what the agent should DO) FIRST,
build-fragility / tamper / false-positive CYA SECOND, false-positive
allowlists LAST. Tests pin the action-shaping caveat at index 0.

Caveat text is quoted verbatim from ``context/domain/03`` so the
critic agent's challenge seeds and the entity gate's citation spans
both pick up the exact phrasing in the domain corpus."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

_VOL_CAVEATS: Final[Mapping[str, tuple[str, ...]]] = {
    "pslist": (
        (
            "windows.pslist walks PsActiveProcessHead — DKOM-hidden "
            "processes are invisible; corroborate with vol_psscan"
        ),
        ("ImageFileName is truncated to 15 chars; use vol_cmdline or vol_dlllist for full paths"),
        ("ExitTime may be set for processes still referenced by other handles (orphan teardown)"),
    ),
    "pstree": (
        ("Parent PIDs can refer to dead processes via PID reuse — cross-check CreateTime ordering"),
        (
            "Process hollowing produces legitimate-looking lineage with "
            "malicious code — vol_pstree alone cannot detect it; "
            "corroborate with vol_malfind + ldrmodules"
        ),
    ),
    "psscan": (
        (
            "windows.psscan may show terminated processes that pslist no "
            "longer sees — entries with ExitTime set are normal teardown "
            "artifacts, not malice"
        ),
        (
            "diff vs vol_pslist: processes in psscan but NOT in pslist "
            "are DKOM-hidden OR terminated; ExitTime distinguishes the two"
        ),
        (
            "pool-tag scan can produce false positives from non-process "
            "allocations — validate Threads/Handles plausibility before "
            "trusting an entry"
        ),
    ),
    "malfind": (
        (
            "RWX private memory with no mapped file is the classic injection "
            "pattern — but legitimate JIT engines (.NET CLR, Java JVM, "
            "V8/Node, Chromium) also allocate RWX; corroborate with "
            "vol_ldrmodules and process lineage before claiming injection"
        ),
        (
            "windows.malfind misses RX-only code (attacker VirtualProtect'd "
            "from RWX to RX post-write) and misses file-backed hollowed "
            "images (use vol_ldrmodules for hollowing detection)"
        ),
        (
            "hexdump_first_128 captures the first 128 bytes of the suspicious "
            "VAD — MZ + PE\\0\\0 pattern indicates a PE payload; lone "
            "0xE8/0xE9 + nop sled indicates shellcode"
        ),
    ),
    "cmdline": (
        (
            "windows.cmdline reads each process's PEB ProcessParameters — "
            "beats Sysmon EID 1 / Security 4688 when Sysmon was never "
            "deployed (the common reality on legacy hosts)"
        ),
        (
            "Command lines can be PEB-tamper-overwritten post-creation "
            "(RtlInitUnicodeString trick used by some Cobalt Strike "
            "profiles) — for tamper detection corroborate against "
            "ImageFileName lineage and vol_handles"
        ),
        (
            "long base64 strings in Args (encoded PowerShell) and "
            "rundll32 / regsvr32 / mshta / msbuild / installutil "
            "arguments are LOLBin red flags worth follow-up"
        ),
        (
            "PEB may be paged out — missing Args for paged-out PEBs is "
            "a smear artifact, not evidence of tampering; rerun with "
            "--single-swap-locations pagefile.sys if pagefile is available"
        ),
        (
            "System (PID 4), Registry, smss.exe, and some service-host "
            "processes have empty or null Args — this is normal, not "
            "malicious"
        ),
    ),
    "netscan": (
        (
            "windows.netscan pool-tag scan returns both active AND "
            "recently-closed endpoints — filter state to ESTABLISHED for "
            "live C2 evidence; TIME_WAIT / CLOSE_WAIT / FIN_WAIT_* are "
            "historical"
        ),
        (
            "windows.netscan is build-fragile on Windows 10/11 — symbol "
            "drift across builds can drop entries or surface artifacts; "
            "cross-check with vol_netstat when available"
        ),
        (
            "Owner process resolution requires the PID still being valid "
            "in pslist — owner may be blank for endpoints whose process "
            "has exited"
        ),
        (
            "LISTENING state on a non-loopback bind from a non-standard "
            "process is a backdoor candidate; LISTENING on loopback is "
            "normal IPC"
        ),
    ),
}


def caveats_for(plugin_key: str) -> tuple[str, ...]:
    """Return the caveat list for ``plugin_key`` or ``()`` if unknown.
    Tools that pass an unknown key get empty caveats — caller should
    have registered them first; a silent ``KeyError`` here would let
    a typo strip safety guidance from the audit row."""
    return _VOL_CAVEATS.get(plugin_key, ())


__all__ = ["caveats_for"]
