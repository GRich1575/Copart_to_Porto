import json
import logging

from vehicle_intelligence.core.logging import LOG_FILE_NAME, get_logger, setup_logging


def test_file_and_stdout_get_json_lines(tmp_path, capsys):
    setup_logging("INFO", tmp_path / "logs")
    get_logger("test").info("hello", extra={"extra_fields": {"job": "demo", "rows": 3}})

    line = (tmp_path / "logs" / LOG_FILE_NAME).read_text(encoding="utf-8").strip().splitlines()[-1]
    rec = json.loads(line)
    assert rec["msg"] == "hello"
    assert rec["level"] == "INFO"
    assert rec["logger"] == "vehicle_intel.test"
    assert rec["job"] == "demo" and rec["rows"] == 3
    assert rec["ts"].endswith("+00:00")

    out = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(out)["msg"] == "hello"


def test_level_filters_debug(tmp_path):
    setup_logging("WARNING", tmp_path)
    get_logger("test").info("quiet")
    assert not (tmp_path / LOG_FILE_NAME).exists() or "quiet" not in (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8")


def test_repeated_setup_does_not_duplicate_handlers(tmp_path):
    setup_logging("INFO", tmp_path)
    setup_logging("INFO", tmp_path)
    assert len(logging.getLogger("vehicle_intel").handlers) == 2  # stdout + file
    get_logger("x").warning("once")
    lines = (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8").strip().splitlines()
    assert sum(json.loads(l)["msg"] == "once" for l in lines) == 1
