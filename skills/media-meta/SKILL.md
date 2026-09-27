---
name: media-meta
description: Review recurring cross-skill failures and improve media coordination or evaluation through bounded system experiments.
---

# Meta / Improvement-System Review

Read [operating boundaries](../../policies/CONSTITUTION.md) and [handoff rules](../../contracts/HANDOFF.md). Use only the current task’s required inputs and references.

## Method
Aggregate actual run failures, costs, handoff defects, experiment decisions and outcomes within the authorized scope. Identify patterns that span capabilities: lost evidence, duplicated work, missing interfaces, queue bottlenecks, poor experiments or evaluator disagreement. Do not assume every failure can be repaired by adding another prompt rule.

Locate the responsible layer and compare plausible causes. Separate coordination/resource changes from changes to evaluation and protected objectives. Prioritize experiments by plausible benefit, evidence, cost and ability to detect harm; retain exploration where repeatedly optimizing a narrow proxy would miss the objective.

Propose a bounded system change with an unchanged comparison, explicit budget/stop condition, relevant transfer cases and rollback. The candidate proposer must not control the final protected evaluator or edit expected answers. Record contamination and independence limits.

Return MetaReview and a justified experiment backlog, including no-change or insufficient-evidence conclusions. Reuse Learning for comparisons and publication-local adaptations. Shared coordination or evaluator changes require separate maintainer approval/versioning; cannot silently affect every publication.

Check whether an accepted change prevents the predicted subsequent failure and whether its cost is justified. Preserve failed experiments and retractions. Stop recursive improvement when the authorized question is resolved or budget exhausted; do not create an endless self-rewrite loop or mandatory optimizer stack.

## Inputs and outputs

Inputs: Cross-run and cross-skill evidence; Experiment and release history; Budget, objectives and protected evaluation policy.

Outputs: MetaReview; System-level ChangeProposal; Prioritized experiment backlog.

## Completion and learning

Check the delivered result against the current brief and the relevant evidence, technical and permission criteria above. Retain concise evidence of what worked, failed or remains unavailable in the private run record. Use media-learning for a justified reusable adaptation; current-output repairs do not automatically change the method.
