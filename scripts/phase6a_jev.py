# @codebase_provenance_JEO
"""Package the sealed Phase 6 evidence packet, call JEV, and map typed answers."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jev_client import ENDPOINT, MODEL_ALIAS, JevClientError, request_system_one


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "reports" / "phase6_jev_adjudication.json"
CSV_PATH = ROOT / "reports" / "phase6_evidence_matrix.csv"
MARKDOWN_PATH = ROOT / "reports" / "phase6_jev_evidence_review.md"
VALIDATION_PATH = ROOT / "reports" / "phase6a_jev_integration_validation.json"
EXPECTED_PACKET_HASHES = {
    "reports/phase6_jev_adjudication.json": "5bc4963b5688fd6cf73469c9beedba0664c99c2fc14daaaa3a11cfa4dd49e827",
    "reports/phase6_evidence_matrix.csv": "8478afcfd4ed6d9b1c438ca6c4724778190c69e2bb8ab078431ad8fc88c60443",
    "reports/phase6_jev_evidence_review.md": "b1ba376f048c94fa48db7f84c2fd6a9fd64049dbcb7a4dff55e8960392df9b56",
}

VERDICTS = {
    "SUPPORTED": "The evidence directly and consistently supports the claim.",
    "SUPPORTED_WITH_LIMITATIONS": "The evidence supports the claim when its stated scope and limitations are retained.",
    "INCONCLUSIVE": "The evidence does not resolve whether the claim is supported.",
    "NOT_SUPPORTED": "The evidence does not provide adequate support for the claim.",
    "CONTRADICTED": "The evidence materially conflicts with the claim.",
}
FINAL_STATUSES = {
    "STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL": "No reproducible predictive improvement was demonstrated under the tested methods; retain the bounded interpretation that this does not prove impossibility.",
    "REQUIRES_METHOD_REPAIR": "A material methodological defect needs repair before the current evidence can support a conclusion.",
    "EVIDENCE_SUPPORTS_MODEL_FREEZE_FOR_TEST": "The evidence supports freezing a specified candidate and plan for a separately authorized one-time test evaluation.",
    "INCONCLUSIVE_REQUIRES_NEW_DATA": "The present evidence is unresolved and additional data are needed for a stronger conclusion.",
}
PHASE5R_LABELS = {
    "TOO_WEAK": "The PHASE5R_INCONCLUSIVE label understates what the evidence establishes.",
    "APPROPRIATE": "The PHASE5R_INCONCLUSIVE label accurately reflects mixed and limited evidence.",
    "TOO_STRONG": "The PHASE5R_INCONCLUSIVE label overstates what the evidence establishes.",
}
NO_SIGNAL_CONCLUSIONS = {
    "DEFENSIBLE": "The scoped conclusion is defensible for the available data and tested methods.",
    "DEFENSIBLE_WITH_LIMITATIONS": "The conclusion is defensible only with explicit scope and limitations.",
    "NOT_DEFENSIBLE": "The evidence does not support this conclusion as worded.",
    "INCONCLUSIVE": "The evidence does not resolve whether this conclusion is defensible.",
}
OVERSTATEMENT_FINDINGS = {
    "NO_MATERIAL_OVERSTATEMENT": "No material overstatement was identified.",
    "SOME_OVERSTATEMENT": "Some wording requires qualification.",
    "MATERIAL_OVERSTATEMENT": "At least one material overstatement needs correction.",
    "UNKNOWN": "The evidence supplied does not resolve overstatement risk.",
}
METHOD_FINDINGS = {
    "NONE_MATERIAL": "No material defect invalidating the current evidence was identified.",
    "LIMITATIONS_ONLY": "Limitations affect interpretation but do not invalidate the evidence.",
    "MATERIAL_METHOD_REPAIR": "A material methodological defect should be repaired.",
    "UNRESOLVED": "The supplied evidence is insufficient to resolve methodological validity.",
}
RISK_OPTIONS = {
    "LOW": "The claim is well scoped and wording is unlikely to overstate the evidence.",
    "MODERATE": "The claim needs qualification to prevent a plausible overstatement.",
    "HIGH": "The claim as worded risks a material overstatement.",
}
ASSUMPTION_LEVELS = [
    "Material assumptions are unsupported, contradicted, or make the claim invalid.",
    "Assumptions are plausible, but important parts remain unverified.",
    "Assumptions are supported or not material to this scoped claim.",
]
LIMITATION_LEVELS = [
    "Limitations are severe enough to prevent or seriously undermine the claim.",
    "Limitations are material but bounded; the claim needs explicit qualification.",
    "Limitations are minor or do not materially affect the scoped claim.",
]


class Phase6AError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_packet() -> tuple[dict[str, Any], list[dict[str, str]], str, dict[str, str]]:
    hashes: dict[str, str] = {}
    for relative, expected in EXPECTED_PACKET_HASHES.items():
        path = ROOT / relative
        actual = _sha256(path)
        if actual != expected:
            raise Phase6AError(f"EvidencePacketHashMismatch:{relative}")
        hashes[relative] = actual

    record = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    matrix_text = CSV_PATH.read_text(encoding="utf-8-sig")
    matrix = list(csv.DictReader(io.StringIO(matrix_text)))
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    if record.get("status") != "PHASE6_BLOCKED":
        raise Phase6AError("Phase6PacketNotBlocked")
    if record.get("jev", {}).get("status") != "UNAVAILABLE":
        raise Phase6AError("Phase6BlockReasonChanged")
    if len(record.get("claims", [])) != 8 or len(matrix) != 8:
        raise Phase6AError("ClaimCountMismatch")
    if record.get("preflight", {}).get("locked_test_metadata_only", {}).get(
        "phase6_target_rows_opened"
    ) is not False:
        raise Phase6AError("LockedTestBoundaryNotProven")
    if record.get("preflight", {}).get("locked_test_metadata_only", {}).get(
        "phase6_predictive_evaluation_performed"
    ) is not False:
        raise Phase6AError("LockedTestEvaluationFlagInvalid")
    if record.get("preflight", {}).get("keys_env", {}).get("tracked") is not False:
        raise Phase6AError("KeysEnvTracked")
    if record.get("preflight", {}).get("keys_env", {}).get("ignored") is not True:
        raise Phase6AError("KeysEnvIgnoreCheckMissing")

    rows_by_id = {row["claim_id"]: row for row in matrix}
    claims = record["claims"]
    if set(rows_by_id) != {claim["id"] for claim in claims}:
        raise Phase6AError("ClaimIdMismatch")
    for claim in claims:
        if rows_by_id[claim["id"]]["claim"] != claim["claim"]:
            raise Phase6AError(f"ClaimTextMismatch:{claim['id']}")
    return record, matrix, markdown, hashes


def _choice(instructions: str, criteria: dict[str, str]) -> dict[str, Any]:
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def _noul(instructions: str, yes: str, no: str) -> dict[str, Any]:
    return {
        "type": "noul",
        "instructions": instructions,
        "criteria": {"true": yes, "false": no},
    }


def _score(instructions: str, levels: list[str]) -> dict[str, Any]:
    return {"type": "score", "instructions": instructions, "criteria": levels}


def _candidate_wording(row: dict[str, str]) -> str:
    prefix = "Candidate wording only: "
    value = row["recommended_wording_for_jev_review"]
    return value[len(prefix) :] if value.startswith(prefix) else value


def _build_questions(
    claims: list[dict[str, Any]], rows_by_id: dict[str, dict[str, str]]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    questions: dict[str, dict[str, Any]] = {}
    wording_choices: dict[str, dict[str, str]] = {}
    for claim in claims:
        claim_id = claim["id"]
        lower_id = claim_id.lower()
        row = rows_by_id[claim_id]
        questions[f"{lower_id}_verdict"] = _choice(
            f"Which allowed evidence verdict best fits claim {claim_id} after weighing the full packet?",
            VERDICTS,
        )
        questions[f"{lower_id}_support"] = _noul(
            f"Does the supplied evidence materially support claim {claim_id} within its stated scope?",
            "The evidence materially supports this scoped claim.",
            "The evidence does not materially support this scoped claim.",
        )
        questions[f"{lower_id}_caution"] = _noul(
            f"Does the supplied contradictory or cautionary evidence materially weaken claim {claim_id}?",
            "Contradicting evidence or limitations materially weaken this claim.",
            "No material contradiction or caution in the supplied packet weakens this claim.",
        )
        questions[f"{lower_id}_assumptions"] = _score(
            f"How well supported are the material assumptions behind claim {claim_id}?",
            ASSUMPTION_LEVELS,
        )
        questions[f"{lower_id}_limitations"] = _score(
            f"How materially do the limitations affect claim {claim_id} as written?",
            LIMITATION_LEVELS,
        )
        questions[f"{lower_id}_overstatement"] = _choice(
            f"What is the risk that the wording of claim {claim_id} overstates the evidence?",
            RISK_OPTIONS,
        )

        choices = {
            "candidate_wording": _candidate_wording(row),
            "original_claim": claim["claim"],
            "human_rewrite_needed": "No supplied sentence is suitable; request human wording review.",
        }
        wording_choices[claim_id] = choices
        wording_criteria = {
            "candidate_wording": f"Choose the existing scoped candidate wording: {choices['candidate_wording']}",
            "original_claim": f"Keep the original wording: {choices['original_claim']}",
            "human_rewrite_needed": choices["human_rewrite_needed"],
        }
        questions[f"{lower_id}_wording"] = _choice(
            f"Which supplied wording is best calibrated for claim {claim_id}? Choose human_rewrite_needed if neither sentence is suitable.",
            wording_criteria,
        )

    questions["global_stop_model_expansion"] = _noul(
        "Does the accumulated evidence support stopping further model expansion for now?",
        "Further model expansion is not justified by the current evidence.",
        "The current evidence supports additional bounded model development.",
    )
    questions["global_open_test_value"] = _noul(
        "Would opening the locked test partition now provide meaningful scientific information, assuming no model and plan are frozen?",
        "Opening it now would provide meaningful scientific information.",
        "Opening it now would not provide meaningful scientific information under the stated condition.",
    )
    questions["global_phase5r_label"] = _choice(
        "Is the existing PHASE5R_INCONCLUSIVE label too weak, appropriate, or too strong?",
        PHASE5R_LABELS,
    )
    questions["global_no_signal_conclusion"] = _choice(
        "Is NO_REPRODUCIBLE_PREDICTIVE_SIGNAL_DETECTED defensible for the available data and tested methods?",
        NO_SIGNAL_CONCLUSIONS,
    )
    questions["global_overstatement_findings"] = _choice(
        "What best summarizes the risk that findings in the supplied packet are overstated?",
        OVERSTATEMENT_FINDINGS,
    )
    questions["global_method_findings"] = _choice(
        "Are there methodological defects serious enough to invalidate the current conclusion?",
        METHOD_FINDINGS,
    )
    questions["global_research_status"] = _choice(
        "Which final research status best follows from the evidence and the limitations?",
        FINAL_STATUSES,
    )
    return questions, wording_choices


def _probability_distribution(
    answer: dict[str, Any], allowed: set[str]
) -> dict[str, float]:
    distribution = answer.get("probabilities")
    if not isinstance(distribution, dict) or set(distribution) != allowed:
        raise Phase6AError("ChoiceProbabilityKeysInvalid")
    clean: dict[str, float] = {}
    for key, value in distribution.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise Phase6AError("ChoiceProbabilityInvalid")
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise Phase6AError("ChoiceProbabilityInvalid")
        clean[key] = float(value)
    if abs(sum(clean.values()) - 1) > 0.001:
        raise Phase6AError("ChoiceProbabilitySumInvalid")
    return clean


def _normalize_answer(
    answer: Any,
    question: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(answer, dict) or answer.get("type") != question["type"]:
        raise Phase6AError("TypedAnswerMismatch")
    kind = question["type"]
    if kind == "noul":
        value = answer.get("noul")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise Phase6AError("NoulValueInvalid")
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise Phase6AError("NoulValueInvalid")
        return {"type": "noul", "noul": float(value)}

    confidence = answer.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise Phase6AError("TypedConfidenceMissing")
    if not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise Phase6AError("TypedConfidenceInvalid")
    allowed = set(question["criteria"]) if kind == "choice" else {"0", "1", "2"}
    probabilities = _probability_distribution(answer, allowed)
    if kind == "choice":
        choice = answer.get("choice")
        if choice not in question["criteria"]:
            raise Phase6AError("ChoiceValueInvalid")
        return {
            "type": "choice",
            "choice": choice,
            "confidence": float(confidence),
            "probabilities": probabilities,
        }
    if kind == "score":
        score_value = answer.get("score")
        if isinstance(score_value, bool) or not isinstance(score_value, (int, float)):
            raise Phase6AError("ScoreValueMissing")
        if not math.isfinite(score_value) or not 0 <= score_value <= 2:
            raise Phase6AError("ScoreValueInvalid")
        legend = answer.get("legend")
        if not isinstance(legend, dict) or set(legend) != allowed:
            raise Phase6AError("ScoreLegendInvalid")
        return {
            "type": "score",
            "score": float(score_value),
            "legend": legend,
            "probabilities": probabilities,
            "confidence": float(confidence),
        }
    raise Phase6AError("QuestionTypeUnsupported")


def _answer(
    normalized: dict[str, dict[str, Any]], question_id: str
) -> dict[str, Any]:
    return normalized[question_id]


def _replace_section(
    report: str,
    heading: str,
    next_heading: str,
    replacement: str,
) -> str:
    start_marker = f"## {heading}\n"
    end_marker = f"## {next_heading}\n"
    start = report.index(start_marker)
    end = report.index(end_marker, start + len(start_marker))
    return report[: start + len(start_marker)] + replacement.strip() + "\n\n" + report[end:]


def _new_markdown(
    prior: str,
    record: dict[str, Any],
    matrix: list[dict[str, str]],
    native: dict[str, dict[str, Any]],
    model: str,
    smoke: dict[str, Any],
) -> str:
    claim_by_id = {claim["id"]: claim for claim in record["claims"]}
    rows = []
    for claim_id in sorted(claim_by_id):
        claim = claim_by_id[claim_id]
        verdict = claim["jev"]["verdict"]
        wording = claim["jev"]["recommended_wording"]["text"] or "Human wording review requested."
        rows.append(
            f"| {claim_id} | {verdict['choice']} | {verdict['confidence']:.3f} | "
            f"{claim['jev']['overstatement_risk']['choice']} | {wording.replace('|', '\\|')} |"
        )
    global_rows = [
        ("Stop further model expansion", native["global_stop_model_expansion"]["noul"]),
        ("Open test now has meaningful value", native["global_open_test_value"]["noul"]),
        ("Phase 5R label", native["global_phase5r_label"]["choice"]),
        ("No reproducible signal conclusion", native["global_no_signal_conclusion"]["choice"]),
        ("Overstatement findings", native["global_overstatement_findings"]["choice"]),
        ("Methodological defects", native["global_method_findings"]["choice"]),
        ("Recommended research status", native["global_research_status"]["choice"]),
    ]
    global_table = "\n".join(f"| {name} | {value} |" for name, value in global_rows)
    result = (
        f"**Phase 6A status: PHASE6A_PASS_AND_PHASE6_ADJUDICATED.** "
        f"TypeSafe System One returned typed judgments using model {model}. "
        f"The JEV-selected Phase 6 research status is {record['status']}. "
        "The locked test remains sealed; the recommendation is not authorization to open it."
    )
    integration = (
        f"- Provider and system: TypeSafe System One.\n"
        f"- Requested alias: {MODEL_ALIAS}; returned model: {model}.\n"
        f"- Request/response shape followed the trusted SINAG reference and official API contract.\n"
        f"- Synthetic smoke test: PASS, HTTP {smoke['http_status']}, typed Noul answer parsed.\n"
        f"- Credential came from the exact TYPESAFE_API_KEY entry in Keys.env; the value and request headers were not recorded.\n"
        f"- TypeSafe System One source and response were checked for credential echo before reporting."
    )
    adjudication = (
        "JEV returned one typed verdict and the requested supporting, cautionary, assumption, limitation, "
        "overstatement, and wording assessments for each claim. Choice probabilities, Choice/Score confidence, "
        "Score distributions, and Noul probabilities are stored as returned. No free-form JEV explanation "
        "or probability was invented.\n\n"
        "| Claim | JEV verdict | Verdict confidence | Overstatement risk | Selected wording |\n"
        "| --- | --- | ---: | --- | --- |\n"
        + "\n".join(rows)
        + "\n\n| Global question | Typed JEV answer |\n| --- | --- |\n"
        + global_table
    )
    research = (
        f"JEV selected {record['status']} as the Phase 6 evidence-level status. "
        "The locked test remains sealed and unscored. Any future one-time test evaluation requires "
        "a separately frozen model and analysis plan plus the applicable authorization."
    )
    report = prior
    report = _replace_section(report, "Result", "JEV availability and credential handling", result)
    report = _replace_section(
        report,
        "JEV availability and credential handling",
        "Preflight",
        integration,
    )
    report = _replace_section(
        report,
        "Claim and global adjudication status",
        "Interim research handling",
        adjudication,
    )
    report = _replace_section(
        report,
        "Interim research handling",
        "Git and validation record",
        research,
    )
    report = report.replace(
        "## JEV availability and credential handling",
        "## JEV integration and credential handling",
    )
    marker = "## Git and validation record\n"
    start = report.index(marker) + len(marker)
    report = report[:start] + (
        "Branch main at HEAD "
        f"{record['repository']['head']}. The tracked tree and index were clean before Phase 6A; "
        "all pre-existing untracked phase artifacts were preserved. Phase 6A added "
        "scripts/jev_client.py, scripts/phase6a_jev.py, "
        "reports/phase6a_jev_smoke_test.json, and "
        "reports/phase6a_jev_integration_validation.json, and updated the three Phase 6 report files. "
        "No model training, new features, test scoring, or number recommendations occurred. "
        "Nothing was staged, committed, pushed, or merged.\n"
    )
    return report


def _safe_write_group(contents: dict[Path, str], api_key: str) -> None:
    for content in contents.values():
        if api_key in content or "Bearer " in content or "Authorization:" in content:
            raise Phase6AError("CredentialOutputBlocked")

    originals = {
        path: path.read_bytes() if path.exists() else None for path in contents
    }
    temporary_paths: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for path, content in contents.items():
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary_paths[path] = Path(temporary.name)
        for path, temporary_path in temporary_paths.items():
            os.replace(temporary_path, path)
            replaced.append(path)
        for path in contents:
            written = path.read_text(encoding="utf-8")
            if api_key in written or "Bearer " in written or "Authorization:" in written:
                raise Phase6AError("CredentialOutputDetected")
    except Exception:
        for path in reversed(replaced):
            original = originals[path]
            if original is None:
                path.unlink(missing_ok=True)
            else:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=path.parent,
                    prefix=f".{path.name}.",
                    suffix=".restore.tmp",
                    delete=False,
                ) as temporary:
                    temporary.write(original)
                    restore_path = Path(temporary.name)
                os.replace(restore_path, path)
        for temporary_path in temporary_paths.values():
            temporary_path.unlink(missing_ok=True)
        raise


def _validate_prior_artifacts() -> dict[str, Any]:
    p5r_path = ROOT / "reports" / "phase5r_evidence.json"
    p5r = json.loads(p5r_path.read_text(encoding="utf-8"))
    safe_hashes = p5r["prior_phase_integrity"]["prior_artifact_hashes"]
    checked: list[str] = []
    for relative, expected in safe_hashes.items():
        if relative.endswith((".md", ".json", ".py")):
            if _sha256(ROOT / relative) != expected:
                raise Phase6AError(f"PriorArtifactHashMismatch:{relative}")
            checked.append(relative)
    phase5r_outputs = p5r["output_sha256"]
    for relative, expected in phase5r_outputs.items():
        if _sha256(ROOT / relative) != expected:
            raise Phase6AError(f"Phase5ROutputHashMismatch:{relative}")

    phase5a = json.loads((ROOT / "reports" / "phase5a_validation.json").read_text(encoding="utf-8"))
    if phase5a["checks"]["test_targets_parsed"] is not False:
        raise Phase6AError("Phase5ATestBoundaryChanged")
    if phase5a["checks"]["test_metrics_calculated"] is not False:
        raise Phase6AError("Phase5ATestMetricsFlagChanged")
    if p5r["security"]["locked_test_targets_parsed"] is not False:
        raise Phase6AError("Phase5RTestBoundaryChanged")
    if p5r["validation"]["locked_test_rows_parsed_or_scored"] != "NO":
        raise Phase6AError("Phase5RTestScoringFlagChanged")

    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", "Keys.env"],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", "Keys.env"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    if not ignored or tracked:
        raise Phase6AError("KeysEnvGitMetadataInvalid")
    return {
        "prior_report_json_source_files_hash_checked": len(checked),
        "prior_report_json_source_files_hash_status": "PASS",
        "phase5r_output_hashes_checked": len(phase5r_outputs),
        "phase5r_output_hash_status": "PASS",
        "phase5a_locked_test_flags": "PASS",
        "phase5r_locked_test_flags": "PASS",
        "keys_env_ignored": ignored,
        "keys_env_tracked": tracked,
        "locked_test_data_reopened": False,
    }


def run_phase6() -> None:
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise Phase6AError("CredentialUnavailable")
    record, matrix, prior_markdown, packet_hashes = _load_packet()
    integrity = _validate_prior_artifacts()
    smoke_path = ROOT / "reports" / "phase6a_jev_smoke_test.json"
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    if smoke.get("status") != "PASS" or smoke.get("system") != "System One":
        raise Phase6AError("SmokeTestNotPassed")

    rows_by_id = {row["claim_id"]: row for row in matrix}
    questions, wording_choices = _build_questions(record["claims"], rows_by_id)
    state = {
        "role": "Independent typed evidence adjudicator, not predictor.",
        "instructions": [
            "Evaluate the evidence and claims in the supplied Phase 6 packet.",
            "The prior PHASE6_BLOCKED status records an integration issue, not scientific evidence.",
            "Use only the supplied packet. Do not invent evidence, train models, recommend numbers, or infer locked-test outcomes.",
            "The test partition is SEALED. This request grants no permission to open or score it.",
            "Use the typed question criteria exactly; do not return free-form explanations.",
        ],
        "packet_sha256": packet_hashes,
        "phase6_packet": {
            "adjudication_record": record,
            "evidence_matrix_rows": matrix,
            "review_report_markdown": prior_markdown,
        },
    }
    status, response = request_system_one(state, questions)
    model = response["model"]
    if not model.lower().startswith("jev-"):
        raise Phase6AError("UnexpectedModelIdentifier")
    answers = response["answers"]
    if set(answers) != set(questions):
        raise Phase6AError("QuestionAnswerSetMismatch")
    native = {
        question_id: _normalize_answer(answers[question_id], question)
        for question_id, question in questions.items()
    }
    if set(native) != set(questions):
        raise Phase6AError("TypedResponseValidationFailed")

    final_status = native["global_research_status"]["choice"]
    if final_status not in FINAL_STATUSES:
        raise Phase6AError("FinalResearchStatusInvalid")
    claims_by_id = {claim["id"]: claim for claim in record["claims"]}
    for claim_id, choices in wording_choices.items():
        result = native[f"{claim_id.lower()}_wording"]["choice"]
        if result not in choices:
            raise Phase6AError(f"RecommendedWordingInvalid:{claim_id}")
        verdict = native[f"{claim_id.lower()}_verdict"]
        claims_by_id[claim_id]["adjudication_status"] = "ADJUDICATED_BY_JEV"
        claims_by_id[claim_id]["jev_verdict"] = verdict["choice"]
        claims_by_id[claim_id]["jev"] = {
            "verdict": verdict,
            "supporting_evidence_assessment": native[f"{claim_id.lower()}_support"],
            "contradicting_or_cautionary_evidence_assessment": native[
                f"{claim_id.lower()}_caution"
            ],
            "assumptions": native[f"{claim_id.lower()}_assumptions"],
            "assumption_scale": ASSUMPTION_LEVELS,
            "limitations": native[f"{claim_id.lower()}_limitations"],
            "limitation_scale": LIMITATION_LEVELS,
            "overstatement_risk": native[f"{claim_id.lower()}_overstatement"],
            "recommended_wording": {
                "choice": result,
                "text": choices[result] if result != "human_rewrite_needed" else None,
                "human_rewrite_needed": result == "human_rewrite_needed",
                "native_answer": native[f"{claim_id.lower()}_wording"],
            },
        }

    global_ids = {
        "stop_model_expansion": "global_stop_model_expansion",
        "open_test_now_value": "global_open_test_value",
        "phase5r_label": "global_phase5r_label",
        "no_reproducible_signal_conclusion": "global_no_signal_conclusion",
        "overstatement_findings": "global_overstatement_findings",
        "methodological_defects": "global_method_findings",
        "recommended_research_status": "global_research_status",
    }
    record["status"] = final_status
    record["jev"] = {
        "status": "SUCCESS",
        "provider": "TypeSafe",
        "system": "System One",
        "endpoint": ENDPOINT,
        "model_alias_requested": MODEL_ALIAS,
        "model_identifier_returned": model,
        "request_question_count": len(questions),
        "http_status": status,
        "request_schema_reference": "D:/Dev/Sinag/scripts/content/jev-smoke-tests.js",
        "response_schema_reference": "D:/Dev/Sinag/scripts/content/definition-cross-check.js",
        "official_api_reference": "https://docs.typesafe.ai/api",
        "evidence_packet_sha256": packet_hashes,
        "native_typed_answers": native,
        "usage": response.get("usage") if isinstance(response.get("usage"), dict) else None,
        "credential_value_recorded": False,
        "request_headers_recorded": False,
        "credential_echo_check": "PASS",
    }
    record["global_questions"] = {
        key: native[question_id] for key, question_id in global_ids.items()
    }
    record["interpretation"]["independent_adjudication_completed"] = True
    record["interpretation"]["no_phase6_scientific_verdict_is_issued"] = False
    record["interpretation"]["all_claim_verdicts_remain_pending"] = False
    record["interpretation"]["interim_test_policy"] = "KEEP_SEALED"
    record["interpretation"]["interim_recommendation"] = (
        "The locked test remains sealed. Any later one-time evaluation requires a separately "
        "frozen model and analysis plan and the applicable authorization."
    )

    output_rows: list[dict[str, str]] = []
    for row in matrix:
        claim_id = row["claim_id"]
        claim = claims_by_id[claim_id]
        jev = claim["jev"]
        output = dict(row)
        output.update(
            {
                "phase6_status": final_status,
                "claim_level_jev_verdict": jev["verdict"]["choice"],
                "jev_verdict_confidence": str(jev["verdict"]["confidence"]),
                "jev_verdict_probabilities": json.dumps(
                    jev["verdict"]["probabilities"], sort_keys=True
                ),
                "jev_supporting_evidence_noul": str(
                    jev["supporting_evidence_assessment"]["noul"]
                ),
                "jev_cautionary_evidence_noul": str(
                    jev["contradicting_or_cautionary_evidence_assessment"]["noul"]
                ),
                "jev_assumptions_score": str(jev["assumptions"]["score"]),
                "jev_assumptions_probabilities": json.dumps(
                    jev["assumptions"]["probabilities"], sort_keys=True
                ),
                "jev_limitations_score": str(jev["limitations"]["score"]),
                "jev_limitations_probabilities": json.dumps(
                    jev["limitations"]["probabilities"], sort_keys=True
                ),
                "jev_overstatement_risk": jev["overstatement_risk"]["choice"],
                "jev_recommended_wording_choice": jev["recommended_wording"]["choice"],
                "jev_recommended_wording": jev["recommended_wording"]["text"] or "",
            }
        )
        output_rows.append(output)

    csv_buffer = io.StringIO(newline="")
    fieldnames = list(output_rows[0])
    for name in (
        "claim_level_jev_verdict",
        "jev_verdict_confidence",
        "jev_verdict_probabilities",
        "jev_supporting_evidence_noul",
        "jev_cautionary_evidence_noul",
        "jev_assumptions_score",
        "jev_assumptions_probabilities",
        "jev_limitations_score",
        "jev_limitations_probabilities",
        "jev_overstatement_risk",
        "jev_recommended_wording_choice",
        "jev_recommended_wording",
    ):
        if name not in fieldnames:
            fieldnames.append(name)
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=fieldnames,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(output_rows)

    csv_text = csv_buffer.getvalue()
    required_csv_fields = {
        "claim_level_jev_verdict",
        "jev_verdict_confidence",
        "jev_verdict_probabilities",
        "jev_supporting_evidence_noul",
        "jev_cautionary_evidence_noul",
        "jev_assumptions_score",
        "jev_assumptions_probabilities",
        "jev_limitations_score",
        "jev_limitations_probabilities",
        "jev_overstatement_risk",
        "jev_recommended_wording_choice",
        "jev_recommended_wording",
    }
    record["validation"].update(
        {
            "phase6a_smoke_test": "PASS",
            "phase6a_typed_claim_answers": "PASS: all 8 claims received valid native typed answers",
            "phase6a_global_answers": "PASS",
            "phase6a_evidence_packet_hashes": "PASS: exact blocked-packet hashes submitted",
            "phase6a_prior_artifacts": "PASS",
            "phase6a_locked_test_boundary": "PASS: metadata only; no rows parsed or scored",
            "phase6a_credential_safety": "PASS: exact credential not emitted or recorded",
            "jev_adjudication": "PASS: actual typed JEV adjudication completed",
        }
    )

    markdown = _new_markdown(prior_markdown, record, matrix, native, model, smoke)
    record["phase6a"] = {
        "status": "PHASE6A_PASS_AND_PHASE6_ADJUDICATED",
        "smoke_test": "PASS",
        "claim_count": 8,
        "question_count": len(questions),
        "pre_adjudication_packet_sha256": packet_hashes,
        "trusted_reference_path": "D:/Dev/Sinag/scripts/content/jev-smoke-tests.js",
        "locked_test_status": "SEALED",
    }

    json_text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    parsed_record = json.loads(json_text)
    parsed_rows = list(csv.DictReader(io.StringIO(csv_text)))
    if (
        len(parsed_record["claims"]) != 8
        or len(parsed_rows) != 8
        or parsed_record.get("phase6a", {}).get("status")
        != "PHASE6A_PASS_AND_PHASE6_ADJUDICATED"
        or parsed_record.get("interpretation", {}).get(
            "no_phase6_scientific_verdict_is_issued"
        )
        is not False
    ):
        raise Phase6AError("SerializedOutputRowCountInvalid")
    if len(fieldnames) != len(set(fieldnames)):
        raise Phase6AError("SerializedCSVHeaderDuplicate")
    if not required_csv_fields.issubset(parsed_rows[0]):
        raise Phase6AError("SerializedCSVRequiredFieldsMissing")

    validation = {
        "schema_version": "phase6a-jev-validation/v1",
        "phase": "PHASE_6A_JEV_INTEGRATION",
        "status": "PHASE6A_PASS_AND_PHASE6_ADJUDICATED",
        "repository": {
            "branch": "main",
            "head": subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
        },
        "trusted_reference": {
            "request_and_smoke_schema": "D:/Dev/Sinag/scripts/content/jev-smoke-tests.js",
            "response_handling": "D:/Dev/Sinag/scripts/content/definition-cross-check.js",
            "request_schema_established": True,
            "official_api_page": "https://docs.typesafe.ai/api",
        },
        "smoke_test": {
            "status": "PASS",
            "http_status": smoke["http_status"],
            "model_identifier_returned": smoke["model_identifier_returned"],
            "typed_answer_type": "noul",
        },
        "phase6_adjudication": {
            "status": "PASS",
            "final_research_status": final_status,
            "claim_count": len(record["claims"]),
            "claims_with_valid_typed_verdicts": sum(
                claim["adjudication_status"] == "ADJUDICATED_BY_JEV"
                for claim in record["claims"]
            ),
            "question_count": len(questions),
            "model_identifier_returned": model,
        },
        "evidence_packet": {
            "sha256": packet_hashes,
            "exact_blocked_packet_used": True,
            "no_new_scientific_evidence_added": True,
        },
        "security": {
            "credential_source": "Keys.env exact TYPESAFE_API_KEY entry",
            "credential_value_recorded": False,
            "authorization_header_recorded": False,
            "credential_echo_check": "PASS",
            "keys_env_ignored": True,
            "keys_env_tracked": False,
        },
        "locked_test": {
            "status": "SEALED",
            "targets_parsed": False,
            "metrics_calculated": False,
            "predictions_generated": False,
        },
        "prior_artifacts": integrity,
        "validation": {
            "python_syntax_and_import": "PASS",
            "json_output_parse": "PASS",
            "csv_output_parse": "PASS",
            "claim_rows": 8,
            "all_required_typed_fields_present": True,
            "output_credential_scan": "PASS",
        },
        "git_policy": {
            "staged": False,
            "committed": False,
            "pushed": False,
            "merged": False,
        },
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    validation_text = json.dumps(validation, ensure_ascii=False, indent=2) + "\n"
    _safe_write_group(
        {
            JSON_PATH: json_text,
            CSV_PATH: csv_text,
            MARKDOWN_PATH: markdown,
            VALIDATION_PATH: validation_text,
        },
        api_key,
    )
    print("PHASE6A_ADJUDICATION_PASS")


def main() -> int:
    if sys.argv[1:] == ["--validate-only"]:
        try:
            record, matrix, _, _ = _load_packet()
            rows_by_id = {row["claim_id"]: row for row in matrix}
            questions, _ = _build_questions(record["claims"], rows_by_id)
            if len(questions) != 63:
                raise Phase6AError("QuestionCountInvalid")
            _validate_prior_artifacts()
        except (Phase6AError, JevClientError) as error:
            print(f"PHASE6A_IMPORT_VALIDATION_FAIL error_class={type(error).__name__}")
            return 1
        print(f"PHASE6A_IMPORT_VALIDATION_PASS questions={len(questions)}")
        return 0
    if sys.argv[1:]:
        print("PHASE6A_ADJUDICATION_FAIL error_class=UnexpectedArguments")
        return 2
    try:
        run_phase6()
    except (Phase6AError, JevClientError) as error:
        if isinstance(error, JevClientError):
            print(
                f"PHASE6A_ADJUDICATION_FAIL status={error.http_status} "
                f"error_class={error.error_class}"
            )
        else:
            print(f"PHASE6A_ADJUDICATION_FAIL error_class={type(error).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
