---
name: media-relationships
description: Read and manage publication conversations with brief, warm, context-specific comments, likes and replies. Use for inbox checks, outside engagement and continuing conversations.
---

# Relationships, Community and Conversations

Read [operating boundaries](../../policies/CONSTITUTION.md) and [handoff rules](../../contracts/HANDOFF.md). Use only the current task’s required inputs and references.

## Understand the exchange
For inbound work retrieve the actual root content, relevant ancestors, newest messages and prior responses. Persist received events before advancing checkpoints; deduplicate webhook/poll copies by their actual source identifiers. Mark missing context or listening gaps. Do not infer that nobody commented because retrieval failed.

Classify the message's purpose: question, correction, feedback, appreciation, complaint, invitation or another supported intent. Decide answer, investigate, clarify, acknowledge, escalate or no response according to the person's intent, conversational fit and the owner's policy. Warmth and shared enjoyment can justify an initial comment; they do not, by themselves, justify another reply after the publication has already spoken. Research factual questions; route a credible correction to Editorial and Publishing. Never fabricate personal experience or familiarity.

For outside participation, read the actual work and existing conversation. Identify something specific the person said, showed or expressed that warrants a natural response. Check relevance, receptivity, applicable permission, history and opt-outs independently. No compulsory link back, generic praise campaign, reciprocal-comment pact or contact quota. Unknown contact permission permits preparation, not assumed sending.

## Keep the exchange brief and human
For proactive engagement comments, read [recipient attention and publication voice](references/friendly-engagement.md) and the actual approved publication voice guide. Say something nice the recipient would appreciate about the work you read. Default to one short sentence of specific, truthful appreciation; two short sentences only when more natural for this exchange. Keep it warm, friendly and modest in the publication's voice and the conversation's language. Center one actual detail or explicitly stated thought or feeling. Appreciation is a complete interaction and does not need to be useful advice.

Do not add unsolicited advice, analysis, corrections, resources, source links, questions or interrogation, self-promotion or a call to action to a proactive comment. Do not introduce it with same-operator disclosure or other boilerplate. This style applies to routine cross-publication engagement too. Preserve truthful account ownership and material relationships; never pretend to be an independent reader or offer a fake independent endorsement. Do not invent personal experience, familiarity, private feelings or actions, including saying something was tried when it was only read. Avoid excessive praise, overfamiliarity and intrusive observations.

For an inbound question, concrete request or material correction, respond to the actual need and use only the detail needed to answer it. Default other casual replies to one short sentence. Do not turn an initial appreciation comment into an unsolicited consultation or ask a question to prolong the exchange.

Like the posts or comments receiving a positive response from the publication. Check and read people's replies, and like appropriate ones. Unless the recipient clearly wants to carry on the conversation, use that like as the final acknowledgment and end the exchange. Default to one publication comment or reply per conversational exchange, across runs rather than per day. Let the other person have the last word. Do not send a further closing reply, thank-you-for-the-thanks, renewed compliment or question merely to maintain contact. Send another brief reply only when the newest message clearly invites further conversation through a direct question, a concrete request, an explicit invitation to continue, a material correction or another substantive unresolved point, and a response fits that invitation or need. Before drafting, identify the exact invitation or unresolved point and check that it has not already been answered. A like does not replace a warranted answer; appreciation or conversational warmth alone is not such a reason. Check the existing like state before acting so a retry cannot remove it. Use judgment if a like would misrepresent agreement, and do not like the publication's own replies or manufacture a back-and-forth.

Before sending, check that the response is grounded in the actual content, easy to understand, brief for its purpose and comfortable to receive from a stranger. Remove anything that makes ordinary friendliness sound like a pitch, a performance or unwanted familiarity.

## Dispatch and continue
Draft to the correct parent with the context needed to make the response meaningful. Apply current task or bounded standing authorization; an explicitly requested engagement run is not automatically draft-only. Immediately before sending, refresh conversation and human/agent ownership, verify the target still exists, enforce per-person and bot-loop stopping limits and revalidate platform policy. A recent human answer may make a queued response unnecessary. Use Publishing for writes and actual confirmation, including likes; report exact sent text and destination separately from unsent drafts.

Retain minimal private ConversationState: account/root/parent/message identifiers, source context, permission and opt-out, actual responses, ownership, publication response count for the exchange, exact unresolved point (if any), closure status, pending actions, commitments and checkpoint. Do not merge people across platforms from names alone. Apply the configured retention policy.

When research or an audit discovers a new reply, persist its source identifiers, context and disposition even if sending is outside the current task. Do not automatically create pending textual follow-up for every incoming message. Keep observed/read, acknowledged and replied states separate; viewing alone is not acknowledgment, but an appropriate like or deliberate no-response decision can close the exchange. Record the close reason and no pending reply; do not reopen it on a later run unless a new clear invitation to continue or substantive unresolved point arrives. Before the next authorized response, reconcile the saved item against the current conversation, prior receipts and human activity, then reply, acknowledge or close it according to the exchange. Deduplicate discoveries across listening and research so the same reply cannot produce duplicate actions.

Check notifications, mentions, comments on the publication's work, replies to its outside comments and outstanding commitments on each authorized listening run, independently of new article publication. Prioritize unanswered conversation, including friendly replies that invite acknowledgment. Apply the one-response default and substantive-answer exception above; apparent friendliness is not permission for repeated replies. Daily reply allowances are ceilings, never reasons to continue a closed exchange. Stop on refusal or natural closure, and avoid repeated nudges. Save the checkpoint and follow-up conditions without starting an unrequested recurring job. Return EngagementDecision and actual or prepared response state. Feed recurring confusion, missed responses and meaningful exchanges into research/editorial/growth; message count is not relationship quality.

## Inputs and outputs

Inputs: Publication intent and relevant GrowthPlan / RankedTargetSet; Authorized contact or community information; Interaction history and permission state; ConversationState; ChannelCapability records; OperationQueueItem; Relevant root/ancestor content.

Outputs: RelationshipPlan; Reviewed interaction drafts; Contact-state and interaction records; EngagementDecision; Updated ConversationState; Follow-up and escalation work orders.

## Completion and learning

Check the delivered result against the current brief and the relevant evidence, technical and permission criteria above. Retain concise evidence of what worked, failed or remains unavailable in the private run record. Use media-learning for a justified reusable adaptation; current-output repairs do not automatically change the method.
