# Outcome verification

This procedure governs main's orchestration. Verifier's role definition governs how it checks a claim and reports CONFIRMED, REFUTED or INCONCLUSIVE.

Resolve the active review mode as in [plan review](plan-review.md). In auto, completed work that met a plan-review trigger gets outcome verification before main reports it complete; an explicit user request applies in either mode. Plan review checks the plan before work starts; outcome verification checks the result, so one does not replace the other.

1. Verify at the smallest integration boundary where the whole claim can be refuted, after main has run the primary acceptance itself. Tests and builds are evidence for the verifier, not a substitute for it.
2. Use verifier, under its installed native name, in fresh native context. Supply the exact claim, its acceptance checks, the relevant diff or paths and the commands main ran. If fresh context or the role is unavailable, report the limitation and keep completion of the affected claim blocked.
3. Allow at most two automatic verification calls per claim, including failed or interrupted calls. Changing verifier, model or wording does not reset the count. A missing verdict or protocol failure is not CONFIRMED.
4. On REFUTED, reproduce the failure and disposition each finding as FIX, correcting it within the authorized scope, or REJECT with concrete evidence: a failed reproduction, a source citation or the claim's own scope, never preference. Use the second call to recheck the original failure plus a bounded regression check, and send it each rejection with its evidence. The verifier may uphold a rejection; an upheld finding can be rejected again only with new evidence. Never resubmit unchanged work unless every remaining finding carries rejection evidence.
5. On INCONCLUSIVE, use the second call only after the named missing evidence, prerequisite or environment has changed; otherwise report the claim unverified.
6. With CONFIRMED, continue to completion under the existing authority. The verdict grants no new authority and main still accepts the whole task. After two calls without CONFIRMED, stop automatic verification, report the claim as unverified with the findings, and require an explicit user request for another call. Preserve the count and open findings in the task and any existing active handoff.

A verifier can still write through Bash; its no-edit rule is an instruction. Compare the workspace with the pre-dispatch state after each call and preserve or report any change it made.
