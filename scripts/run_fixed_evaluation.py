"""运行40个固定场景的训练前基线评测。"""

from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

MANIFEST_COLUMNS = [
    "case_id",
    "group",
    "scene",
    "task",
    "input_file",
    "source_and_license",
    "target",
    "query",
    "expected_status",
    "expected_keywords",
    "expected_text",
    "notes",
]
REQUIRED_COLUMNS = set(MANIFEST_COLUMNS)
SUPPORTED_TASKS = {
    "scene_description",
    "read_text",
    "find_object",
    "visual_question",
}
RESULT_COLUMNS = [
    *MANIFEST_COLUMNS,
    "input_state",
    "http_status",
    "response_status",
    "actual",
    "automatic_pass",
    "api_latency_ms",
    "round_trip_ms",
    "evidence_count",
    "warnings",
    "failure_type",
]


def _is_placeholder(value: str) -> bool:
    normalized = value.strip()
    return not normalized or normalized.startswith("待")


def load_cases(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            names = "、".join(sorted(missing))
            raise ValueError(f"评测清单缺少字段：{names}")
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    if not rows:
        raise ValueError("评测清单中没有用例。")
    case_ids = [row["case_id"] for row in rows]
    duplicates = sorted(case_id for case_id, count in Counter(case_ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"评测清单存在重复编号：{'、'.join(duplicates)}")
    return rows


def resolve_input(repo_root: Path, input_file: str) -> Path:
    path = Path(input_file)
    return path if path.is_absolute() else repo_root / path


def inspect_case(row: dict[str, str], repo_root: Path) -> str:
    if row["task"] not in SUPPORTED_TASKS:
        return "invalid_task"
    if row["task"] == "find_object" and _is_placeholder(row["target"]):
        return "missing_target"
    if row["task"] == "visual_question" and _is_placeholder(row["query"]):
        return "missing_query"
    if _is_placeholder(row["input_file"]):
        return "missing_input"
    if not resolve_input(repo_root, row["input_file"]).is_file():
        return "missing_input"
    if _is_placeholder(row["source_and_license"]):
        return "missing_license"
    return "ready"


def _normalized_text(value: str) -> str:
    return "".join(value.lower().split())


def evaluate_expectations(row: dict[str, str], payload: dict[str, Any]) -> str:
    checks: list[bool] = []
    expected_status = row["expected_status"].strip()
    if expected_status:
        checks.append(str(payload.get("status", "")) == expected_status)

    evidence = payload.get("evidence") or []
    evidence_text = " ".join(
        str(item.get("content", "")) for item in evidence if isinstance(item, dict)
    )
    combined = " ".join(
        [
            str(payload.get("message", "")),
            str(payload.get("narration", "")),
            evidence_text,
        ]
    )
    normalized_combined = _normalized_text(combined)

    keywords = [item.strip() for item in row["expected_keywords"].split("|") if item.strip()]
    if keywords:
        checks.append(all(_normalized_text(item) in normalized_combined for item in keywords))

    expected_text = row["expected_text"].strip()
    if expected_text:
        checks.append(_normalized_text(expected_text) in normalized_combined)

    if not checks:
        return "manual_review"
    return "pass" if all(checks) else "fail"


def _mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed in {"image/jpeg", "image/png", "image/webp"}:
        return guessed
    raise ValueError(f"不支持的图片格式：{path.suffix or '无扩展名'}")


def _base_result(row: dict[str, str], state: str) -> dict[str, Any]:
    return {
        **row,
        "input_state": state,
        "http_status": "",
        "response_status": "",
        "actual": "",
        "automatic_pass": "not_run",
        "api_latency_ms": "",
        "round_trip_ms": "",
        "evidence_count": "",
        "warnings": "",
        "failure_type": "" if state == "ready" else state,
    }


def run_case(
    client: httpx.Client,
    row: dict[str, str],
    repo_root: Path,
) -> dict[str, Any]:
    state = inspect_case(row, repo_root)
    result = _base_result(row, state)
    if state != "ready":
        return result

    image_path = resolve_input(repo_root, row["input_file"])
    data = {"task": row["task"]}
    if row["target"]:
        data["target"] = row["target"]
    if row["query"]:
        data["query"] = row["query"]

    started = time.perf_counter()
    try:
        with image_path.open("rb") as image_file:
            response = client.post(
                "/api/v1/analyze",
                data=data,
                files={"file": (image_path.name, image_file, _mime_type(image_path))},
            )
        round_trip_ms = (time.perf_counter() - started) * 1000
        result["http_status"] = response.status_code
        result["round_trip_ms"] = f"{round_trip_ms:.1f}"
        response.raise_for_status()
        payload = response.json()
        result.update(
            {
                "response_status": payload.get("status", ""),
                "actual": payload.get("narration", ""),
                "automatic_pass": evaluate_expectations(row, payload),
                "api_latency_ms": payload.get("latency_ms", ""),
                "evidence_count": len(payload.get("evidence") or []),
                "warnings": json.dumps(payload.get("warnings") or [], ensure_ascii=False),
            }
        )
        if result["automatic_pass"] == "fail":
            result["failure_type"] = "needs_review"
    except (OSError, ValueError, httpx.HTTPError, json.JSONDecodeError) as exc:
        result["automatic_pass"] = "error"
        result["failure_type"] = type(exc).__name__
        result["actual"] = str(exc)
    return result


def write_results(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("docs/testing/test-cases.csv"),
        help="固定场景清单路径",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="已启动的AI视觉服务地址",
    )
    parser.add_argument("--output", type=Path, help="结果CSV路径")
    parser.add_argument("--check-only", action="store_true", help="只检查图片和清单，不调用API")
    parser.add_argument("--limit", type=int, help="只运行前N条可调试用例")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    cases_path = args.cases if args.cases.is_absolute() else repo_root / args.cases
    try:
        cases = load_cases(cases_path)
    except (OSError, ValueError) as exc:
        print(f"[失败] {exc}")
        return 1
    if args.limit is not None:
        if args.limit <= 0:
            print("[失败] --limit必须大于0。")
            return 1
        cases = cases[: args.limit]

    states = Counter(inspect_case(row, repo_root) for row in cases)
    print(f"固定场景清单：{len(cases)}条")
    for state, count in sorted(states.items()):
        print(f"- {state}: {count}")
    if args.check_only:
        print("检查完成。把图片放入清单指定路径并填写来源授权后，再运行正式评测。")
        return 0

    output_path = args.output or Path(
        "output", f"fixed-evaluation-{datetime.now():%Y%m%d-%H%M%S}.csv"
    )
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    with httpx.Client(base_url=args.base_url, timeout=90.0) as client:
        results = [run_case(client, row, repo_root) for row in cases]
    write_results(output_path, results)

    outcomes = Counter(str(row["automatic_pass"]) for row in results)
    print(f"结果已保存：{output_path}")
    for outcome, count in sorted(outcomes.items()):
        print(f"- {outcome}: {count}")
    return 1 if outcomes.get("error", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
