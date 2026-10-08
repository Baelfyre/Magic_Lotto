# @codebase_provenance_JEO
"""Minimal TypeSafe System One transport and synthetic connectivity smoke test."""

from __future__ import annotations

import argparse
import json
import math
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL_ALIAS = "jev-latest"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


class JevClientError(RuntimeError):
    def __init__(self, error_class: str, http_status: int | None = None) -> None:
        self.error_class = error_class
        self.http_status = http_status
        super().__init__(error_class)


def request_system_one(
    state: Any,
    questions: dict[str, dict[str, Any]],
    timeout_seconds: int = 60,
) -> tuple[int, dict[str, Any]]:
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise JevClientError("CredentialUnavailable")

    request_body = json.dumps(
        {"state": state, "model": MODEL_ALIAS, "questions": questions},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if api_key in request_body:
        raise JevClientError("CredentialInRequestBlocked")

    request = urllib.request.Request(
        ENDPOINT,
        data=request_body.encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    response_bytes: bytes | None = None
    status: int | None = None
    for attempt in range(3):
        try:
            with _OPENER.open(request, timeout=timeout_seconds) as response:
                status = response.status
                response_bytes = response.read()
            break
        except urllib.error.HTTPError as error:
            status = error.code
            if status in (429, 529) and attempt < 2:
                time.sleep(2**attempt)
                continue
            raise JevClientError("HTTPError", status) from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            reason = getattr(error, "reason", None)
            error_class = type(reason if reason is not None else error).__name__
            raise JevClientError(error_class, status) from None

    if response_bytes is None or status is None:
        raise JevClientError("EmptyResponse", status)

    response_text = response_bytes.decode("utf-8", errors="replace")
    if api_key in response_text:
        raise JevClientError("CredentialEchoDetected", status)
    try:
        data = json.loads(response_text)
    except (json.JSONDecodeError, UnicodeError):
        raise JevClientError("InvalidJSONResponse", status) from None

    if not isinstance(data, dict):
        raise JevClientError("InvalidResponseShape", status)
    if "error" in data:
        raise JevClientError("TypeSafeAPIError", status)
    if not isinstance(data.get("model"), str) or not data["model"]:
        raise JevClientError("ModelMissingFromResponse", status)
    if not isinstance(data.get("answers"), dict):
        raise JevClientError("AnswersMissingFromResponse", status)
    return status, data


def _project_output_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    if not path.is_relative_to(ROOT) or path.parent != ROOT / "reports":
        raise JevClientError("OutputPathOutsideReports")
    return path


def _write_json(path: Path, value: dict[str, Any], api_key: str | None) -> None:
    serialized = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if (api_key and api_key in serialized) or "Bearer " in serialized:
        raise JevClientError("CredentialOutputBlocked")
    path.write_text(serialized, encoding="utf-8", newline="\n")
    if api_key and api_key in path.read_text(encoding="utf-8"):
        path.unlink(missing_ok=True)
        raise JevClientError("CredentialOutputDetected")


def run_smoke_test(output_path: Path) -> dict[str, Any]:
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise JevClientError("CredentialUnavailable")
    if output_path.exists():
        raise JevClientError("SmokeOutputAlreadyExists")

    state = {
        "statement": "A synthetic arithmetic note states that 2 + 2 = 4.",
        "reference": "In ordinary base-ten arithmetic, 2 + 2 equals 4.",
    }
    questions = {
        "synthetic_statement_matches_reference": {
            "type": "noul",
            "instructions": "Is state.statement consistent with state.reference?",
            "criteria": {
                "true": "The statement agrees with the reference.",
                "false": "The statement conflicts with or is not supported by the reference.",
            },
        }
    }
    status, data = request_system_one(state, questions)
    model = data["model"]
    if not model.lower().startswith("jev-"):
        raise JevClientError("UnexpectedModelIdentifier", status)
    answer = data["answers"].get("synthetic_statement_matches_reference")
    if not isinstance(answer, dict) or answer.get("type") != "noul":
        raise JevClientError("TypedNoulAnswerMissing", status)
    value = answer.get("noul")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise JevClientError("TypedNoulValueInvalid", status)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise JevClientError("TypedNoulValueInvalid", status)

    usage = data.get("usage")
    safe_usage = {}
    if isinstance(usage, dict):
        for key in ("input_tokens", "output_tokens"):
            token_count = usage.get(key)
            if isinstance(token_count, int) and not isinstance(token_count, bool):
                safe_usage[key] = token_count

    record = {
        "schema_version": "phase6a-jev-smoke/v1",
        "phase": "PHASE_6A_JEV_INTEGRATION",
        "status": "PASS",
        "provider": "TypeSafe",
        "system": "System One",
        "endpoint": ENDPOINT,
        "model_alias_requested": MODEL_ALIAS,
        "model_identifier_returned": model,
        "http_status": status,
        "synthetic_state": state,
        "typed_answer": {
            "question_id": "synthetic_statement_matches_reference",
            "type": "noul",
            "noul": value,
        },
        "usage": safe_usage,
        "credential_safety": {
            "authorization_header_recorded": False,
            "credential_value_recorded": False,
            "credential_echo_check": "PASS",
        },
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(output_path, record, api_key)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument(
        "--output",
        default="reports/phase6a_jev_smoke_test.json",
    )
    args = parser.parse_args()
    if not args.smoke_test:
        parser.error("Only --smoke-test is supported by this transport command.")

    try:
        output_path = _project_output_path(args.output)
        record = run_smoke_test(output_path)
    except JevClientError as error:
        api_key = os.environ.get("TYPESAFE_API_KEY")
        try:
            output_path = _project_output_path(args.output)
            if not output_path.exists():
                status = (
                    "AUTHENTICATION_FAILED"
                    if error.http_status in (401, 403)
                    else "CREDENTIAL_UNAVAILABLE"
                    if error.error_class == "CredentialUnavailable"
                    else "FAIL"
                )
                _write_json(
                    output_path,
                    {
                        "schema_version": "phase6a-jev-smoke/v1",
                        "phase": "PHASE_6A_JEV_INTEGRATION",
                        "status": status,
                        "http_status": error.http_status,
                        "sanitized_error_class": error.error_class,
                        "credential_value_recorded": False,
                        "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    },
                    api_key,
                )
        except JevClientError:
            pass
        print(
            f"SMOKE_TEST_FAIL status={error.http_status} "
            f"error_class={error.error_class}"
        )
        return 1

    print("SMOKE_TEST_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
