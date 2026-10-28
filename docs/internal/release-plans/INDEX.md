# Release Plan Index

Generated file. Regenerate with `python scripts/gen-release-index.py` from the repository root. Hand edits will be overwritten on the next regeneration.

**Releases:** 5 **Efforts:** 23 (15 unassigned) **Source:** every `plan.md` and `spec.md` under `docs/internal/release-plans/`, including `_unassigned/`, plus each effort's `implementation-plan.md` where present

---

## Series Legend

Every effort id's letter prefix names which series it belongs to. An id whose letter is not listed here is a generator bug, not a rendering gap: the generator refuses to run rather than leave the meaning blank.

| Letter | Meaning |
|---|---|
| D | defect in the wrap and continue pair |
| W | wrap-session roadmap item |
| C | continue-session roadmap item |
| CI | continuous integration |
| A | ai-review roadmap item |
| H | hygiene and repo-wide |
| AU | audit-skill roadmap item |
| WD | resolve-open-items roadmap item |
| CS | current-status roadmap item |

---

## Summary by Release

| Release | Target Version | Theme | Efforts | Spec Statuses | Implementation Plan Statuses |
|---|---|---|---|---|---|
| [plan_04_gates-that-cannot-fail-open](plan_04_gates-that-cannot-fail-open/plan.md) | v0.4.0 | Gates that cannot fail open | 8 | fulfilled: 8 | complete: 8 |
| [plan_05_reconcile-at-resume](plan_05_reconcile-at-resume/plan.md) | v0.6.0 | Reconcile at resume | 0 |  |  |
| [plan_06_derived-facts](plan_06_derived-facts/plan.md) | v0.7.0 | Derived facts | 0 |  |  |
| [plan_07_aggregation](plan_07_aggregation/plan.md) | v0.8.0 | Aggregation | 0 |  |  |
| [plan_08_escape-and-measure](plan_08_escape-and-measure/plan.md) | v0.9.0 | Escape and measure | 0 |  |  |
| **Total (assigned to a release)** | | | **8** | fulfilled: 8 | complete: 8 |

---

## Unassigned Efforts

Specs written before being assigned to a release: the documented default home `/plab-spec` writes into when `--target-release` is omitted (`docs/internal/release-plans/_unassigned/`). These carry no target version until `/plab-release-plan --promote` moves the whole effort folder into a release. `_unassigned/` does not exist on disk until the first spec is written there; its absence is normal, not an error.

| Effort | Handle | Series | Spec Status | Implementation Plan Status | Priority | Human Review Required |
|---|---|---|---|---|---|---|
| [A-02](_unassigned/A-02_programmatic-review-dispatch/spec.md) | programmatic review dispatch | A (ai-review roadmap item) | committed | complete | P1 | No |
| [AU-01](_unassigned/AU-01_audit-skill/spec.md) | audit skill | AU (audit-skill roadmap item) | committed | in-progress | P1 | No |
| [C-02](_unassigned/C-02_reconcile-at-resume/spec.md) | reconcile at resume | C (continue-session roadmap item) | committed | complete | P1 | Yes |
| [C-03](_unassigned/C-03_cold-repo-degradation/spec.md) | cold repo degradation | C (continue-session roadmap item) | draft | draft | P2 | Yes |
| [C-04](_unassigned/C-04_consumption-disposition/spec.md) | consumption disposition | C (continue-session roadmap item) | draft | draft | P2 | No |
| [C-05](_unassigned/C-05_arc-resume/spec.md) | arc resume | C (continue-session roadmap item) | draft | draft | P2 | No |
| [CS-01](_unassigned/CS-01_current-status/spec.md) | current status | CS (current-status roadmap item) | committed | complete | P2 | Yes |
| [D-10](_unassigned/D-10_log-format-contract/spec.md) | log format contract | D (defect in the wrap and continue pair) | draft | draft | P2 | No |
| [H-05](_unassigned/H-05_retire-dash-enforcement/spec.md) | retire dash enforcement | H (hygiene and repo-wide) | draft | (no implementation plan yet) | P3 | Yes |
| [H-06](_unassigned/H-06_optional-release-plan-version/spec.md) | optional release plan version | H (hygiene and repo-wide) | draft | (no implementation plan yet) | P3 | Yes |
| [W-02](_unassigned/W-02_derived-log-facts/spec.md) | derived log facts | W (wrap-session roadmap item) | committed | in-progress | P1 | No |
| [W-03](_unassigned/W-03_waiting-on-escapes-gitignore/spec.md) | waiting on escapes gitignore | W (wrap-session roadmap item) | draft | draft | P2 | Yes |
| [W-04](_unassigned/W-04_digest-mode/spec.md) | digest mode | W (wrap-session roadmap item) | draft | draft | P2 | Yes |
| [WD-01](_unassigned/WD-01_resolve-open-items/spec.md) | resolve open items | WD (resolve-open-items roadmap item) | fulfilled | complete | P2 | Yes |
| [WD-02](_unassigned/WD-02_backlog-sweep/spec.md) | backlog sweep | WD (resolve-open-items roadmap item) | committed | complete | P2 | Yes |

---

## All Efforts

One row per effort, grouped by release in sequence order (see the Release column), with unassigned efforts listed last.

| Effort | Handle | Series | Spec Status | Implementation Plan Status | Release | Target Version | Priority | Human Review Required |
|---|---|---|---|---|---|---|---|---|
| [CI-01](plan_04_gates-that-cannot-fail-open/CI-01_ci-bootstrap/spec.md) | ci bootstrap | CI (continuous integration) | fulfilled | complete | [plan_04_gates-that-cannot-fail-open](plan_04_gates-that-cannot-fail-open/plan.md) | v0.4.0 | P1 | No |
| [D-03](plan_04_gates-that-cannot-fail-open/D-03_bidirectional-drift-check/spec.md) | bidirectional drift check | D (defect in the wrap and continue pair) | fulfilled | complete | [plan_04_gates-that-cannot-fail-open](plan_04_gates-that-cannot-fail-open/plan.md) | v0.4.0 | P1 | Yes |
| [D-04](plan_04_gates-that-cannot-fail-open/D-04_capture-lite-consumers/spec.md) | capture lite consumers | D (defect in the wrap and continue pair) | fulfilled | complete | [plan_04_gates-that-cannot-fail-open](plan_04_gates-that-cannot-fail-open/plan.md) | v0.4.0 | P2 | Yes |
| [D-05](plan_04_gates-that-cannot-fail-open/D-05_superseding-logs/spec.md) | superseding logs | D (defect in the wrap and continue pair) | fulfilled | complete | [plan_04_gates-that-cannot-fail-open](plan_04_gates-that-cannot-fail-open/plan.md) | v0.4.0 | P2 | Yes |
| [D-06](plan_04_gates-that-cannot-fail-open/D-06_resumed-from-semantics/spec.md) | resumed from semantics | D (defect in the wrap and continue pair) | fulfilled | complete | [plan_04_gates-that-cannot-fail-open](plan_04_gates-that-cannot-fail-open/plan.md) | v0.4.0 | P3 | No |
| [D-07](plan_04_gates-that-cannot-fail-open/D-07_waiting-on-blocker-contract/spec.md) | waiting on blocker contract | D (defect in the wrap and continue pair) | fulfilled | complete | [plan_04_gates-that-cannot-fail-open](plan_04_gates-that-cannot-fail-open/plan.md) | v0.4.0 | P1 | Yes |
| [D-11](plan_04_gates-that-cannot-fail-open/D-11_three-state-gate-canaries/spec.md) | three state gate canaries | D (defect in the wrap and continue pair) | fulfilled | complete | [plan_04_gates-that-cannot-fail-open](plan_04_gates-that-cannot-fail-open/plan.md) | v0.4.0 | P1 | Yes |
| [D-12](plan_04_gates-that-cannot-fail-open/D-12_path-citation-precision/spec.md) | path citation precision | D (defect in the wrap and continue pair) | fulfilled | complete | [plan_04_gates-that-cannot-fail-open](plan_04_gates-that-cannot-fail-open/plan.md) | v0.4.0 | P2 | Yes |
| [A-02](_unassigned/A-02_programmatic-review-dispatch/spec.md) | programmatic review dispatch | A (ai-review roadmap item) | committed | complete | `_unassigned/` | - | P1 | No |
| [AU-01](_unassigned/AU-01_audit-skill/spec.md) | audit skill | AU (audit-skill roadmap item) | committed | in-progress | `_unassigned/` | - | P1 | No |
| [C-02](_unassigned/C-02_reconcile-at-resume/spec.md) | reconcile at resume | C (continue-session roadmap item) | committed | complete | `_unassigned/` | - | P1 | Yes |
| [C-03](_unassigned/C-03_cold-repo-degradation/spec.md) | cold repo degradation | C (continue-session roadmap item) | draft | draft | `_unassigned/` | - | P2 | Yes |
| [C-04](_unassigned/C-04_consumption-disposition/spec.md) | consumption disposition | C (continue-session roadmap item) | draft | draft | `_unassigned/` | - | P2 | No |
| [C-05](_unassigned/C-05_arc-resume/spec.md) | arc resume | C (continue-session roadmap item) | draft | draft | `_unassigned/` | - | P2 | No |
| [CS-01](_unassigned/CS-01_current-status/spec.md) | current status | CS (current-status roadmap item) | committed | complete | `_unassigned/` | - | P2 | Yes |
| [D-10](_unassigned/D-10_log-format-contract/spec.md) | log format contract | D (defect in the wrap and continue pair) | draft | draft | `_unassigned/` | - | P2 | No |
| [H-05](_unassigned/H-05_retire-dash-enforcement/spec.md) | retire dash enforcement | H (hygiene and repo-wide) | draft | (no implementation plan yet) | `_unassigned/` | - | P3 | Yes |
| [H-06](_unassigned/H-06_optional-release-plan-version/spec.md) | optional release plan version | H (hygiene and repo-wide) | draft | (no implementation plan yet) | `_unassigned/` | - | P3 | Yes |
| [W-02](_unassigned/W-02_derived-log-facts/spec.md) | derived log facts | W (wrap-session roadmap item) | committed | in-progress | `_unassigned/` | - | P1 | No |
| [W-03](_unassigned/W-03_waiting-on-escapes-gitignore/spec.md) | waiting on escapes gitignore | W (wrap-session roadmap item) | draft | draft | `_unassigned/` | - | P2 | Yes |
| [W-04](_unassigned/W-04_digest-mode/spec.md) | digest mode | W (wrap-session roadmap item) | draft | draft | `_unassigned/` | - | P2 | Yes |
| [WD-01](_unassigned/WD-01_resolve-open-items/spec.md) | resolve open items | WD (resolve-open-items roadmap item) | fulfilled | complete | `_unassigned/` | - | P2 | Yes |
| [WD-02](_unassigned/WD-02_backlog-sweep/spec.md) | backlog sweep | WD (resolve-open-items roadmap item) | committed | complete | `_unassigned/` | - | P2 | Yes |

