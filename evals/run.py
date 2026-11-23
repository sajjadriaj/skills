#!/usr/bin/env python3
"""Run skill evals across assistant hosts and print a pass/fail grid.

Usage: evals/run.py [--host claude,codex,pi] [--case PATTERN] [--jobs N]
Env: PI_MODEL=<provider/model> to pick pi's model (default: pi's configured default).

Each case loads one skill (prepended as instructions), runs its prompt in a fresh temp
workdir (optionally seeded with a fixture), then checks the reply and the workdir.
Replies are saved to evals/out/<host>/<case>.md. Exit 1 if any check fails.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent / "out"
TIMEOUT = 900


def skill_text(name: str) -> str:
    s = (SKILLS / name / "SKILL.md").read_text()
    return s.replace("<skill-dir>", str(SKILLS / name)).replace(
        "`template.svg` (same folder)", f"`{SKILLS / name / 'template.svg'}`")


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=eval", "-c", "user.email=eval@example.com", *args],
                   cwd=cwd, check=True, capture_output=True)


def setup_shop(work: Path) -> None:
    shop = work / "shop"
    shutil.copytree(FIX / "shop" / "base", shop)
    git(shop, "init", "-q", "-b", "main")
    git(shop, "add", "-A")
    git(shop, "commit", "-q", "-m", "Initial shop: cart totals and checkout")
    old = subprocess.run(["git", "rev-parse", "--short=8", "HEAD"], cwd=shop, capture_output=True, text=True).stdout.strip()
    (shop / "README.md").write_text("# shop\n")
    git(shop, "add", "-A")
    git(shop, "commit", "-q", "-m", "Add README")
    git(shop, "checkout", "-q", "-b", "feature/coupons")
    shutil.copytree(FIX / "shop" / "change", shop, dirs_exist_ok=True)
    git(shop, "add", "-A")
    git(shop, "commit", "-q", "-m", "Add coupon codes at checkout")
    git(shop, "checkout", "-q", "main")
    h = work / "handoff" / "shop"
    h.mkdir(parents=True)
    (h / "handoff.md").write_text((FIX / "handoff.md").read_text().replace("{OLD_SHA}", old))


def run_host(host: str, skill: str, prompt: str, work: Path) -> str:
    sys_text = skill_text(skill)
    if host == "claude":
        cmd = ["claude", "-p", "--append-system-prompt", sys_text,
               "--allowedTools", "Read,Grep,Glob,Write,Edit,Bash", "--add-dir", str(SKILLS), "--", prompt]
    elif host == "codex":
        last = work / ".codex-last.txt"
        cmd = ["codex", "exec", "--skip-git-repo-check", "--ephemeral", "-s", "workspace-write",
               "-C", str(work), "-o", str(last),
               f"Follow these skill instructions for this task:\n\n{sys_text}\n\n---\n\nTask: {prompt}"]
    elif host == "pi":
        model = ["--model", os.environ["PI_MODEL"]] if os.environ.get("PI_MODEL") else []
        cmd = ["pi", "-p", "--no-session", *model, "--append-system-prompt", sys_text, prompt]
    else:
        raise SystemExit(f"unknown host {host}")
    r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=TIMEOUT, stdin=subprocess.DEVNULL)
    if host == "codex" and (work / ".codex-last.txt").exists():
        return (work / ".codex-last.txt").read_text()
    return r.stdout if r.stdout.strip() else r.stdout + r.stderr


def check(c: dict, reply: str, work: Path) -> bool:
    flags = re.I | re.M
    if "regex" in c:
        return re.search(c["regex"], reply[: c.get("head", len(reply))], flags) is not None
    if "not_regex" in c:
        return re.search(c["not_regex"], reply, flags) is None
    if "order" in c:
        a, b = (re.search(p, reply, flags) for p in c["order"])
        return bool(a and b and a.start() < b.start())
    if "cmd" in c:
        cmd = c["cmd"].replace("{skills}", str(SKILLS))
        return subprocess.run(cmd, shell=True, cwd=work, capture_output=True).returncode == 0
    raise ValueError(f"bad check {c}")


def run_case(host: str, case: dict) -> tuple:
    with tempfile.TemporaryDirectory(prefix="skill-eval-") as tmp:
        work = Path(tmp)
        if case.get("fixture") == "shop":
            setup_shop(work)
        try:
            reply = run_host(host, case["skill"], case["prompt"], work)
        except subprocess.TimeoutExpired:
            reply = "TIMEOUT"
        out = OUT / host / (case["id"].replace("/", "__") + ".md")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(reply)
        failed = [c["name"] for c in case["checks"] if not check(c, reply, work)]
        files = out.with_suffix(".files")
        shutil.rmtree(files, ignore_errors=True)
        shutil.copytree(work, files, ignore=shutil.ignore_patterns(".git", "node_modules", "*.png"))
    return host, case["id"], failed, len(case["checks"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="claude,codex,pi")
    ap.add_argument("--case", default="")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    cases = [c for c in yaml.safe_load((Path(__file__).parent / "cases.yaml").read_text()) if a.case in c["id"]]
    hosts = [h for h in a.host.split(",") if shutil.which(h) or print(f"skip host {h}: not installed")]
    jobs = [(h, c) for c in cases for h in hosts]
    with ThreadPoolExecutor(a.jobs) as ex:
        results = list(ex.map(lambda hc: run_case(*hc), jobs))

    width = max(len(c["id"]) for c in cases)
    print(f"{'case':<{width}}  " + "  ".join(f"{h:<8}" for h in hosts))
    bad = 0
    for c in cases:
        row = []
        for h in hosts:
            _, _, failed, n = next(r for r in results if r[0] == h and r[1] == c["id"])
            row.append(f"{n - len(failed)}/{n}".ljust(8) if not failed else f"FAIL {n - len(failed)}/{n}")
            bad += bool(failed)
        print(f"{c['id']:<{width}}  " + "  ".join(row))
    for h, cid, failed, _ in results:
        for f in failed:
            print(f"  ✗ {h} {cid}: {f}   (reply: evals/out/{h}/{cid.replace('/', '__')}.md)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
