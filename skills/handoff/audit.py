#!/usr/bin/env python3
"""Mechanical audit of a handoff doc: staleness, broken references, secrets, poison.

Usage: audit.py path/to/handoff.md [--repo DIR ...] [--gh] [--today YYYY-MM-DD]

Checks
  - age of "Last updated YYYY-MM-DD"
  - size (words, lines)
  - commit SHAs in backticks exist in a --repo
  - "<ref> head ... <sha>" claims still match `git rev-parse <ref>`
  - ~/ and / paths in backticks exist; scripts/ files and doc mentions agree
  - #PR numbers: current state via `gh` (only with --gh, needs a --repo with a GitHub remote)
  - secrets (key/token patterns), instructions aimed at an AI, relative dates
Prints one line per finding: CRIT / HIGH / MED / INFO, then a summary. Exit 1 if any CRIT.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path

SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
    (r"\bgh[pousr]_[A-Za-z0-9]{30,}", "GitHub token"),
    (r"\bsk-[A-Za-z0-9_-]{20,}", "API secret key"),
    (r"\bxox[abpr]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"\b[a-z][a-z0-9+.-]*://[^\s:/@`]+:(?![<$*{\[]|x+@|\.\.\.)[^\s@/`]{3,}@", "credentials in URL"),  # skips <pw>, $PW, ***, {pw}
    (r"(?i)\b(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[`'\"]?[A-Za-z0-9/+_\-]{8,}", "inline secret value"),
]
POISON_PATTERNS = [
    r"(?i)ignore (all |any )?(previous|prior|above) (instructions|rules)",
    r"(?i)\byou (are|must) (now )?(an?|the) (ai|assistant|model)\b",
    r"(?i)do not (tell|inform|mention to) the user",
    r"(?i)\b(system prompt|developer message)\b",
    r"(?i)without (asking|confirmation|approval)",
]
RELATIVE_DATES = r"(?i)\b(yesterday|tomorrow|today|tonight|last (week|night|month)|next (week|month)|this (morning|week|afternoon))\b"


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("doc")
    ap.add_argument("--repo", action="append", default=[])
    ap.add_argument("--gh", action="store_true")
    ap.add_argument("--today")
    a = ap.parse_args()
    doc = Path(a.doc).expanduser().resolve()
    text = doc.read_text()
    lines = text.splitlines()
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    repos = [str(Path(r).expanduser().resolve()) for r in a.repo]
    out = []

    def add(sev, msg, ln=None):
        out.append((sev, f"{doc.name}:{ln}: {msg}" if ln else msg))

    # age + size
    m = re.search(r"(?i)last updated\s*\**\s*(\d{4}-\d{2}-\d{2})", text)
    if not m:
        add("HIGH", "no 'Last updated YYYY-MM-DD' line")
    else:
        age = (today - dt.date.fromisoformat(m.group(1))).days
        if age > 7:
            add("HIGH", f"last updated {age} days ago; treat every state claim as stale")
        elif age > 2:
            add("MED", f"last updated {age} days ago")
    words = len(text.split())
    if words > 3000:
        add("MED", f"{words} words, {len(lines)} lines: long for a handoff (target < 1500); prune done items")
    else:
        add("INFO", f"{words} words, {len(lines)} lines")

    # per-line checks
    sha_seen = {}
    for i, line in enumerate(lines, 1):
        for pat, name in SECRET_PATTERNS:
            if re.search(pat, line):
                add("CRIT", f"possible {name}; replace with where it lives", i)
        for pat in POISON_PATTERNS:
            if re.search(pat, line):
                add("HIGH", f"instruction-like text aimed at an AI: {line.strip()[:80]!r}", i)
        if re.search(RELATIVE_DATES, line):
            add("MED", f"relative date ({re.search(RELATIVE_DATES, line).group(0)}); use YYYY-MM-DD", i)
        if not re.search(r"(?i)\b(image|digest|container|sha256|docker|ecr)\b", line):
            for sha in re.findall(r"`([0-9a-f]{7,40})`", line):
                sha_seen.setdefault(sha, i)
        hm = re.search(r"`([\w./-]+)`[^`\n]{0,20}\bhead\b[^`\n]{0,20}`([0-9a-f]{7,40})`", line)
        if hm and repos:
            ref, sha = hm.groups()
            for r in repos:
                rc, cur = git(r, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
                if rc == 0:
                    if not cur.startswith(sha):
                        add("HIGH", f"{ref} head is now {cur[:8]}, doc says {sha}", i)
                    break
        for p in re.findall(r"`(~?/[^`\s]+)`", line):
            p = p.rstrip(".,:;)")
            if re.search(r"[<>*{}$|\[\]]", p) or not re.match(r"~/|/(home|usr|etc|opt|var|srv|mnt|tmp|root|Users)/", p):
                continue  # placeholder, glob, or app route like /api/x
            try:
                if not Path(os.path.expanduser(p)).exists():
                    add("MED", f"path does not exist on this machine (fine if it's on a server): {p}", i)
            except OSError:
                pass  # unreadable here (e.g. /root): can't judge

    if repos:
        missing = []
        for sha, i in sha_seen.items():
            if not any(git(r, "cat-file", "-e", sha + "^{commit}")[0] == 0 for r in repos):
                missing.append((sha, i))
        for sha, i in missing:
            add("HIGH", f"commit {sha} not found in any --repo (typo, unfetched, or invented)", i)
        if sha_seen and not missing:
            add("INFO", f"all {len(sha_seen)} commit SHAs exist")

    # scripts dir vs mentions
    sdir = doc.parent / "scripts"
    if sdir.is_dir():
        for f in sorted(sdir.iterdir()):
            if f.name not in text:
                add("MED", f"scripts/{f.name} is never mentioned in the doc")
    def script_exists(ref: str) -> bool:
        if ref.startswith(("~", "/")):
            return Path(os.path.expanduser(ref)).exists()
        if (doc.parent / ref).exists():
            return True
        # in a repo working tree, or on any branch of it
        return any((Path(r) / ref).exists() or git(r, "log", "--all", "-1", "--format=%h", "--", ref)[1] for r in repos)

    for ref in sorted(set(re.findall(r"(?<![\w.-])((?:~|/)?[\w./-]*scripts/[\w.-]+\.\w+)", text))):
        if not script_exists(ref):
            add("MED", f"{ref} mentioned but not found (next to the doc, on disk, or in any branch of a --repo)")

    # PR states
    if a.gh and repos:
        prs = sorted(set(re.findall(r"(?<![\w/])#(\d{2,6})\b", text)), key=int)
        states = {}
        for n in prs:
            r = subprocess.run(["gh", "pr", "view", n, "--json", "state,title"], cwd=repos[0], capture_output=True, text=True)
            if r.returncode == 0:
                states[n] = json.loads(r.stdout)["state"]
        if states:
            add("INFO", "PR states: " + ", ".join(f"#{n} {s}" for n, s in states.items()))
        for n in prs:
            if n not in states:
                add("MED", f"#{n} not found as a PR in {repos[0]}")
        for m in re.finditer(r"(?i)(open|in review|awaiting review)[^\n]{0,40}#(\d+)|#(\d+)[^\n]{0,40}\b(open|in review)\b", text):
            n = m.group(2) or m.group(3)
            if states.get(n) in ("MERGED", "CLOSED"):
                add("HIGH", f"doc calls #{n} open but it is {states[n]}")

    order = {"CRIT": 0, "HIGH": 1, "MED": 2, "INFO": 3}
    out.sort(key=lambda x: order[x[0]])
    for sev, msg in out:
        print(f"{sev:4} {msg}")
    counts = {k: sum(1 for s, _ in out if s == k) for k in order}
    print(f"summary: {counts['CRIT']} crit, {counts['HIGH']} high, {counts['MED']} med")
    return 1 if counts["CRIT"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
