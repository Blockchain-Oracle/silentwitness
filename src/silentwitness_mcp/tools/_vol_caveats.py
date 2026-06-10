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
    "dlllist": (
        (
            "windows.dlllist walks the PEB InLoadOrderModuleList — "
            "reflectively-loaded DLLs (Cobalt Strike sRDI, Meterpreter, "
            "custom reflective loaders) are INVISIBLE here; corroborate "
            "with vol_malfind + ldrmodules"
        ),
        (
            "a system DLL name loaded from a non-standard path (e.g., "
            "ntdll.dll from C:\\Users\\Public\\) is a side-loading red "
            "flag"
        ),
        (
            "LoadTime is when the DLL entered the loader list — usable "
            "for per-process timeline reconstruction"
        ),
        (
            "suspicious-DLL detection requires a baseline of expected "
            "DLLs per process — without it, false-positive rate is high "
            "for anything more interesting than the system-DLL-from-"
            "wrong-path pattern"
        ),
    ),
    "handles": (
        (
            "cross-process handles (Process A → Process B) with "
            "PROCESS_VM_WRITE | PROCESS_CREATE_THREAD | "
            "PROCESS_ALL_ACCESS access are the injection prerequisites "
            "— flag these"
        ),
        (
            "a non-system process holding a handle to lsass.exe with "
            "PROCESS_VM_READ is the classic Mimikatz signature"
        ),
        (
            "mutex (Mutant) names are malware family fingerprints — "
            "many families use distinctive Global\\<random> names to "
            "prevent re-infection"
        ),
        (
            "handles to \\Device\\PhysicalMemory or unusual \\Device\\ "
            "paths are driver-IPC / rootkit candidates"
        ),
        (
            "file handles to deleted files persist while the handle is "
            "open — vol_dumpfiles can recover the content even after del"
        ),
    ),
    "lsadump": (
        # Ordered: Credential-Guard misconception correction FIRST
        # (action-shaping — distinguishes "empty output" interpretations),
        # then the operational caveats (DefaultPassword, $MACHINE.ACC,
        # _SC_<service>), then the technical preconditions, then the
        # field-citation contract.
        (
            "VBS / Credential Guard does NOT protect LSA secrets the same "
            "way it protects LSASS process memory — lsadump output is "
            "generally intact even on Credential Guard systems; do not "
            "assume empty output means the host is Credential-Guarded"
        ),
        (
            "DefaultPassword may contain auto-logon plaintext credentials "
            "— sensitive material, treat as Restricted in the report and "
            "the HMAC ledger"
        ),
        (
            "$MACHINE.ACC is the machine account password hash (NTLM) — "
            "usable for silver-ticket attacks; report as credential-"
            "rotation requirement"
        ),
        ("_SC_<service> contains passwords for services configured with non-default credentials"),
        (
            "windows.lsadump decrypts LSA secrets using the SysKey from "
            "the SYSTEM hive — requires both SYSTEM and SECURITY hives "
            "present in memory (true by default on a running system)"
        ),
        (
            "the Secret field is best-effort UTF-16LE decode — the "
            "authoritative bytes are in Hex; cite Hex when recording the "
            "observation"
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


class UnknownCaveatKeyError(ValueError):
    """Raised when ``caveats_for`` is called with a key not registered
    in :data:`_VOL_CAVEATS`. Inherits from :class:`ValueError` to match
    the :class:`UnknownToolError` precedent in
    :mod:`silentwitness_mcp.verification.normalizer` and so
    :func:`_run_wrapper`'s ``ValidationError | ValueError`` catch path
    surfaces it as ``OUTPUT_PARSE_FAILED`` if it ever leaks past the
    pre-spawn fail-fast check. A typo or rename-without-update would
    otherwise silently strip safety guidance from the audit row."""


def caveats_for(plugin_key: str) -> tuple[str, ...]:
    """Return the caveat tuple registered for ``plugin_key``.

    Raises :class:`UnknownCaveatKeyError` on unregistered keys so
    a wiring typo cannot ship findings with an empty caveat list."""
    try:
        return _VOL_CAVEATS[plugin_key]
    except KeyError as exc:
        raise UnknownCaveatKeyError(
            f"caveat_key={plugin_key!r} not in catalogue; known keys: {sorted(_VOL_CAVEATS)}"
        ) from exc


__all__ = ["UnknownCaveatKeyError", "caveats_for"]
