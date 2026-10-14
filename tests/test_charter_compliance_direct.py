import json
import pytest

INITIAL_CHARTER = json.dumps([
    {
        "id": "A1",
        "rule": "All grants must fund open-source tooling.",
        "severity": "HARD",
        "weight": 60,
    },
    {
        "id": "A2",
        "rule": "Proposals over 1000 units must include a public GitHub repo and milestone schedule.",
        "severity": "REMEDIABLE",
        "weight": 40,
    },
])


def test_deterministic_budget_cap_fast_fail(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/charter_compliance.py", 50000, INITIAL_CHARTER)

    res_json = contract.screen_proposal(
        "PROP-CAP-EXCEEDED",
        "Ecosystem Super Grant",
        75000,
        "https://dao.example.com/proposals/large-grant",
    )
    res = json.loads(res_json)

    assert res["status"] == "UNCONSTITUTIONAL"
    assert res["risk_score"] == 100
    assert res["hard_violation"] is True
    assert res["violated_ids"] == ["TREASURY_CAP_EXCEEDED"]
    assert "exceeds max_single_budget_cap" in res["opinion"]
    assert contract.is_executable("PROP-CAP-EXCEEDED") is False

    # Confirm no external web or LLM mocks were consumed
    assert len(direct_vm._web_mocks_hit) == 0
    assert len(direct_vm._llm_mocks_hit) == 0


def test_remediable_violation_and_amendment_upgrade(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/charter_compliance.py", 50000, INITIAL_CHARTER)

    # Initial submission: violates A2 (REMEDIABLE)
    direct_vm.mock_web(
        r"https://dao\.example\.com/proposals/dev-tool-v1",
        {"status": 200, "body": "Developer tooling proposal without repo milestones."},
    )
    direct_vm.mock_llm(
        r".*",
        json.dumps({
            "violated_ids": ["A2"],
            "opinion": "Missing public repository and milestone delivery schedule.",
        }),
    )

    res1_json = contract.screen_proposal(
        "PROP-REMEDIABLE-01",
        "Developer Tooling Suite",
        10000,
        "https://dao.example.com/proposals/dev-tool-v1",
    )
    res1 = json.loads(res1_json)

    assert res1["status"] == "NEEDS_AMENDMENT"
    assert res1["risk_score"] == 40
    assert res1["hard_violation"] is False
    assert res1["violated_ids"] == ["A2"]
    assert contract.is_executable("PROP-REMEDIABLE-01") is False

    # Resubmit amended proposal with compliant disclosures
    direct_vm.clear_mocks()
    direct_vm.mock_web(
        r"https://dao\.example\.com/proposals/dev-tool-v2",
        {"status": 200, "body": "Updated specification with public repo and quarterly milestones."},
    )
    direct_vm.mock_llm(
        r".*",
        json.dumps({
            "violated_ids": [],
            "opinion": "All milestone and repo disclosures satisfied.",
        }),
    )

    res2_json = contract.resubmit_amended_proposal(
        "PROP-REMEDIABLE-01",
        10000,
        "https://dao.example.com/proposals/dev-tool-v2",
    )
    res2 = json.loads(res2_json)

    assert res2["status"] == "COMPLIANT"
    assert res2["risk_score"] == 0
    assert res2["hard_violation"] is False
    assert res2["violated_ids"] == []
    assert res2["revision_count"] == 1
    assert contract.is_executable("PROP-REMEDIABLE-01") is True


def test_charter_amendment_invalidates_stale_compliance(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/charter_compliance.py", 50000, INITIAL_CHARTER)

    # Establish an initially COMPLIANT proposal under charter version 1
    direct_vm.mock_web(
        r"https://dao\.example\.com/proposals/open-source-lib",
        {"status": 200, "body": "Open-source library with repository and milestones."},
    )
    direct_vm.mock_llm(
        r".*",
        json.dumps({
            "violated_ids": [],
            "opinion": "Fully compliant with version 1 charter.",
        }),
    )

    res1_json = contract.screen_proposal(
        "PROP-AMENDMENT-01",
        "Open Source Library",
        5000,
        "https://dao.example.com/proposals/open-source-lib",
    )
    res1 = json.loads(res1_json)
    assert res1["status"] == "COMPLIANT"
    assert contract.is_executable("PROP-AMENDMENT-01") is True

    # Amend charter to version 2
    updated_charter = json.dumps([
        {
            "id": "A1",
            "rule": "All grants must fund open-source tooling.",
            "severity": "HARD",
            "weight": 60,
        },
        {
            "id": "A2",
            "rule": "Proposals over 1000 units must include a public GitHub repo and milestone schedule.",
            "severity": "REMEDIABLE",
            "weight": 40,
        },
        {
            "id": "A3",
            "rule": "Proposals must include an independent third-party audit report.",
            "severity": "HARD",
            "weight": 50,
        },
    ])

    new_version = contract.amend_charter(updated_charter, 60000)
    assert new_version == 2

    # Compliant status is immediately invalidated by charter version mismatch
    assert contract.is_executable("PROP-AMENDMENT-01") is False

    # Re-screen under version 2
    res2_json = contract.rescreen_proposal("PROP-AMENDMENT-01")
    res2 = json.loads(res2_json)
    assert res2["charter_version_checked"] == 2
    assert res2["status"] == "COMPLIANT"
    assert contract.is_executable("PROP-AMENDMENT-01") is True


def test_validator_consensus_agreement_and_disagreement(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/charter_compliance.py", 50000, INITIAL_CHARTER)

    # Setup proposal evaluated by leader as NEEDS_AMENDMENT with risk_score = 40
    spec_url = "https://dao.example.com/proposals/consensus-check"
    direct_vm.mock_web(
        r"https://dao\.example\.com/proposals/consensus-check",
        {"status": 200, "body": "Consensus test specification body."},
    )
    direct_vm.mock_llm(
        r".*",
        json.dumps({
            "violated_ids": ["A2"],
            "opinion": "Missing milestone schedule.",
        }),
    )

    contract.screen_proposal(
        "PROP-CONSENSUS-01",
        "Consensus Evaluation Proposal",
        8000,
        spec_url,
    )

    # 1. Consensus Agreement:
    # Validator re-runs leader_fn independently and reaches identical verdict
    agree_exact = direct_vm.run_validator()
    assert agree_exact is True

    # Tolerance band agreement: leader score within 15 points (e.g. 35 vs 40)
    agree_tolerance = direct_vm.run_validator(
        leader_result={
            "status": "NEEDS_AMENDMENT",
            "risk_score": 35,
            "hard_violation": False,
            "violated_ids": ["A2"],
            "opinion": "Close evaluation within tolerance band.",
        }
    )
    assert agree_tolerance is True

    # 2. Consensus Disagreement:
    # Disagreement Case A: Leader classifies as COMPLIANT while validator flags A1 (UNCONSTITUTIONAL)
    direct_vm.clear_mocks()
    direct_vm.mock_web(
        r"https://dao\.example\.com/proposals/consensus-check",
        {"status": 200, "body": "Consensus test specification body."},
    )
    direct_vm.mock_llm(
        r".*",
        json.dumps({
            "violated_ids": ["A1"],
            "opinion": "Violates open-source mandate (A1 HARD).",
        }),
    )

    disagree_status = direct_vm.run_validator(
        leader_result={
            "status": "COMPLIANT",
            "risk_score": 0,
            "hard_violation": False,
            "violated_ids": [],
            "opinion": "Leader found no violations.",
        }
    )
    assert disagree_status is False

    # Disagreement Case B: Score difference > 15 tolerance (e.g., leader 10 vs validator 60)
    disagree_score = direct_vm.run_validator(
        leader_result={
            "status": "UNCONSTITUTIONAL",
            "risk_score": 10,
            "hard_violation": True,
            "violated_ids": ["A1"],
            "opinion": "Score disparity beyond 15 points.",
        }
    )
    assert disagree_score is False
