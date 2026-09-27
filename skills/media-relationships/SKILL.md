---
name: media-relationships
description: Read and manage publication conversations, contextual replies, useful outside contributions and follow-up commitments.
---

# Relationships, Community and Conversations

Read [operating boundaries](../../policies/CONSTITUTION.md) and [handoff rules](../../contracts/HANDOFF.md). Use only the current task’s required inputs and references.

## Understand the exchange
For inbound work retrieve the actual root content, relevant ancestors, newest messages and prior responses. Persist received events before advancing checkpoints; deduplicate webhook/poll copies by their actual source identifiers. Mark missing context or listening gaps. Do not infer that nobody commented because retrieval failed.

Classify the message's purpose: question, correction, feedback, appreciation, complaint, invitation or another supported intent. Decide answer, investigate, clarify, acknowledge, escalate or no response according to usefulness and the owner's policy. Research factual questions; route a credible correction to Editorial and Publishing. Never fabricate personal experience or familiarity.

For outside participation, read the actual work and identify a concrete contribution valuable to its author/readers. Check relevance, receptivity, applicable permission, history and opt-outs independently. No compulsory link back, generic praise campaign, reciprocal-comment pact or contact quota. Unknown contact permission permits preparation, not assumed sending.

## Dispatch and continue
Draft to the correct parent with the context needed to make the response meaningful. Use bounded standing authorization when applicable. Immediately before sending, refresh conversation and human/agent ownership, verify the target still exists, enforce per-person and bot-loop stopping limits and revalidate platform policy. A recent human answer may make a queued response unnecessary. Use Publishing for writes and actual confirmation.

Retain minimal private ConversationState: account/root/parent/message identifiers, source context, permission and opt-out, actual responses, ownership, pending actions, commitments and checkpoint. Do not merge people across platforms from names alone. Apply the configured retention policy.

Check later replies and commitments independently of new article publication. Continue only when there is useful work, stop on refusal, and avoid repeated nudges. Return EngagementDecision, actual or prepared response state and follow-up conditions. Feed recurring confusion, missed responses and useful exchanges into research/editorial/growth; message count is not relationship quality.

## Inputs and outputs

Inputs: Publication intent and relevant GrowthPlan / RankedTargetSet; Authorized contact or community information; Interaction history and permission state; ConversationState; ChannelCapability records; OperationQueueItem; Relevant root/ancestor content.

Outputs: RelationshipPlan; Reviewed interaction drafts; Contact-state and interaction records; EngagementDecision; Updated ConversationState; Follow-up and escalation work orders.

## Completion and learning

Check the delivered result against the current brief and the relevant evidence, technical and permission criteria above. Retain concise evidence of what worked, failed or remains unavailable in the private run record. Use media-learning for a justified reusable adaptation; current-output repairs do not automatically change the method.
