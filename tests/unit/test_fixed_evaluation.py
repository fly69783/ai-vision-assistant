from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.run_fixed_evaluation import (
    REQUIRED_COLUMNS,
    evaluate_expectations,
    inspect_case,
    load_cases,
)


def _row(**overrides: str) -> dict[str, str]:
    row = {column: "" for column in REQUIRED_COLUMNS}
    row.update(
        {
            "case_id": "FIND-001",
            "group": "find",
            "scene": "桌面找水杯",
            "task": "find_object",
            "input_file": "sample.jpg",
            "source_and_license": "团队自摄，仅本项目使用",
            "target": "水杯",
        }
    )
    row.update(overrides)
    return row


def test_load_cases_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "cases.csv"
    path.write_text("case_id,task\nA,read_text\n", encoding="utf-8")
    with pytest.raises(ValueError, match="缺少字段"):
        load_cases(path)


def test_load_cases_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "cases.csv"
    fieldnames = sorted(REQUIRED_COLUMNS)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(_row())
        writer.writerow(_row(scene="另一个场景"))
    with pytest.raises(ValueError, match="重复编号"):
        load_cases(path)


def test_inspect_case_requires_existing_image(tmp_path: Path) -> None:
    assert inspect_case(_row(), tmp_path) == "missing_input"


def test_inspect_case_requires_find_target(tmp_path: Path) -> None:
    (tmp_path / "sample.jpg").write_bytes(b"image")
    assert inspect_case(_row(target="待填写"), tmp_path) == "missing_target"


def test_inspect_case_reports_ready(tmp_path: Path) -> None:
    (tmp_path / "sample.jpg").write_bytes(b"image")
    assert inspect_case(_row(), tmp_path) == "ready"


def test_expectations_pass_when_status_and_keywords_match() -> None:
    row = _row(expected_status="success", expected_keywords="水杯|中央")
    payload = {
        "status": "success",
        "narration": "画面中央找到水杯。",
        "evidence": [],
    }
    assert evaluate_expectations(row, payload) == "pass"


def test_expectations_fail_when_text_is_missing() -> None:
    row = _row(task="read_text", expected_text="实验室A301")
    payload = {"status": "success", "narration": "实验室A310", "evidence": []}
    assert evaluate_expectations(row, payload) == "fail"


def test_expectations_require_manual_review_without_rules() -> None:
    assert evaluate_expectations(_row(), {"status": "success"}) == "manual_review"
