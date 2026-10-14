# CharterCompliance

[![GenLayer Network](https://img.shields.io/badge/GenLayer-StudioNet%20(61999)-4F46E5?style=flat-square)](https://studio.genlayer.com)
[![GenVM Runner](https://img.shields.io/badge/Runner-py--genlayer%3A1jb45aa8...-059669?style=flat-square)](https://github.com/genlayerlabs/genvm-manager)
[![Tests](https://img.shields.io/badge/pytest-4%20passed%20(100%25)-10B981?style=flat-square)](https://github.com/JimmyOgb/charter_compliance)
[![Linter](https://img.shields.io/badge/genvm--lint-0%20errors%2C%200%20warnings-brightgreen?style=flat-square)](https://github.com/JimmyOgb/charter_compliance)

> **Autonomous Constitutional Court and Execution Gate for DAOs on GenLayer.**

---

## 🏛️ Executive Summary

Decentralized Autonomous Organizations (DAOs) frequently establish governance charters and operational constitutions. However, enforcing these charters today suffers from critical systemic flaws:
- **Manual, off-chain review:** Slow, inconsistent, and susceptible to voter fatigue or political bribery.
- **Dumb execution gates:** Traditional smart contracts can only enforce static token tallies and cannot parse grant specifications, milestones, licensing requirements, or budget mandates.
- **Governance drift:** Unconstitutional proposals pass and drain treasuries without judicial review.

**CharterCompliance** is an Intelligent Contract deployed on GenLayer that serves as an autonomous, on-chain constitutional court and execution gate. It intercepts submitted proposals, subjects them to a deterministic fast-fail and an AI-powered substantive audit across independent consensus validators, and deterministically gates execution permissions.

---

## 🚀 Live StudioNet Deployment

| Parameter | Value |
| :--- | :--- |
| **Network** | GenLayer StudioNet (Chain ID: `61999`) |
| **Contract Address** | [`0x5b844791e0500BdE7D0daeA9F9150cFeeBE0B0F0`](https://genlayer-explorer.vercel.app/address/0x5b844791e0500BdE7D0daeA9F9150cFeeBE0B0F0) |
| **Deployment Transaction** | [`0x55ad3466a47bde7022c2f03e948d4a41e9f48845014c087ddf65dd90d112b495`](https://genlayer-explorer.vercel.app/tx/0x55ad3466a47bde7022c2f03e948d4a41e9f48845014c087ddf65dd90d112b495) |
| **Deployer Account** | `0xe4220c4b71877bb94eb173f467ef5c5557017085` |
| **Consensus Status** | `ACCEPTED` (Unanimous validator agreement) |
| **Pinned Runner Hash** | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |

---

## ⚙️ Architecture & Two-Stage Screening Pipeline

```
                              [Proposal Submitted]
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │   Stage 1: Deterministic Fast-Fail│
                     │   - Validates HTTPS scheme        │
                     │   - Checks max_single_budget_cap  │
                     └─────────────────┬─────────────────┘
                                       │
                      Violated? ───────┴─────── Compliant?
                         │                           │
                         ▼                           ▼
            ┌─────────────────────────┐   ┌───────────────────────────────────┐
            │ Immediate UNCONSTITUTIONAL│ │ Stage 2: Substantive Audit        │
            │ Risk Score = 100        │   │ (gl.vm.run_nondet_unsafe)         │
            │ (Zero LLM/Web Overhead) │   │ 1. Fetches spec via web.get       │
            └─────────────────────────┘   │ 2. Isolates <PROPOSAL_SPEC> tags  │
                                          │ 3. Non-deterministic LLM audit    │
                                          │ 4. Deterministic score & severity │
                                          └─────────────────┬─────────────────┘
                                                            │
                                              ┌─────────────┴─────────────┐
                                              ▼                           ▼
                                     [HARD Violation]            [REMEDIABLE Only]
                                     UNCONSTITUTIONAL             NEEDS_AMENDMENT
                                    is_executable: FALSE        is_executable: FALSE
                                                                          │
                                                                   [Up to 3 Revisions]
                                                                          │
                                              ┌───────────────────────────┘
                                              ▼
                                         [No Violations]
                                            COMPLIANT
                                       is_executable: TRUE
```

### 1. Stage 1 — Deterministic Fast-Fail (Zero LLM Overhead)
Deterministic rules execute in native WebAssembly without spinning up the nondet LLM pipeline:
- **`SCHEMA_HTTPS_REQUIRED`:** Enforces that proposal specifications are fetched over authenticated, encrypted TLS endpoints (`https://`).
- **`TREASURY_CAP_EXCEEDED`:** Proposals requesting an allocation exceeding `max_single_budget_cap` are rejected immediately with `risk_score = 100` and `hard_violation = True`.

### 2. Stage 2 — Substantive Constitutional Audit (`gl.vm.run_nondet_unsafe`)
When proposals pass Stage 1, validators execute an independent, comparative constitutional evaluation:
1. **Evidence Fetching:** The specification document is retrieved via `gl.nondet.web.get(spec_url)` and truncated to 8,000 characters to defend against resource exhaustion.
2. **Prompt Injection Defense:** External specification text is isolated inside `<PROPOSAL_SPEC>` XML tags with explicit instructions directing the model to treat the content as untrusted data.
3. **Structured Judicature:** The LLM identifies violated constitutional article IDs (`violated_ids`) and judicial reasoning (`opinion`).
4. **Deterministic Verdict Derivation:**
   - Valid article IDs are filtered against the stored canonical charter.
   - Integer arithmetic calculates `risk_score = min(100, sum(weights))`.
   - If any violated article has `severity == "HARD"` &rarr; `status = "UNCONSTITUTIONAL"`.
   - If violated articles are strictly `severity == "REMEDIABLE"` &rarr; `status = "NEEDS_AMENDMENT"`.
   - If no violations &rarr; `status = "COMPLIANT"` and `risk_score = 0`.

### 3. Leader-Validator Equivalence & Consensus Rule
Validators independently re-execute `leader_fn()` against their local web/LLM runtime. Consensus passes (`validator_fn == True`) if and only if:
1. `lead["status"] == val["status"]` (Exact agreement on classification).
2. `lead["hard_violation"] == val["hard_violation"]` (Exact agreement on constitutional severity).
3. `abs(int(lead["risk_score"]) - int(val["risk_score"])) <= 15` (Deterministic 15-point scoring tolerance).

---

## 🔄 Remediation & Constitutional Invalidation Lifecycle

### Multi-Round Remediation (`resubmit_amended_proposal`)
- Proposals flagged as `NEEDS_AMENDMENT` enter a structured remediation workflow.
- Proposers can address identified deficiencies (e.g., adding public GitHub repositories, milestone delivery schedules, or licensing disclosures) and submit amended specifications up to a maximum of 3 revisions.
- Upon successful remediation, the proposal is upgraded to `COMPLIANT`.

### Constitutional Invalidation Gate (`amend_charter`)
- The constitutional court is fully dynamic. When DAO members pass a constitutional amendment via `amend_charter(new_charter_json, new_max_budget_cap)`, the on-chain `charter_version` increments.
- **Instant Invalidation:** Any existing proposal previously deemed `COMPLIANT` immediately becomes non-executable (`is_executable(proposal_id) == False`).
- Proposals must be re-evaluated under the current constitution via `rescreen_proposal(proposal_id)` to regain execution rights.

---

## 📋 Smart Contract Interface

### State Variables
- `owner: Address` — Contract administrator and deployer.
- `max_single_budget_cap: u256` — Maximum budgetary threshold permitted for a single proposal.
- `charter_json: str` — Canonical JSON payload defining constitutional articles, severity levels, and weights.
- `charter_version: u256` — Monotonically increasing constitutional version counter.
- `proposals: TreeMap[str, str]` — Persistent storage mapping `proposal_id` to its serialized JSON evaluation record.

### Public Write Methods (`@gl.public.write`)
| Method | Parameters | Return | Description |
| :--- | :--- | :--- | :--- |
| `screen_proposal` | `proposal_id: str, title: str, requested_budget: int, spec_url: str` | `str` | Screens an initial proposal through the two-stage pipeline. |
| `submit_proposal` | `proposal_id: str, title: str, requested_budget: int, spec_url: str` | `str` | Alias for `screen_proposal`. |
| `resubmit_amended_proposal` | `proposal_id: str, new_requested_budget: int, new_spec_url: str` | `str` | Submits an amended proposal (max 3 revisions). |
| `rescreen_proposal` | `proposal_id: str` | `str` | Re-evaluates an existing proposal against the active charter version. |
| `amend_charter` | `new_charter_json: str, new_max_budget_cap: int` | `int` | Amends the constitution, updates treasury cap, increments version. |

### Public View Methods (`@gl.public.view`)
| Method | Parameters | Return | Description |
| :--- | :--- | :--- | :--- |
| `is_executable` | `proposal_id: str` | `bool` | Returns `True` iff proposal is `COMPLIANT` under the active `charter_version`. |
| `get_proposal` | `proposal_id: str` | `str` | Returns the raw serialized JSON evaluation record. |
| `get_charter_state` | *none* | `str` | Returns JSON of `charter_version`, `max_single_budget_cap`, and `articles`. |

---

## 🧪 Testing & Verification

The test suite `tests/test_charter_compliance_direct.py` leverages `gltest` in-memory direct mode:

```bash
pytest tests/test_charter_compliance_direct.py -v
```

### Verified Test Cases:
1. `test_deterministic_budget_cap_fast_fail`
   - Validates that requests exceeding `max_single_budget_cap` return `UNCONSTITUTIONAL` with risk score 100.
   - Asserts zero web or LLM mocks were consumed during execution.
2. `test_remediable_violation_and_amendment_upgrade`
   - Flags remediable violation `A2` (weight 40).
   - Verifies proposal cannot be executed.
   - Resubmits amended specification and validates status flips to `COMPLIANT` (`revision_count = 1`, `is_executable = True`).
3. `test_charter_amendment_invalidates_stale_compliance`
   - Asserts a `COMPLIANT` proposal becomes immediately unexecutable (`is_executable == False`) after `amend_charter`.
   - Confirms re-screening restores `is_executable == True` under charter version 2.
4. `test_validator_consensus_agreement_and_disagreement`
   - Simulates consensus agreement across independent runs within the 15-point tolerance band.
   - Simulates consensus disagreement when status, severity, or scores diverge.

---

## 🛠️ Developer Quickstart

### Prerequisites
- Python 3.12+
- Node.js 18+ and `genlayer` CLI (`npm install -g genlayer`)
- `genvm-linter` (`pip install genvm-linter`)
- `genlayer-test` (`pip install genlayer-test`)

### 1. Static Analysis
Run static AST safety checks and SDK semantic validation:
```bash
genvm-lint check contracts/charter_compliance.py
```
*Expected: 0 errors, 0 warnings.*

### 2. Run Direct Tests
```bash
pytest tests/test_charter_compliance_direct.py -v
```
*Expected: 4 passed in ~30s.*

### 3. Deploy to StudioNet
```bash
genlayer network set studionet
genlayer deploy --contract contracts/charter_compliance.py --args 50000 '[{"id":"A1","rule":"All grants must fund open-source tooling.","severity":"HARD","weight":60},{"id":"A2","rule":"Proposals over 1000 units must include a public GitHub repo and milestone schedule.","severity":"REMEDIABLE","weight":40}]'
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
