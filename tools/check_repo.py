#!/usr/bin/env python3
"""Repository rule checks (R1–R6). Run: python tools/check_repo.py

Exit 0 — no violations; 1 — violations printed as `path:line: message`.
Checks only git-tracked files (falls back to a directory walk outside git).
"""

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS_MAX_LINES = 60
PLAN_PATH = "docs/plan/stages.md"
PROGRESS_PATH = "PROGRESS.md"

SECRET_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(password|passwd|api[_-]?key|secret|token)\s*[:=]\s*[\"']?[^\s\"'$<{]{12,}"),
]
TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml", ".txt", ".cfg", ".ini", ".json", ".example", ""}

STAGE_RE = re.compile(r"^## (S\d+) — (.+)$")
STATUS_RE = re.compile(r"^Status: (not started|in progress|done|blocked)$")
DEPENDS_RE = re.compile(r"^Depends: (.*)$")
STEP_RE = re.compile(r"^- \[( |x)\] (\d+\.\d+) (.+?)(?: — tests: (\S+))?$")


@dataclass
class Step:
    line: int
    checked: bool
    sid: str
    name: str
    tests: str | None


@dataclass
class Stage:
    line: int
    sid: str
    title: str
    status: str = "not started"
    depends: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)


def tracked_files(root: Path) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            capture_output=True, text=True, check=True,
        ).stdout
        return [p for p in out.splitlines() if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        skip = {".git", ".venv", "__pycache__", ".pytest_cache"}
        return [
            p.relative_to(root).as_posix()
            for p in root.rglob("*")
            if p.is_file() and not (set(p.relative_to(root).parts) & skip)
        ]


def check_progress(root: Path) -> list[str]:
    path = root / PROGRESS_PATH
    if not path.is_file():
        return [f"{PROGRESS_PATH}:1: missing (R1)"]
    n = len(path.read_text(encoding="utf-8").splitlines())
    if n > PROGRESS_MAX_LINES:
        return [f"{PROGRESS_PATH}:{PROGRESS_MAX_LINES + 1}: {n} lines > {PROGRESS_MAX_LINES} (R1)"]
    return []


def check_env_files(files: list[str]) -> list[str]:
    bad = [f for f in files if Path(f).name == ".env" or (Path(f).name.startswith(".env.") and not f.endswith(".example"))]
    return [f"{f}:1: secret env file is tracked (R2)" for f in bad]


def check_secrets(root: Path, files: list[str]) -> list[str]:
    out = []
    for f in files:
        p = root / f
        if Path(f).suffix not in TEXT_SUFFIXES or not p.is_file():
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(lines, 1):
            if any(rx.search(line) for rx in SECRET_PATTERNS):
                out.append(f"{f}:{i}: possible secret (R3)")
    return out


def parse_plan(text: str) -> list[Stage]:
    stages: list[Stage] = []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if m := STAGE_RE.match(line):
            stages.append(Stage(n, m.group(1), m.group(2)))
        elif not stages:
            continue
        elif m := STATUS_RE.match(line):
            stages[-1].status = m.group(1)
        elif m := DEPENDS_RE.match(line):
            stages[-1].depends = [d.strip() for d in m.group(1).split(",") if re.fullmatch(r"S\d+", d.strip())]
        elif m := STEP_RE.match(line):
            stages[-1].steps.append(Step(n, m.group(1) == "x", m.group(2), m.group(3), m.group(4)))
    return stages


def check_plan(root: Path, stages: list[Stage]) -> list[str]:
    out = []
    by_id = {s.sid: s for s in stages}
    for s in stages:
        loc = f"{PLAN_PATH}:{s.line}"
        if s.status == "done" and not all(st.checked for st in s.steps):
            out.append(f"{loc}: {s.sid} is done but has unchecked steps (R5)")
        for d in s.depends:
            if d not in by_id:
                out.append(f"{loc}: {s.sid} depends on unknown stage {d} (R5)")
            elif s.status == "done" and by_id[d].status != "done":
                out.append(f"{loc}: {s.sid} is done but dependency {d} is not done (R5)")
        if s.status != "done" and any(st.checked for st in s.steps):
            blockers = [d for d in s.depends if d in by_id and by_id[d].status != "done"]
            if blockers:
                out.append(f"{loc}: {s.sid} has checked steps while {', '.join(blockers)} not done (R6)")
        for st in s.steps:
            if not st.checked:
                continue
            sloc = f"{PLAN_PATH}:{st.line}"
            if not st.tests:
                out.append(f"{sloc}: checked step {st.sid} has no `— tests:` path (R4)")
            elif not (root / st.tests).is_file():
                out.append(f"{sloc}: checked step {st.sid} test file missing: {st.tests} (R4)")
    return out


def run(root: Path = ROOT) -> list[str]:
    files = tracked_files(root)
    violations = check_progress(root)
    violations += check_env_files(files)
    violations += check_secrets(root, files)
    plan = root / PLAN_PATH
    if not plan.is_file():
        violations.append(f"{PLAN_PATH}:1: missing (R4)")
    else:
        violations += check_plan(root, parse_plan(plan.read_text(encoding="utf-8")))
    return violations


def main() -> int:
    violations = run()
    for v in violations:
        print(v)
    print(f"check_repo: {len(violations)} violation(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
