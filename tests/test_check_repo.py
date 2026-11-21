import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_repo as cr  # noqa: E402


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_progress_missing_is_violation(tmp_path):
    assert cr.check_progress(tmp_path) == ["PROGRESS.md:1: missing (R1)"]


def test_progress_within_limit_ok(tmp_path):
    _write(tmp_path, "PROGRESS.md", "line\n" * cr.PROGRESS_MAX_LINES)
    assert cr.check_progress(tmp_path) == []


def test_progress_over_limit_is_violation(tmp_path):
    _write(tmp_path, "PROGRESS.md", "line\n" * (cr.PROGRESS_MAX_LINES + 1))
    out = cr.check_progress(tmp_path)
    assert len(out) == 1 and "(R1)" in out[0]


def test_env_file_tracked_is_violation_example_allowed():
    out = cr.check_env_files([".env", "config/.env.local", ".env.example", "src/a.py"])
    assert out == [".env:1: secret env file is tracked (R2)", "config/.env.local:1: secret env file is tracked (R2)"]


def test_secret_detected_and_placeholder_ignored(tmp_path):
    _write(tmp_path, "a.py", 'token = "ghp_' + "A" * 36 + '"\n')
    _write(tmp_path, "b.py", "api_key = ${API_KEY}\n")
    out = cr.check_secrets(tmp_path, ["a.py", "b.py"])
    assert out == ["a.py:1: possible secret (R3)"]


def test_parse_plan_reads_stages_steps_and_depends():
    text = (
        "## S0 — Process\nStatus: done\nDepends: —\n- [x] 0.1 Doc — tests: t/a.py\n"
        "## S1 — Foundation\nStatus: not started\nDepends: S0\n- [ ] 1.1 Skel — tests: t/b.py\n"
    )
    stages = cr.parse_plan(text)
    assert [s.sid for s in stages] == ["S0", "S1"]
    assert stages[0].status == "done" and stages[0].depends == []
    assert stages[1].depends == ["S0"]
    assert stages[0].steps[0].checked and stages[0].steps[0].tests == "t/a.py"
    assert not stages[1].steps[0].checked


def _plan(tmp_path, text):
    _write(tmp_path, cr.PLAN_PATH, text)
    return cr.check_plan(tmp_path, cr.parse_plan(text))


def test_checked_step_requires_existing_test_file(tmp_path):
    text = "## S0 — P\nStatus: in progress\nDepends: —\n- [x] 0.1 Doc — tests: tests/missing.py\n"
    out = _plan(tmp_path, text)
    assert len(out) == 1 and "test file missing" in out[0] and "(R4)" in out[0]


def test_checked_step_without_tests_path_is_violation(tmp_path):
    text = "## S0 — P\nStatus: in progress\nDepends: —\n- [x] 0.1 Doc\n"
    out = _plan(tmp_path, text)
    assert len(out) == 1 and "(R4)" in out[0]


def test_done_stage_with_unchecked_step_is_violation(tmp_path):
    _write(tmp_path, "tests/ok.py", "")
    text = "## S0 — P\nStatus: done\nDepends: —\n- [x] 0.1 A — tests: tests/ok.py\n- [ ] 0.2 B\n"
    out = _plan(tmp_path, text)
    assert any("unchecked steps (R5)" in v for v in out)


def test_downstream_stage_cannot_be_done_before_upstream(tmp_path):
    text = (
        "## S0 — P\nStatus: in progress\nDepends: —\n- [ ] 0.1 A\n"
        "## S1 — F\nStatus: done\nDepends: S0\n"
    )
    out = _plan(tmp_path, text)
    assert any("dependency S0 is not done (R5)" in v for v in out)


def test_downstream_stage_with_checked_step_while_upstream_open_is_violation(tmp_path):
    _write(tmp_path, "tests/ok.py", "")
    text = (
        "## S0 — P\nStatus: in progress\nDepends: —\n- [ ] 0.1 A\n"
        "## S1 — F\nStatus: in progress\nDepends: S0\n- [x] 1.1 B — tests: tests/ok.py\n"
    )
    out = _plan(tmp_path, text)
    assert any("(R6)" in v for v in out)


def test_unknown_dependency_is_violation(tmp_path):
    text = "## S1 — F\nStatus: not started\nDepends: S9\n- [ ] 1.1 B\n"
    out = _plan(tmp_path, text)
    assert any("unknown stage S9 (R5)" in v for v in out)


def test_real_repository_passes_checks():
    assert cr.run(ROOT) == []
