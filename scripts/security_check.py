#!/usr/bin/env python3
"""
security_check.py — Pre-Push & Release Security Gate for AlexandriaSandwich

Scans git tracked files or commit diffs for:
  1. Private IP addresses (192.168.*, 10.*, 172.16-31.*)
  2. Concrete personal user identifiers (e.g. marco@*, /Users/marco/*)
  3. Hardcoded API keys, tokens & secrets (Mistral keys, GitHub PATs, private keys)
  4. Forbidden files (.env, *.pem, *.key) tracked or staged in git

Usage:
  python3 scripts/security_check.py                 # scope=diff (commits since remote)
  python3 scripts/security_check.py --scope=all     # scan all tracked files in git
  python3 scripts/security_check.py --strict        # fail on any finding
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

ROOT = Path(__file__).resolve().parent.parent

# ── FORBIDDEN FILE PATTERNS (TRACKED IN GIT) ──────────────────────────────────
FORBIDDEN_FILE_PATTERNS = [
    r"^\.env$",
    r"^\.env\.(local|production|prod|stage)$",
    r".*\.pem$",
    r".*\.key$",
    r".*id_rsa.*",
]

# Files to ignore during content scan
IGNORE_FILES = {
    "security_check.py",  # Contains regex pattern definitions
    ".gitignore",
}

# ── PATTERN DEFINITIONS ───────────────────────────────────────────────────────
SECURITY_RULES: List[Dict[str, Any]] = [
    {
        "id": "PRIVATE_IPV4_192",
        "desc": "Private IP address (192.168.x.x)",
        "pattern": re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"),
        "severity": "ERROR",
    },
    {
        "id": "PRIVATE_IPV4_10",
        "desc": "Private IP address (10.x.x.x)",
        "pattern": re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        "severity": "ERROR",
    },
    {
        "id": "PRIVATE_IPV4_172",
        "desc": "Private IP address (172.16-31.x.x)",
        "pattern": re.compile(r"\b172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}\b"),
        "severity": "ERROR",
    },
    {
        "id": "PERSONAL_USER_SSH",
        "desc": "Personal username in SSH host target (e.g. marco@...)",
        "pattern": re.compile(r"\bmarco@[a-zA-Z0-9_\.-]+\b", re.IGNORECASE),
        "severity": "ERROR",
    },
    {
        "id": "PERSONAL_USER_PATH",
        "desc": "Personal local filesystem path (/Users/marco or /home/marco)",
        "pattern": re.compile(r"/(Users|home)/marco(/|\b)", re.IGNORECASE),
        "severity": "ERROR",
    },
    {
        "id": "API_KEY_MISTRAL",
        "desc": "Potential hardcoded Mistral API Key (32+ alphanum chars)",
        "pattern": re.compile(r"MISTRAL_API_KEY\s*=\s*['\"]?([a-zA-Z0-9]{32,})['\"]?"),
        "severity": "ERROR",
    },
    {
        "id": "GITHUB_PAT",
        "desc": "GitHub Personal Access Token",
        "pattern": re.compile(r"\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b"),
        "severity": "ERROR",
    },
    {
        "id": "PRIVATE_KEY_BLOCK",
        "desc": "Cryptographic Private Key block",
        "pattern": re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|PGP|PRIVATE) KEY"),
        "severity": "ERROR",
    },
]

# False positive exclusions (line-level)
ALLOWLIST_PATTERNS = [
    re.compile(r"\$\{MISTRAL_API_KEY"),
    re.compile(r"MISTRAL_API_KEY=\s*$"),
    re.compile(r"MISTRAL_API_KEY=\$\{"),
    re.compile(r"<deploy-user>"),
    re.compile(r"<nas-user>"),
    re.compile(r"\b127\.0\.0\.1\b"),
    re.compile(r"\b0\.0\.0\.0\b"),
]


def get_git_tracked_files() -> List[str]:
    """Return all tracked files in git."""
    res = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        return []
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def get_files_to_scan(scope: str) -> List[Path]:
    """Retrieve file list based on scope (diff or all) strictly within git."""
    if scope == "all":
        tracked = get_git_tracked_files()
        return [ROOT / f for f in tracked if Path(f).name not in IGNORE_FILES and (ROOT / f).is_file()]

    # scope == "diff": files changed between HEAD and upstream / origin/main
    upstream_ref = "origin/main"
    try:
        cmd = ["git", "rev-parse", "--abbrev-ref", "@{u}"]
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            upstream_ref = res.stdout.strip()
    except Exception:
        pass

    candidates = set()
    cmd = ["git", "diff", "--name-only", upstream_ref, "HEAD"]
    try:
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if line.strip():
                    candidates.add(line.strip())
        else:
            res_diff = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=ROOT, capture_output=True, text=True)
            for line in res_diff.stdout.splitlines():
                if line.strip():
                    candidates.add(line.strip())
    except Exception:
        pass

    # Also include staged uncommitted files
    try:
        res_staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT, capture_output=True, text=True)
        if res_staged.returncode == 0:
            for l in res_staged.stdout.splitlines():
                if l.strip():
                    candidates.add(l.strip())
    except Exception:
        pass

    results = []
    for rel in candidates:
        if Path(rel).name in IGNORE_FILES:
            continue
        p = ROOT / rel
        if p.is_file():
            results.append(p)
    return results


def check_forbidden_filenames(files: List[Path]) -> List[Tuple[str, str]]:
    """Check if any git-tracked files match strictly forbidden filename patterns."""
    findings = []
    for f in files:
        rel_str = str(f.relative_to(ROOT))
        for pat in FORBIDDEN_FILE_PATTERNS:
            if re.match(pat, rel_str) or re.match(pat, f.name):
                findings.append((rel_str, f"Forbidden file pattern tracked/staged in git: {pat}"))
    return findings


def scan_file_contents(file_path: Path) -> List[Dict[str, Any]]:
    """Scan file lines for security rule violations."""
    findings = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [{"line": 0, "rule": "READ_ERROR", "desc": str(e), "content": ""}]

    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        if any(allow.search(line) for allow in ALLOWLIST_PATTERNS):
            continue

        for rule in SECURITY_RULES:
            match = rule["pattern"].search(line)
            if match:
                findings.append({
                    "line": idx,
                    "rule": rule["id"],
                    "desc": rule["desc"],
                    "severity": rule["severity"],
                    "content": line.strip()[:140],
                    "matched": match.group(0),
                })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-push security & privacy scanner")
    parser.add_argument("--scope", choices=["diff", "all"], default="diff",
                        help="Scan mode: 'diff' (unpushed commits) or 'all' (all git tracked files)")
    parser.add_argument("--strict", action="store_true",
                        help="Treat any warning as fatal error")
    args = parser.parse_args()

    print(f"🔒 [security_check] Scanning repository (scope: {args.scope})...")
    files_to_scan = get_files_to_scan(args.scope)

    if not files_to_scan:
        print("   No modified git-tracked files to inspect. Security check PASSED.")
        return 0

    total_findings = 0
    forbidden_files = check_forbidden_filenames(files_to_scan)
    if forbidden_files:
        for fname, reason in forbidden_files:
            print(f"❌ [CRITICAL] {fname}: {reason}")
            total_findings += 1

    for f in files_to_scan:
        rel = f.relative_to(ROOT)
        findings = scan_file_contents(f)
        if findings:
            print(f"\n❌ [VIOLATION] In file: {rel}")
            for item in findings:
                total_findings += 1
                print(f"   Line {item['line']} [{item['rule']}]: {item['desc']}")
                print(f"   Snippet: {item['content']}")

    print("\n" + "─" * 60)
    if total_findings == 0:
        print(f"✅ [security_check] All checks passed ({len(files_to_scan)} files inspected).")
        return 0
    else:
        print(f"🚫 [security_check] FAILED: Found {total_findings} security violation(s).")
        print("   Please anonymize private IPs, personal usernames, and remove unmasked secrets.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
