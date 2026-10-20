# Delegation dedupe: condition inventory

Baseline: `f4671bd`. Spec: [delegation-dedupe.md](delegation-dedupe.md), revised after the security analysis F1–F16. This inventory was written read-only by an analyst who does not implement the Runtime part. No file changed and no code ran. It is part of the plan, an appendix the spec's tickets cite by section. Its baseline columns, sections 0–6 and the Id and Baseline owner columns of section 7, stay fixed after the last plan review before implementation (T1). It lists only the rules this work consolidates; every rule it does not list keeps its baseline text and place (spec item 1 and item 7). After the Runtime part the verifier copies section 7's table into `docs/specs/delegation-dedupe-results.md` and fills the remaining columns there; this file does not change. The revisions of plan review calls 1–6 and of the Codex second opinion after call 4 are applied (spec Further Notes).

Main's owner and wording decisions of 2026-10-20 are applied: O1–O8, D2/D3/D8/D9, D5 and D6 withdrawn, H7 replaced, H9 and H11 kept. Section 8 lists what is still open.

## 0. Conventions

### File abbreviations and baseline loading path

| Abbr | File | When main has it loaded in the baseline |
| --- | --- | --- |
| SK | `skills/delegation/SKILL.md` | Whenever cc-feather:delegation is used. The installed policy loads it before dispatching, accepting or recovering, before any requested review, for toggles, for findings and before a Security-critical change. |
| RS | `skills/delegation/references/review-state.md` | Only when main follows a link to it. No baseline sentence makes main read it in full. |
| PR | `skills/delegation/references/plan-review.md` | For plan review (SK:62). Also cited for mode resolution (CR:5, OV:5, AR:5), classification, plan identification and step-1 recovery (CR:9, OV:9, AR:12). |
| CR | `skills/delegation/references/code-review.md` | For code review (SK:56, SK:66). |
| OV | `skills/delegation/references/outcome-verification.md` | For outcome verification (SK:56, SK:70). |
| AR | `skills/delegation/references/adversarial-review.md` | For Adversarial review (SK:74, ARC:10). |
| PV | `skills/delegation/references/preview.md` | Only through PVC. |
| ARC | `skills/adversarial-review/SKILL.md` | When the user runs `/cc-feather:adversarial-review`. |
| PVC | `skills/delegation-preview/SKILL.md` | When the user runs `/cc-feather:delegation-preview`. |
| STC | `skills/stop-threshold/SKILL.md` | When the user runs `/cc-feather:stop-threshold`. |
| STP | `skills/setup/references/stop-threshold.md` | Through STC, or for a natural-language change request (SK:62, STP:3). |

Context only, not in scope for change:
- ATG = `skills/setup/references/auto-review.md`
- POL = `templates/review-auto.md` (the installed policy)
- role:X = `templates/agents/X.md`

**Line numbers.** Each of these files keeps one paragraph or one list item per line, so `RS:51` means the whole Reading set bullet. A quoted anchor locates the sentence inside that line.

**Attributes (S1).**
- A: actor
- M: mode (auto, off, or both)
- Tr: trigger
- Ti: timing
- Ex: exceptions
- P: precedence
- Re: how the rule reaches a role. Def = role definition. Brief = the role's brief. Main = applies to main only.
- L: loading path. A copy's L is the file the copy is in, plus SK. RS counts only when the copy is in RS or main has followed a link to it.

**Flags.**
- OWNER: the owner's copy (item 1, with main's decisions).
- RESTATE: a full or partial restatement.
- PTR: already a pointer.
- MOVES: the condition appears only in a non-owner copy and moves to the owner with the quoted qualifier (item 2).
- BRIEF-STAYS(X): a brief requirement that stays in procedure X (item 3, S2; also indexed in section 1a).
- ROLE-DEF: also stated in a role definition; that copy stays (item 7).
- HIST: historical wording (section 3).
- D#: affected by an enumerated fix (section 4).
- U#: an ambiguity kept under S4 (section 2b).

---

## 1. Rules restated in more than one place

**Default loading route (S1), for every copy listed below of a rule whose owner is not review state.** A rule's own loading line may require state (c) where this default would allow (b); the stricter one applies. Each such copy ends in one of three states, and the verifier checks which: (a) it keeps its full baseline text, so the rule is in the file main applies (route 1); (b) it is a baseline sentence this work leaves unchanged, keeping the baseline's loading (route 4), which covers every copy in the `/cc-feather:adversarial-review` command (loaded with the Adversarial review procedure through ARC:10's baseline instruction to follow it), SK:56's and SK:74's baseline instructions to follow the procedures, and CR:5, OV:5 and AR:5's "as in plan review"; or (c) it is a pointer or a sentence this work writes or rewrites, which uses item 3's explicit-read form (route 2), so any new or rewritten reference to the Adversarial review procedure's step 7 or step 10, including RS:51's per-destination text for R3 and any rewritten copy at CR:8 or OV:8, names the step and tells main to read and follow it. Copies of rules review state owns rely on item 4's read (route 3). The loading lines under individual rules add to this default and never relax it. PV:30, preview's one-line report of the counts, the Stop threshold and the Adversarial review timing (listed as a copy under R7.1, R7.2, R8.1, R8.5, AP1 and AP8), and PV:43 (R29) stay as preview's own summaries (spec item 1), PV:30 reworded only by D8.

### R1. Reading set

**Owner:** RS:51 **Reading set**.

- **R1.1 Contents.**
  - Text (RS:51): "the text the claim is written in and the parts of a spec it cites, an Out of Scope line that limits what the claim may change included, and, only for a claim a spec lists, the spec's parts that state they hold for every claim; no other part of a spec is supplied, and the whole spec only when the spec itself is the claim".
  - Attributes: A main assembles it. M both. Tr any brief for the claim's implementation or review. Ti each dispatch. Ex R1.2, R1.3, R1.8, R1.9. Re Brief.
  - Copies:
    - RS:51 OWNER.
    - SK:44 RESTATE, word for word (implementation dispatch).
    - CR:8, OV:8 and AR:10 RESTATE, word for word.
    - PR:9 partial: "a ticket's reviews after plan review do not read the parts of the spec it does not cite".
  - Ambiguities: U1, U2.
- **R1.2 A plan that is neither a spec nor tickets of a spec.**
  - Text: "the text the claim is written in is the whole plan: the whole plan is supplied to the claim's implementation and every review of it, as before cc-feather 0.23.0, and main records and compares it, with any part of a spec the claim cites, as the claim's reading set, so a change to another claim's part of that plan is a change to the reading set".
  - Attributes: A main. M both. Tr a claim of a plan file, a plan-mode plan, or a conversation plan with several claims. Re Brief.
  - Copies: RS:51 OWNER. SK:44, CR:8, OV:8 and AR:10 RESTATE, word for word.
  - Flags: HIST, H1–H6.
- **R1.3 A ticket without a READY.**
  - Text (RS:51): "When a ticket of a spec is implemented or reviewed without a READY for its plan in this session, as in off mode, after a waived plan review or for an explicit call, … read the whole spec as context, … and main records and compares the ticket and the whole spec as its reading set, while its security invariants and test targets stay those named above."
  - Attributes: M both. In auto, a READY held in the dispatch record counts as this session's (RS:75). Re Brief.
  - Copies:
    - RS:51 OWNER, the only full statement.
    - SK:44, CR:8, OV:8 and AR:10 carry it only as an embedded pointer: "except for a ticket of a spec implemented or reviewed without a READY for its plan in this session, as review state's Reading set describes".
  - Flags: HIST (H3). Ambiguities: U3, U4.
- **R1.4 When the reading set is recorded.**
  - Text (RS:51): at READY, by content or hash; otherwise at the claim's first dispatch in this session.
  - Attributes: A main. M both. Re Main.
  - Copies:
    - RS:51 OWNER.
    - PR:21: "Main records each claim's reading set at that READY".
    - RS:74 and SK:62 (auto): the dispatch record holds the hash.
- **R1.5 Confirm it unchanged; supply only what was recorded.**
  - Text (RS:51), with exceptions R1.8 and R1.9.
  - Attributes: A main. M both. Ti before each dispatch. Re Brief.
  - Copies:
    - RS:51 OWNER.
    - SK:44: "main confirms it unchanged before dispatch and supplies only the reading set it recorded".
    - CR:8, OV:8 and AR:10: "Before dispatch, main confirms … supplies only the reading set it recorded".
  - Additional timings, stated only in RS: RS:61 (auto, before the final check) and RS:70 (auto, before the end decision).
- **R1.6 Changes to the reading set.** Ticket status and notes are not a change. An unauthorised change is a material deviation; after an authorised change, main records the changed set.
  - Copies: RS:51 OWNER. Related, all in RS: RS:50, RS:61, RS:70, RS:81 ("counts as a changed ticket"), RS:82.
- **R1.7 Spec lines.** "a `Spec:` line, a parent reference or a shared directory brings in no part of a spec".
  - Copies: RS:51 OWNER. CR:8, OV:8 and AR:10, word for word. PR:9 ("is not a citation"). Absent from SK:44.
- **R1.8 Composed-review addition.**
  - Owner: AR:10, step 2. Related: AR:14 step 6, AR:17 step 9. RS:51 has a pointer.
  - The brief also carries the accepted claim's invariants and test targets. They come from that claim's reading set as recorded in this session. If only a hash or no record exists, they come from the claim's text and cited parts at the accepted commit, checked against the hash. Main labels them with their source, and a HELD counts only if they are covered.
  - Attributes: A main. M both. Tr the claim owns a composed review. Re Brief.
  - Flags: BRIEF-STAYS(AR). The exception to R2.1 MOVES (see R2.1).
  - Loading at the decision (S1): owner AR, loaded when main writes the Adversarial review brief; RS:51's pointer to it uses the explicit-read form.
- **R1.9 Acceptance-check files.**
  - Owner: CR:8, step 2. M auto.
  - A claim may change such a file only if its own reading set says so; otherwise the change is a Deviation and a Blocking finding. The brief names the files and carries the served claims' acceptance "as a stated exception", and the reviewer checks that the change does not weaken them. "The installed reviewer definition is unchanged: the brief states this check."
  - Pointers: RS:51, RS:50, RS:61.
  - Flags: BRIEF-STAYS(CR) (S2 "the check that acceptance of another claim is not weakened").
  - Loading at the decision (S1): owner CR, loaded when main writes the code review brief; the pointers in RS:50, RS:51 and RS:61 use the explicit-read form.
- **R1.10** SK:44: "This is the same material the claim's code review, outcome verification and Adversarial review read." This is implied by R1.1 and listed only so T1 accounts for it.

### R2. A Security-critical claim's security invariants and test targets

**Owner:** RS:51 defines them. Each procedure that writes a brief keeps the requirement to carry them (S2).

- **R2.1 Exactly the claim's own.**
  - Text (RS:51): "those written in the claim's own text, which for a claim of a plan that is neither … is its own part of that plan, the parts it cites and, for a claim a spec or other plan lists, the parts stated to hold for every claim; a claim of such a plan takes no other claim's invariants or targets from the rest of that plan".
  - Attributes: A main. M both. Tr a Security-critical claim's brief. Re Brief.
  - Copies:
    - RS:51 OWNER. Only this copy has "takes no other claim's … from the rest of that plan". It lacks "never another claim's".
    - SK:44: "the brief carries exactly … never another claim's". BRIEF-STAYS(SK).
    - CR:8 and OV:8: "… exactly … never another claim's". BRIEF-STAYS(CR, OV).
    - AR:10: "… never another claim's except as the next sentence adds for a composed review, together with any target the user's own command arguments name as step 3 allows". BRIEF-STAYS(AR).
    - AR:7 (auto, final commit): "The brief carries only the claim's own security invariants and test targets, as step 2 describes, never another claim's of the plan".
  - **MOVES (item 2):** AR:10's two exceptions, (i) a composed review and (ii) targets the user's own command arguments name. They move to the owner with the predicate "in an Adversarial review brief". They must not become exceptions for the implementer, code review or outcome verification briefs.
  - Flags: D1 (five copies).
- **R2.2** RS:51 alone: for a ticket without a READY, the invariants and targets "stay those named above". Owner only.
- **R2.3 Code review brief.**
  - CR:8: "for a Security-critical claim, name the trust boundaries to check. The brief for a Security-critical claim also carries its security invariants."
  - Flags: MOVES (item 2), BRIEF-STAYS(CR).
  - ROLE-DEF: role:reviewer:13.
- **R2.4 Outcome verification brief.**
  - OV:8: "The brief for a Security-critical claim also carries its security invariants."
  - Flags: MOVES, with the predicate "outcome verification brief", and BRIEF-STAYS(OV).
- **R2.5 Adversarial review brief: targets.**
  - AR:10, step 2: each target with where it runs, its environment variables, start and reset, synthetic data, allowed effects, reachable dependencies, any isolated environment, and the open gaps.
  - AR:11, step 3: a target that lacks any of these counts as no target.
  - Flags: OWNER (AR), BRIEF-STAYS(AR) (S2 "the targets' own properties").
  - ROLE-DEF: role:adversary:17–21.
- **R2.6 Where security analysis writes them.** PR:13 OWNER. SK:38 summarises. Loading at the decision (S1): SK:38's summary becomes an explicit-read pointer to PR:13, or stays as it is. Condition (PR:13): "Main writes each such security invariant into the claim's own acceptance or a part of a spec the claim cites, and each test target into the claim's own text or a part it cites".

### R3. Findings or dispositions given to the implementer also go to the reviews

**Owner (O2):** RS:51 Reading set, with one predicate per destination. Each procedure that writes one of these briefs keeps its own requirement.

- **R3.1** SK:44, inside "For a Security-critical claim …": "any finding or disposition main gives the implementer also goes to the claim's code review, outcome verification and Adversarial review".
  - Attributes: A main. M both. Tr a Security-critical claim, plus a finding or disposition given to its implementer. Re Brief.
  - This copy states no disclosure limit. The implementer's own brief is unchanged by this rule (U17).
- **R3.2 To code review.** CR:8: "masked and limited as Adversarial review step 7 sets for findings it passes to code review or outcome verification". BRIEF-STAYS(CR).
- **R3.3 To outcome verification.** OV:8: identical to R3.2. BRIEF-STAYS(OV).
- **R3.4 To Adversarial review.** AR:10: "with any secret, credential or real data masked as step 7 requires". BRIEF-STAYS(AR). Masking only.
- **Status: MOVES** into RS Reading set with three predicates kept apart: code review and outcome verification, masked and limited; Adversarial review, masked only; the implementer brief unchanged.

### R4. Citations

**Owner:** PR:9.

**Loading at the decision (S1).** The copies that become pointers to plan review's citation rule (SK:44, RS:51, CR:8, OV:8, AR:10, "Citations are as plan review defines them") are written in item 3's explicit-read form. The brief instruction of R4.2 stays at each brief writer (CR:8, OV:8, AR:10), so main has it in the file it is applying. RS:81's restatement of the checklist parts (R4.3) points to plan review in the explicit-read form.

- **R4.1 Definition.**
  - PR:9: "A citation is explicit: a named section or heading, a numbered item or an identifier such as `C1 item 1`, `D3` or `S2`, …; a `Spec:` line, a parent reference or a shared directory is not a citation." Also: "A citation that does not resolve to exactly one part of the spec is a blocker."
  - Pointers: SK:44, RS:51, CR:8, OV:8, AR:10.
  - Ambiguity: U14.
- **R4.2 Follow a citation to the cited part only.**
  - PR:9 OWNER: "A reviewer follows a citation to the cited part only."
  - CR:8, OV:8 and AR:10: "and the brief tells the role to follow a citation to the cited part only". BRIEF-STAYS(CR, OV, AR).
  - Absent from SK:44, RS:51 and every role definition.
  - Flags: MOVES (O3). The owner gains the brief instruction with the predicate "code review, outcome verification and Adversarial review briefs", not the implementation brief.
  - Loading at the decision: main applies the instruction when it writes the brief, in code review, outcome verification or Adversarial review, whose BRIEF-STAYS requirement is in the file main has loaded; the owner's definition of a citation is reached through their existing link to plan review, which main also loads for mode resolution (R9).
- **R4.3 Checklist parts.** PR:9 OWNER. RS:81 (Deviation scope) restates the invariant-citation check ("a narrowed one included") and the coverage rerun. Condition (PR:9): "The coverage part runs whenever the named tickets together with the finished ones are all of the spec's tickets"; "Every plan review over tickets of a spec also checks that each of the spec's security invariants is cited by at least one of its tickets".
- **R4.4 A spec that lists claims.** PR:9 only. Condition (PR:9): "When a spec lists its own claims, plan review checks that every decision, Out of Scope line and security invariant that applies to a listed claim is in the claim's own text".

### R5. Dispatch record

**Owner:** RS:74.

- **R5.1 What it is, where it lives, how it is named.** Auto only, one per plan, at `.feather/dispatch/<name>.md`; the naming rule.
  - Copies: RS:74 OWNER. SK:62 RESTATE, without the naming details.
- **R5.2 Contents.** Condition (RS:74): "It holds what a later session needs: the plan, its base revision and its plan-review READY".
  - Copies:
    - RS:74 OWNER.
    - SK:62: a subset, without the one-line summary or the fix claim's problem and summary.
    - RS:61: fix claims.
    - RS:63, RS:68: pass state.
    - AR:7: "each BROKEN's one-line summary".
- **R5.3 Excluded contents.** No counts, exploit details or secrets. RS:74, SK:62.
- **R5.4 Writing rules.** Only between calls, out of Git, `.gitignore`, never staged, written by main and not by the handoff tool.
  - Copies: RS:74 OWNER. SK:62 RESTATE, without the `.gitignore` and handoff-tool clauses.
- **R5.5 Role in crossing sessions.** It replaces handoff notes; the handoff names it; a handoff note still restricts. RS:74, RS:63, SK:62.
- **R5.6 Taken as written.** RS:74 OWNER (full). SK:62 (short). RS:70. Condition (RS:74): "Main takes the dispatch record as written, so an edit to it, by repository code a review or the final check runs or by a person, changes which passes and results main believes".
- **R5.7 Off mode writes none.** RS:74, SK:62.
- **R5.8 Differences and the end list.** RS:69, RS:70. Condition (RS:69): "main reports any difference between it and an active handoff's record of the decision"; (RS:70): "main builds the list from the plan's dispatch record and its own observations in this session".

### R6. Resumed sessions and context compaction

**Owner:** RS:75, with RS:14 and RS:36.

- **R6.1 Counts do not cross sessions.**
  - Copies: RS:14, RS:75 OWNER, SK:62, PR:17 ("since resuming requires the user"), CR:9, OV:9, AR:12.
  - Flags: HIST (H13).
- **R6.2 Off mode.** Passing verdicts do not cross; passes are re-obtained; the stated exemptions apply.
  - Copies: RS:75 OWNER, RS:63, PR:17, AR:12 ("in off HELD does not cross sessions").
- **R6.3** Auto plan re-review unless the record holds a READY; finished tickets are not redone. RS:75, PR:17.
- **R6.4 Scope of an unresolved verdict.** Condition (RS:75): "an unresolved verdict that an active handoff records for a spec's plan restricts that spec's tickets when they are named, and one recorded for a ticket's plan still restricts that ticket when the whole spec is named".
  - Copies: RS:75 OWNER, RS:14, PR:7, PR:17, SK:62, CR:9, OV:9, AR:12.
- **R6.5 How long an unresolved verdict lasts.**
  - PR:17: "it then applies, in either mode, until a later call passes it or the user cancels the work, changes its acceptance or waives it. A re-review is another call and lifts it only by passing, and a deferral keeps it."
  - Flags: MOVES (into RS).
- **R6.6 What auto restores.** Condition (RS:75): "take the plan's READY, each claim's reading set, its passes, its Adversarial review results and the user's decisions from the plan's dispatch record".
  - Copies:
    - RS:75 OWNER, SK:62, PR:17.
    - CR:9 and OV:9: "passes, verdicts and open findings".
    - AR:12: result and BROKEN by summary, "details staying where step 10 puts them".
    - AR:7, RS:42, RS:54, RS:69, RS:79.
- **R6.7 What comes only from this session.** Counts, the Stop threshold, the final check state.
  - Copies: RS:75 OWNER, SK:62, PR:17, RS:22, RS:61.
- **R6.8** If the record lacks what main needs, Unknown state applies. RS:75, RS:36.
- **R6.9** Auto replaces the off rules. RS:75 only. Condition (RS:75): "For a plan in auto, this replaces the rules above that passing verdicts do not cross sessions and that an unresolved verdict reaches a resumed session only through an active handoff".
- **R6.10 Unknown state.**
  - Copies:
    - RS:36 OWNER.
    - PR:17: "treat the step as stopped and ask the user".
    - CR:9, OV:9, AR:12: "makes the step stopped until the user decides".
    - RS:21, RS:70, RS:79.
  - Ambiguity: U7.
- **R6.11** PR:17: "never assume a count of zero". MOVES.

### R7. Counts

**Owner:** RS:10, RS:29–37, RS:52.

- **R7.1 What counts.** Condition (RS:29): "As many consecutive automatic calls without a pass as the Stop threshold in effect stop the step for that work"; (RS:10): "Automatic calls in a row that did not pass, including failed, interrupted and protocol-failure calls".
  - Copies: RS:10, RS:29 OWNER, PR:19, CR:9, OV:9, AR:12, PV:30.
- **R7.2 Resets.** An automatic pass resets; an explicit verdict changes nothing.
  - Copies: PR:19, CR:9, OV:9, AR:12, RS:31, RS:52, PV:30.
- **R7.3 Explicit calls are outside the count.**
  - Copies: RS:9 (D2), PR:5 (D2), CR:5 (D2), OV:5 (D2), PR:22, AR:12.
- **R7.4 Every attempted call counts; precondition failure is not a call.**
  - Copies: RS:34 OWNER, SK:54, CR:12, AR:10.
- **R7.5 What does not reset a count.** MOVES (item 2), with each copy's own list:
  - SK:54 is not part of this rule and stays where it is: "Changing child, model or error wording does not reset this limit" refers to the preceding sentence's limit, "Retry the same operation at most once", owned by the delegation skill's Accept or recover section (plan review call 1, B2).
  - PR:17: "Within a session, mode changes, renamed plans, different reviewers/models or cosmetic splits do not reset the count or clear blockers".
  - CR:9: "changing reviewer, model or wording never resets it".
  - OV:9: "a different verifier, model or wording does not change it".
  - AR:12: "changing the adversary's model or the brief's wording never resets it".
- **R7.6 Kept across mode changes within a session.** MOVES (item 2), each copy with its own predicate:
  - SK:62 (plan review): "Keep the review count and unresolved verdicts across mode changes within a session". Moves with this predicate.
  - SK:66 (code review): "Keep its call count and open findings across mode changes within a session". Moves with this predicate.
  - PR:17: "Within a session, mode changes … do not reset the count or clear blockers". Part of R7.5; moves with that predicate.
  - AR:5 stays in the Adversarial review procedure, unchanged: "Off mode starts no automatic Adversarial review; existing notes, counts and obligations persist", which holds in off with no session limit and covers notes and obligations.
  - PR:26 stays in plan review, unchanged: "Turning review off does not erase an unresolved verdict or manufacture approval".
  - ATG:24 stays (out of scope). `skills/setup/SKILL.md:49` ("changing the mode does not reset any automatic review count") is a further copy outside item 1's scope and stays, for reference only.
- **R7.7** OV:9 alone: "the count runs across fixes …", and "stops after K − 1 automatically rechecked fixes". Owned by OV.
- **R7.8 Next automatic call.** Condition (RS:30): "A step's next automatic call for a work needs the user's explicit request exactly while that step's count for the work is at or above the Stop threshold in effect".
  - Copies: RS:30 OWNER. PR:21, PR:22, CR:16, OV:9, AR:12, RS:23, RS:37, RS:52, STP:25.
- **R7.9 On a stop, keep the state in the task.** Each procedure owns its own: PR:22, CR:12, OV:12, AR:16.
- **R7.10 Reopened calls continue the count.** RS:52 OWNER. CR:16, RS:61.
- **R7.11 Overlap.** RS:37 OWNER. PR:7. Condition (RS:37): "Work that overlaps a stopped plan keeps that plan's count and stop".
- **R7.12** RS:14: "step 1 or step 3". D9.

### R8. Stop threshold

**Owner (O1):** RS:18–25 is the single owner of resolution. STP keeps how a value is saved, its values and its scopes (R8.11–R8.16).

**Loading at the decision (S1).** R8.1–R8.10 are owned by review state, which item 4's read covers at every place it names, STP and STC included. For R8.11–R8.16 (owner STP): STC:10's baseline instruction to follow the Stop threshold procedure stays, so STP is loaded when the command runs; SK:62's baseline "follow the Stop threshold procedure" for a natural-language request stays; any pointer this work writes from review state or preview to how a value is saved uses the explicit-read form.

- **R8.1 Definition.** RS:18, RS:20, STP:3, STC description, PR:5, PV:17, PV:30. Condition (RS:18): "the number of consecutive automatic calls without a pass that stops a step: one integer from 2 to 10".
- **R8.2 Resolution order.** Condition (RS:20): "The Stop threshold in effect is, in order: the user's task choice, for that task; otherwise the user's session choice; otherwise the value the loaded project guidance states; otherwise the value the loaded user guidance states; otherwise 2".
  - Copies:
    - RS:20 OWNER (D7).
    - PV:17: no invalid-value rule and no "loaded".
    - STP:15, STP:27: "the project's value before the user's".
    - Pointers: PR:5, CR:9, SK:62.
- **R8.3 Main never changes it on its own.** RS:20, SK:62, STP:33.
- **R8.4 Unknown threshold.** RS:21 only. Condition (RS:21): "When main cannot establish whether a task or session choice exists, for example after context compaction, it treats the Stop threshold as unknown".
- **R8.5 Stating it.** RS:22 OWNER, PR:5, CR:9, SK:62, PV:30, STP:29. Condition (RS:22): "Whenever a review decision comes up, main states the Stop threshold in effect and its source".
- **R8.6 A session choice does not cross sessions.** RS:22 OWNER, STP:15, STP:33, RS:75, SK:62, PR:17.
- **R8.7 Changing it.** Condition (RS:23): "A change of the Stop threshold never changes a count; Next automatic call is applied with the new value at once".
  - Copies: RS:23 OWNER, STP:25, STP:29, STP:33, STC:10 ("Never change a step's count").
- **R8.8 Saved in this conversation.**
  - Copies:
    - RS:24 OWNER: "where the project states its own".
    - STP:27 RESTATE: "while the project has a saved value so taken, report that the project's value overrides it and stays in effect".
    - PV:17.
- **R8.9 What a scope's saved value is.**
  - STP:27, sentence 2: "Each scope's saved value is the one last saved in it in this conversation, none after `default`, and otherwise the value its loaded guidance states, since the guidance loaded at the start of the session does not show later saves."
  - Flags: MOVES (O1, item 2) into RS:24 Saved in this conversation, with the predicate "saved in this conversation". D7 points Resolution to it.
- **R8.10 Steps that are not counted.** RS:25 OWNER, PR:13, RS:61. Condition (RS:25): "The security analysis before plan review is not a counted step"; "The final check before landing or release, … is not a counted step either".
- **R8.11 Value and scope validation.** STP:7–8 OWNER. STC:10. Condition (STP:7): "The value is an integer from 2 to 10, or `default`"; (STP:8): "Refuse a value outside 2 to 10"; "A missing value, more than one value, or an unknown or conflicting scope needs clarification before anything is applied or written".
- **R8.12 Scope forms.** STP:9–11 OWNER. Condition (STP:9): "No scope or `session` sets a session choice. A request the user limits to the current task sets a task choice for that task instead"; (STP:10): "`project` saves the value for the confirmed current project installation. `user` saves it for the selected Claude user configuration root"; (STP:11): "A user-supplied equivalent natural-language scope is accepted".
- **R8.13 `default`.** STP:7 OWNER. Ambiguity: U21. Condition (STP:7): "In project or user scope, `default` removes the value saved in that scope; without a scope or with `session`, it drops an earlier session choice in this conversation".
- **R8.14 Applying a session value.** STP:15 OWNER, including "An earlier task choice stays in effect for its task".
- **R8.15 Saving through the tool.** STP:19, STP:21. STP:21 is excluded from item 5. Condition (STP:19): "Check that the delegation component is installed. A handoff-only installation is insufficient"; (STP:21): "apply with identical arguments plus `--apply --expected-plan <returned-plan-id>`".
- **R8.16 Meaning.** STP:33 OWNER. Condition (STP:33): "Changing it grants no authority to implement, merge or release"; "The Stop threshold is a model instruction, not a hook-enforced counter".
- **R8.17 Natural-language requests.** STP:3, SK:62. Condition (STP:3): "a natural-language request to change the Stop threshold, which cannot load the user-invoked command and follows this same procedure".

### R9. Review mode resolution

**Owner (O6):** PR:5.

**Loading at the decision (S1).** CR:5, OV:5 and AR:5 resolve the mode "as in plan review" (baseline, unchanged), which their procedures direct main to follow before the call. PV:16's restatement becomes an explicit-read pointer to plan review's mode resolution, and R9.2 (preview's own precedence sentence) stays in preview. SK:62 and SK:66 name the triggers and stay.

- **R9.1 Order.** Condition (PR:5): "Resolve the active review mode in this order: a task/session choice, then project guidance, then user guidance".
  - Copies: PR:5 OWNER. CR:5, OV:5, AR:5 PTR ("as in plan review"). PV:16 RESTATE. SK:62 and SK:66 (triggers). POL (stays).
- **R9.2** PV:16 alone: "A session choice takes precedence over the saved mode reported by `show`, because a session toggle writes no file." Owned by preview. Ambiguity: U10.
- **R9.3 A saved mode keeps a separate session override.** RS:24, STP:27, ATG:20 (context).
- **R9.4 Explicit requests apply in either mode.** PR:5, CR:5, OV:5, ARC:25.
- **R9.5 State the mode with each review decision.** RS:22, ATG:7.

### R10. Per-claim timing

**Owner:** RS:57.

- **R10.1** In auto, code review and then outcome verification once each claim is implemented and committed. RS:57 OWNER, SK:62, PR:26, CR:5, OV:5.
- **R10.2** The only timing in auto. RS:57, PR:26, SK:62, CR:5, OV:5.
- **R10.3** A single-claim plan is unchanged. RS:57 only.
- **R10.4** Serial working tree. RS:57, SK:62. Condition (RS:57): "Implementation and reviews in one working tree stay serial as Serial within a working tree states".

### R11. Dependent claims

**Owner:** RS:58.

- **R11.1** In auto, `Blocked by` or a stated dependency means the claim waits for valid APPROVED and CONFIRMED.
  - Copies: RS:58 OWNER. SK:62 RESTATE, with no "In auto" in the sentence (K1). PR:26 PTR. PR:7.
- **R11.2** No dependency means no wait. RS:58 only.
- **R11.3** With no stated dependencies, plan order. RS:58, SK:62.
- **R11.4 When upstream stops.** RS:58 lists the triggers. SK:62 has only "when a claim stops". Condition (RS:58): "When a claim's code review or outcome verification stops, its outcome verification cannot be resolved, it has a Deviation, or it would need accept and land, every claim that depends on it stops and main asks the user".
- **R11.5 Deferral naming dependents.** RS:58 OWNER, RS:69, SK:62.

### R12. Serial within a working tree

**Owner:** RS:59.

- **R12.1–R12.8:** serial work; nothing changes the tree during a call (SK:48 lacks "nothing main started writes to it"); handoff updates only between calls; no running writer; one executing gated call; no review worktree on main's own initiative; user worktrees in parallel; shared test resources.
- Copies: RS:59 OWNER, SK:48, RS:57, RS:74, SK:62.

### R13. A pass not used after a workspace change

**Owner:** RS:59, with RS:35 and RS:56.

- **R13.1 Trigger.** RS:59 OWNER. RS:56: "its pass is not used and the step is not cleared". Condition (RS:59): "finds a change to a file the claim depends on, its own files and what its acceptance checks depend on included, that call's pass is not used".
- **R13.2 A non-pass with no coverage and no reset.** RS:59, RS:35, CR:9, CR:16, OV:9, AR:14.
- **R13.3 The next call covers the full scope from the base revision.**
  - Copies: RS:59, RS:35, CR:8, CR:10, CR:18, OV:10, AR:13 (D4), AR:14.
- **R13.4 Brief wording.** "the brief does not say that call completed with a verdict". CR:8, CR:10, CR:18, OV:10. BRIEF-STAYS(CR, OV).
- **R13.5 No continuation and no stopped step cleared.**
  - Copies: CR:12, OV:12 (no "clears no stopped step"), AR:16, RS:56.

### R14. Workspace reads (What a gated pass judged)

**Owner:** RS:56.

- **R14.1 Gated claims.** RS:56 OWNER, RS:8, CR:8, OV:8, AR:9, AR:10, ARC:16, ARC:23. Condition (RS:56): "For a claim the acceptance gate covers, main dispatches a code review, outcome verification or Adversarial review only when the workspace equals the commit it names in the brief".
- **R14.2 The two reads, what counts as a change, overrides, residual risk.** RS:56 only. Condition (RS:56): "Main establishes this with two reads"; "A read that exits non-zero, writes anything to standard error, or prints output that is not porcelain v1 lines counts as a change"; "The command line overrides the user's `status.showUntrackedFiles` and submodule-ignore settings"; "Ignored files and files marked assume-unchanged or skip-worktree are outside this check, which is residual risk".
- **R14.3 Reads before and after; compare; preserve or report.** RS:56, CR:8, CR:14, OV:8, OV:15, AR:10, AR:22, ARC:23.
- **R14.4 Plan review and security analysis.** RS:56, SK:38, PR:18, PR:24. Condition (RS:56): "Plan review and security analysis do not need a clean workspace"; "main runs the same reads before and after the call and reports any difference".
- **R14.5 Work outside the gate.** RS:56, ARC:18, ARC:29. Condition (RS:56): "A call for work the gate does not cover, … judges the workspace change from the base revision, except that an Adversarial review run through [the adversarial-review command] reviews the range that command defines, and main does not commit that work to review it".
- **R14.6 The final check.** RS:56, RS:61. Condition (RS:56): "The final check uses the same reads before and after it".
- **R14.7 Commit when needed; blocked if told not to commit.** RS:54, RS:55, ARC:23.

### R15. Base revision in briefs

**Owner:** RS:42.

- **R15.1 The claim's base revision.** Condition (RS:42): "Every brief of the claim's code review, outcome verification and Adversarial review, a narrowed follow-up's included, names the claim's base revision, which main establishes itself from Git in this session".
  - Copies: RS:42 OWNER, CR:8, OV:8 ("a recheck's included"), AR:10, CR:10, ARC:19, ARC:20.
  - Flags: BRIEF-STAYS(CR, OV, AR). ROLE-DEF: role:reviewer:13, :26.
- **R15.2 The plan's base revision (auto).** Condition (RS:42): "In auto, every such brief also names, beside the claim's base revision, the plan's base revision".
  - Copies: RS:42, CR:8, OV:8, AR:10, AR:7, ARC:20, RS:75.
  - Flags: BRIEF-STAYS(CR, OV, AR).
- **R15.3 Main judges whether a finding is pre-existing.** RS:42, CR:8, CR:11, OV:8, AR:10, AR:7.
- **R15.4 Judged at the base revision.** RS:42, PR:15, CR:5, OV:5. ROLE-DEF: role:reviewer:26. Condition (RS:42): "The existing behaviour a regression breaks, and any written rule or shipped spec acceptance it is judged against, are taken at the claim's base revision, never from the reviewed commit".

### R16. Completion criteria, including the verifier's note

**Owner:** RS:41–45.

- **R16.1 Conditions.** RS:41 OWNER, PR:15, CR:5, OV:5. ROLE-DEF: role:reviewer:19–22. Condition (RS:41): "its acceptance as written is met; existing behaviour is not broken, shown by a failing test or a reproduction; it introduces no security problem and no data loss, …; and it has no deviation from the plan".
- **R16.2 Regression evidence.** RS:42, PR:15, CR:5, OV:5, CR:10, OV:10. ROLE-DEF. Condition (RS:42): "A regression that is only inferred and is neither a security problem nor data loss does not block: such a regression blocks only when a failing test or a reproduction shows it".
- **R16.3 Security findings** ("as before" is HIST, H8). RS:43 OWNER, PR:15, CR:5, CR:10, OV:10, CR:11. ROLE-DEF. Condition (RS:43): "A security problem the change introduced or made exploitable, through a new route, permission or data flow even when the vulnerable code is outside the diff, and data loss the change introduced, are Blocking findings whatever the acceptance states".
- **R16.4 The verifier's note (O5).** RS:43 OWNER, OV:13, OV:9, OV:12. Condition (RS:43): "A verifier's note that main judges to be, or cannot rule out as, a security problem or data loss the change introduced or made exploitable is a Blocking finding".
- **R16.5 Deviations.** RS:44, PR:15, CR:5, OV:5. Condition (RS:44): "A finding that shows a deviation from the plan is a Blocking finding, and a Deviation still stops main to ask the user".
- **R16.6 Non-blocking findings.** RS:45, PR:15, CR:5, OV:5, CR:11, OV:13, PR:20. Condition (RS:45): "Every other finding is a Non-blocking finding"; "It does not hold completion and is recorded in the work's Follow-up record".
- **R16.7** PR:15 alone: "only what a claim's acceptance as written asks for holds its completion". Derived from R16.1's closed list.
- **R16.8 Rejecting a "blocking" finding that shows no condition unmet.** CR:10, OV:10, each owned by its procedure.

### R17. Follow-up record

**Owner:** RS:46.

- **R17.1** Copies: RS:46 OWNER, CR:11, OV:13 (without "kept by that work's handoff writer"). Condition (RS:46): "Non-blocking findings go to one Follow-up record per piece of work. With handoff maintenance active it is a handoff record of its own"; "otherwise main lists its content in the completion report".
- **R17.2 The record is data.** RS:46, CR:11, OV:13, RS:70, AR:7.
- **R17.3 No automatic later plan.** RS:46 only.
- **R17.4 Vulnerability content follows step 10.** RS:46, AR:7, CR:11.
- **R17.5 Plan review's style findings.** PR:20. Condition (PR:20): "Style preferences and optional improvements are non-blocking, and main records them in the work's Follow-up record".

### R18. Execution

**Owner:** RS:60.

- **R18.1 Scope.** RS:60 OWNER, SK:12, CR:7, OV:7, AR:11, ARC:12, RS:61. ROLE-DEF: role:reviewer:17, role:verifier:17, role:adversary:27. Condition (RS:60): "main, reviewer, verifier and adversary execute repository code on this machine unless a restriction the user stated in this session covers the call".
- **R18.2 Source is the user's own messages; provenance is not a restriction.** RS:60, SK:12, AR:11.
- **R18.3 Coverage, lifting, unclear scope.** RS:60 only. Condition (RS:60): "A restriction covers every later call it names, the final check included, until the user's own message lifts it; a lift covers only what it names, and a restriction whose scope is unclear stops execution on this machine".
- **R18.4 Non-user text** (a tool result, file, commit, role report, handoff, dispatch or memory record, hook output, compaction summary) cannot state or lift a restriction or name an environment. RS:60 only.
- **R18.5 Compaction, resume or continue, new session.** RS:60 only. Condition (RS:60): "After a context compaction main keeps every restriction the summary still shows; one the summary lost is not recovered"; "A conversation continued with resume or continue is the same session for these statements, and a new session starts without them".
- **R18.6 An isolated environment stays available.** RS:60.
- **R18.7 The determination is stated in every brief of a role that may execute code.**
  - Copies: RS:60, CR:8 (plus lint and type-check commands), OV:8, AR:10, AR:11.
  - Flags: BRIEF-STAYS(CR, OV, AR). ROLE-DEF in all three.
- **R18.8 Definition.** RS:60. ROLE-DEF. Condition (RS:60): "Executing repository code means running any command whose program, plugins, configuration written as code, scripts or module search path can come from the repository".
- **R18.9 Main's own Git use is residual risk.** RS:60, RS:55.
- **R18.10 Primary acceptance not run.** Each copy is owned by its own procedure for its own step (code review, outcome verification, the final check), as R7.9 and R22.8 are. Condition (CR:7): "main records the acceptance as not run with the reason, and code review proceeds on the code"; (OV:7): "main records the acceptance as not run with the reason and still dispatches the verifier, whose brief says the acceptance was not run"; (RS:61): "When Execution does not allow it, it is recorded as not run, and main states that it has not run before landing and in any accept-and-land decision".
  - Copies: CR:7, SK:66, OV:7 (the brief says it was not run; BRIEF-STAYS(OV)), RS:61, RS:70.
- **R18.11 Static analysis and INCONCLUSIVE without an environment.** AR:11, ARC:12. ROLE-DEF: role:adversary:17.

### R19. Security-critical definition, classification and routing

**Owner:** SK:36 and SK:38. PR:11 owns the classification procedure.

**Loading at the decision (S1).** The delegation skill is loaded whenever delegation is used (installed policy), so SK:36 and SK:38 are loaded at every copy. Plan review's classification procedure (PR:11) is loaded at plan review; CR:8's "if it is not yet classified" and the reclassification copies (CR:11, RS:61, ARC:43) stay where they are or point to PR:11 in the explicit-read form.

- **R19.1 Definition.** SK:36. PR:11 points to it. Condition (SK:36): "A Security-critical change is a change to a security guarantee at a trust boundary, or to the implementation or configuration of a security control".
- **R19.2 When to classify.** SK:36 OWNER, PR:11, CR:8. Condition (SK:36): "classify claims as … describes, in off mode too, before dispatching or starting their implementation, main's own work included".
- **R19.3 Implementation goes to security-executor.** SK:25, SK:38 OWNER, PR:11.
- **R19.4 An executor-reported change.** SK:38 ("In off mode too"), PR:11 ("In either mode"). Condition (SK:38): "In off mode too, a Security-critical change an executor reports goes to security-executor".
- **R19.5 Analyst brief.** SK:38 only. Condition (SK:38): "give analyst a read-only brief identifying paths, trust boundaries, evidence questions and excluded scope".
- **R19.6 Security analysis and plan review are separate.** SK:38, PR:13.
- **R19.7 Auto sequence.** SK:38, PR:13 (owner). Condition (PR:13): "In auto, a plan with a Security-critical claim gets a security analysis before its plan review".
- **R19.8 Off.** PR:13, SK:38. Condition (PR:13): "In off mode this sequence is not forced"; "rule that a Security-critical change gets an analyst security analysis still applies".
- **R19.9 Marking and recording.** PR:11 OWNER. HIST (H7). Condition (PR:11): "Main marks each Security-critical claim in a plan it proposes itself"; "Main records the classification in the plan-review brief, in its report and in any active handoff".
- **R19.10 Reclassification.** CR:11, RS:61, ARC:43. Condition (CR:11): "when a later claim changes a security control, main classifies it again as Security-critical by what the change does"; (RS:61): "A fix claim is classified as Security-critical by what it changes"; (ARC:43): "When the revision makes the claim Security-critical, the claim follows the normal flow for one".
- **R19.11** RS:79. Condition (RS:79): "A waiver of the missing READY does not waive security analysis".

### R20. Adversarial review premise in off and auto

**Owner:** AR:5, AR:7, AR:9.

**Loading at the decision (S1).** Each copy outside the Adversarial review procedure: SK:62 and PR:26 become explicit-read pointers to the procedure's At the final commit (SK:74's baseline "read and follow the adversarial-review procedure" also stays); OV:5 and OV:12 become explicit-read pointers; RS:31, RS:32, RS:50, RS:56, RS:61 and RS:70 keep their review-state statements of what a pass and the gate need, and their references to the procedure use the explicit-read form; ARC:16, ARC:20 and ARC:21 stay, since ARC:10's baseline instruction to follow the adversarial-review procedure loads it; PV:30 stays as preview's own one-line summary, reworded by D8, and is not consolidated.

- **AP1 Auto timing.** AR:5, AR:7, AR:9 OWNER; SK:62, PR:26, OV:5, OV:12, RS:56, ARC:16, ARC:20, PV:30 (D8). Condition (AR:5): "In auto, each Security-critical claim of plan-driven work, other than a fix claim, gets one Adversarial review at the final commit, once the final check has passed there and the workspace equals it".
- **AP2 A fix claim gets none in auto.** AR:5, AR:7, SK:62, PR:26, RS:61, RS:70.
- **AP3 Off premise.** AR:5, AR:9 OWNER; RS:56, OV:5 (CONFIRMED only; K2), ARC:16, ARC:20, AR:7. Condition (AR:9): "In off, dispatch a call that can count as the step's pass only for a claim with a valid APPROVED and a valid CONFIRMED at the same commit".
- **AP4 Off, early explicit call.** AR:9, RS:31, RS:32, RS:56, ARC:21. Condition (AR:9): "In off, an explicit call the user requests for a claim that does not yet have a valid APPROVED and a valid CONFIRMED at the same commit still runs"; "but it does not count as the step's pass".
- **AP5 Auto, early or other-commit call counts as not run.** AR:7, AR:9, AR:13, RS:31, RS:32, RS:50, RS:56, RS:70, ARC:20, ARC:21, ARC:39.
- **AP6 Off starts none.** AR:5, ARC:25, SK:74.
- **AP7 No separate switch.** AR:5, RS:53, RS:69.
- **AP8 Auto BROKEN at the final commit.** AR:7, AR:12, AR:15, RS:70, ARC:39, PV:30. Condition (AR:7): "A BROKEN is not fixed in the plan, and step 7 does not apply to it: it counts as a call without a pass".
- **AP9 Listed BROKEN findings carried and open.** AR:7, AR:10, AR:14, RS:50, RS:70, RS:75, ARC:39. BRIEF-STAYS(AR) (S2 "the listed BROKEN findings").
- **AP10 Off rules kept.** AR:7. Condition (AR:7): "These rules hold in auto only: in off, the same-commit premise of step 1, a BROKEN fixed under step 7 before completion and".
- **AP11 Gate needs a HELD or accept and land.** Owner RS:53 (R28), which AR:5 already defers to ("as review state describes"); copies AR:5, SK:56 (plan review call 3, B2).
- **AP12 Limits of this flow.** AR:7, RS:70. Condition (AR:7): "This flow does not check everything: the commit an Adversarial review attacks was not judged as a whole by the claim's own code review and outcome verification, and its findings are not fixed in the plan".
- **AP13 Explicit HELD that clears no stop.** RS:31, ARC:20. Condition (RS:31): "An explicit HELD obtained before the claim's valid APPROVED and CONFIRMED does not clear a stop"; "In auto, an explicit HELD obtained before the final check passed at the commit to be landed, with the workspace equal to it, does not clear a stop either".

### R21. BROKEN and vulnerability disclosure

**Owner:** AR:15 (step 7) and AR:18 (step 10). Exceptions: R21.2 and R21.3 are owned by CR:20 (O8; plan review call 1, B4).

**Loading at the decision (S1).** CR:18 and OV:10 (the step-7 default for findings passed to them) become explicit-read pointers to the Adversarial review procedure's step 7, and the copies in review state (RS:43, RS:46, RS:70, RS:74, RS:75) and CR:11 refer to its step 10 in the explicit-read form; CR:20 keeps R21.2 and R21.3 in code review, loaded on the fix path; ARC:39 and ARC:43 are loaded with the procedure through ARC:10.

- **R21.1 Step 7 default.** Condition (AR:15): "By default, each finding passed to code review or outcome verification carries the violated invariant, the location, the root cause and the observed and expected behaviour, without exploit steps".
  - Copies: AR:15 OWNER, CR:18, OV:10, AR:10, AR:7.
  - Flags: BRIEF-STAYS(CR, OV, AR).
- **R21.2 REFUTED findings of a Security-critical claim passed to the fix review.**
  - CR:20 OWNER: "For a Security-critical claim, the verifier's REFUTED findings, whose evidence may be a reproducing command, are passed to this review with the same disclosure default, masking and limits on added exploit steps that Adversarial review step 7 sets for findings after BROKEN."
  - Stays in code review as its own rule. BRIEF-STAYS(CR).
- **R21.3 Public records after a BROKEN.**
  - CR:20's list: "the fix's commit messages, the notes of a tracked handoff, follow-up items in a tracked handoff or in a tracked or public tracker, such as those steps 5 and 6 write, notes on such a ticket, an ADR and the validation entry's review history. The reviewer's report to main is not such a record".
  - Owner: CR:20, which keeps the list (plan review call 1, B4): main applies it while handling code review's fix path, with code review loaded. Not merged with AR:18's own examples.
  - OV:10 points to it and adds "the verifier's report to main is not such a record".
- **R21.4 Step 10.** Condition (AR:18): "A pre-existing vulnerability becomes separate work in the project's tracker"; "exploit details and secrets go only into untracked, non-public records".
  - Copies: AR:18 OWNER, RS:43, RS:46, RS:70, RS:74, RS:75, CR:11, AR:7, AR:16, ARC:39, ARC:43.
  - ROLE-DEF: role:reviewer:15, role:adversary:29.
- **R21.5** AR:16. Condition (AR:16): "The note records the open findings as step 10 describes, so a tracked handoff carries only their summary unless the user agrees". **R21.6** RS:74, SK:62. Condition (RS:74): "It holds no counts, and no exploit details or secrets". **R21.7** RS:70. Condition (RS:70): "Known vulnerabilities appear as the reporting role stated them, never merged or downgraded".

### R22. Pending-acceptance handoff note

**Owner:** RS:62–63.

- **R22.1** RS:63. Condition (RS:63): "A gated claim stays gated after either single pass, and a Security-critical claim after both until it also has a valid HELD".
- **R22.2** RS:63, CR:12, OV:12, CR:5. Condition (RS:63): "When a pass resolves an active handoff's unreviewed or unverified note for a gated claim, main replaces it with a note that the claim is pending acceptance, naming what is still missing".
- **R22.3** RS:63, AR:16. Condition (RS:63): "When Adversarial review stops, or a BROKEN is unresolved, main records a pending-acceptance note naming the missing Adversarial review and its open findings whether or not an earlier note existed".
- **R22.4** RS:63 OWNER; CR:12, OV:12, AR:16. Condition (RS:63): "An accept-and-land decision does not remove the note"; "Main removes the note only when the claim is landed, released or reported complete, or cancelled with its commits disposed of; a deferral keeps it and a waiver stays visible in it".
- **R22.5** RS:63, RS:75. Condition (RS:63): "In off, a resumed session that finds a pending-acceptance note keeps the claim under the gate and obtains passes from the current session".
- **R22.6** RS:63, RS:74. Condition (RS:63): "In auto, a plan's dispatch record, not these notes, is where its claims' review state crosses sessions".
- **R22.7** RS:62. Condition (RS:62): "An active handoff's record that a claim is unreviewed, unverified or pending acceptance restricts it under the acceptance gate whatever its wording".
- **R22.8** CR:12, OV:12, PR:22, each owned by its procedure. Condition (CR:12): "When a handoff is active, record as plain text that the claim is unreviewed, its open findings and that it must not be landed on the default branch, released or reported complete"; (OV:12): "record as plain text that the claim is unverified"; (PR:22): "When a handoff is active, record the unresolved verdict and what it blocks as plain text in the record".
- **R22.9** CR:5. Condition (CR:5): "the unreviewed rule in step 6 applies only to the automatic flow"; "acceptance gate still covers, in either mode, a claim an active handoff records as unreviewed, unverified or pending acceptance".

### R23. Explicit calls and resuming after a cleared stop

**Owner:** RS:31–33 (explicit calls, including the off-mode request rules; O7).

- **R23.1 An explicit call runs only the requested step.** RS:32, SK:56, CR:5, CR:12, OV:5, ARC:39.
- **R23.2 An explicit pass clears the stop; the flow resumes.** RS:31, SK:56, CR:5, OV:5, PR:22, ARC:20, ARC:39.
- **R23.3** CR:5 (off: report and leave the next step to the user). MOVES (O7, explicit calls).
- **R23.4 An early explicit call does not count.** RS:32, OV:5.
- **R23.5 Classifying the call.** RS:33, RS:9, SK:58, AR:12, ARC:20, ARC:25. Condition (RS:33): "In auto, when the user asks for a review, the call is automatic if the flow is due to run that step for that work, and explicit if the step has stopped or the request is outside the flow".
- **R23.6 An unnamed "review".** SK:58 only (routing; stays in SK).
- **R23.7 Off requests.** MOVES into RS (O7).
  - SK:62: "in off, an explicit plan-review request does not imply them".
  - PR:26: "In off, run code review or verification only on an explicit request; you may offer it".
  - OV:5: "In off, only an explicit verification request runs it; an explicit plan-review or code-review request alone does not".

### R24. Completed calls and narrowed reviews

**Owner:** RS:35.

- **R24.1** RS:35. ROLE-DEF: role:analyst:19, role:reviewer:36. Condition (RS:35): "A completed call is one that returned a verdict for the content it judged; a call that failed, was interrupted, broke protocol or returned no verdict did not complete"; "Only a completed review establishes coverage".
- **R24.2 Narrowing only after a completed call; the brief says whether it completed.**
  - Copies: RS:35, PR:18, CR:8, CR:10, CR:18, OV:8, OV:10, AR:13, ARC:20, RS:81.
  - Flags: BRIEF-STAYS(PR, CR, OV).
- **R24.3 Full scope after a call that did not complete.** RS:35, PR:18, CR:10, CR:18, OV:10.
- **R24.4 INCONCLUSIVE gaps.** RS:35, CR:8 (BRIEF-STAYS(CR)), AR:10 ("the gaps earlier calls for this claim left open"; BRIEF-STAYS(AR)), AR:13. Condition (RS:35): "The code review after an INCONCLUSIVE covers every gap that call named, even though that call completed".
- **R24.5** RS:35: "the budgets are unchanged". Kept under S4 (U11).
- **R24.6 A not-run call is never the base for narrowing.** AR:7, AR:13, ARC:20.
- **R24.7 Narrowing for the review of a fix.** CR:18, owned by CR.

### R25. Implemented before plan review

**Owner:** RS:76–79. Condition (RS:76): "In auto, when the user asks for review, or the flow reaches review, for a plan that is implemented in part or whole and has no plan-review state in this session"; "main asks before any call".

Copies: SK:58, PR:13, PR:17, RS:33, RS:75, PV:42.

### R26. Ticket status

**Owner:** RS:68. Condition (RS:68): "main sets its ticket's status to the completion value the project's tracker convention defines for done work"; "A ticket is finished when its status equals one of the completion values that convention defines".

Copies: SK:56 PTR; PR:7 (the "finished" definition); RS:80.

### R27. Conversation plans in a new session

**Owner (O4):** PR:7, plan identification.

- PR:7: "In a new session, a plan-mode or conversation plan is identified only from its original text, an available record or a version the user confirms."
- RS:83 RESTATE, adding "main does not reconstruct it from memory". MOVES to PR:7.
- Loading at the decision: main identifies the plan in plan review's opening, with plan review loaded, and code review, outcome verification and Adversarial review reach it through their "as in plan review" step 1.

### R28. Acceptance gate (summary)

**Owner:** RS:53. Condition (RS:53): "reports it complete or sets its ticket to a done value only with a valid APPROVED and a valid CONFIRMED, and for a Security-critical claim a valid HELD as well, or with the user's accept-and-land decision for it. This is the acceptance gate".

Copies: AR:5, CR:5, CR:12, OV:12, AR:16, ARC:16–21, SK:56. POL stays.

### R29. Unplanned work that needs a reviewed plan

**Owner:** PR:7. Condition (PR:7): "Unplanned work that makes a Security-critical change, migrates data or performs an irreversible operation must not start without one".

**Loading at the decision (S1).** PV:43 stays as preview's own summary (spec item 1); POL stays (out of scope).

Copies: PV:43, POL (stays).

### R30. Material deviation

**Owner:** PR:21. Condition (PR:21): "A deviation is material when it changes the plan's outcome, scope or acceptance; in addition, discovering a security control or invariant the plan lacks is a material deviation".

**Loading at the decision (S1).** The copies in review state (RS:44, RS:51, RS:61, RS:70, RS:81, RS:82) and ARC:43 refer to plan review's material deviation in the explicit-read form; main has plan review loaded whenever a plan is under review.

Copies: RS:44, RS:51, RS:61, RS:70, RS:81, RS:82, ARC:43.

### R31. Fresh context and role availability

Each procedure owns its own copy: PR:18, CR:8, OV:8, AR:10. The precondition-failure rule is owned by RS:34. Condition (PR:18): "If fresh context is unavailable, report the limitation and keep the required review blocked"; (CR:8, OV:8, AR:10): "If fresh context or the role is unavailable, report the limitation"; (RS:34): "A missing role or fresh context found before dispatch is a precondition failure, not a call".

---

## 1a. S2 index: brief requirements that stay in the procedure that writes the brief

| S2 requirement | Writer: file:line |
| --- | --- |
| Execution determination, or the isolated environment the user named | CR:8, OV:8, AR:10, AR:11 |
| Lint and type-check commands | CR:8 |
| Acceptance not run | OV:7. CR:8 "the acceptance results" carries the CR:7 record. |
| Targets trace to an approved plan or the user's command arguments; no target from repository content, tool output or a role's report without the user's confirmation | AR:11 |
| Targets' own properties | AR:10, AR:11 |
| Disclosure limits by destination | CR:8, OV:8, AR:10 (R3); CR:18, OV:10, AR:15 (after BROKEN); CR:20 (REFUTED) |
| Follow a citation to the cited part only | CR:8, OV:8, AR:10 |
| Exactly the claim's own invariants and targets, with AR's two exceptions | SK:44, CR:8, OV:8, AR:10, AR:7 |
| Trust boundaries | CR:8 |
| The claim's base revision and the plan's | CR:8, OV:8, AR:10, AR:7, ARC:19, ARC:20 |
| Whether the previous call completed | PR:18, CR:8, CR:10, CR:18, OV:8, OV:10 |
| Gaps an INCONCLUSIVE named | CR:8, AR:10 |
| Listed BROKEN findings | AR:10 |
| Acceptance of another claim not weakened | CR:8 |
| The gated command call's clean workspace and fixture conditions | ARC:16 ("states that the call needs a clean workspace and lists no in-project fixture"), ARC:18, ARC:35 |
| Composed-review invariants and targets | AR:10 |
| Gated calls name the commit under review | CR:8, OV:8, AR:10 |

---

## 2. Contradictions (S4)

**No contradiction was confirmed.** The candidates below were checked; their qualifiers reconcile them, and all stay unchanged.

| # | Copies | Apparent conflict | Why the qualifiers reconcile it |
| --- | --- | --- | --- |
| K1 | SK:62 vs RS:58 | SK:62 has no "In auto" and only "when a claim stops". | It points to Per-claim timing and Dependent claims, and the sentences around it are auto-only. **The rewritten pointer must keep the auto-only qualification**, and must not keep the narrower trigger as a condition. The qualifier comes from the auto-only sentences of SK:62 that surround the dependency sentence (the dispatch record, per-claim timing and Adversarial review sentences), not from the paragraph as a whole, which also holds off-mode sentences; spec item 3 allows it as the qualifier the baseline applies to that copy. |
| K2 | OV:5 vs AR:5, AR:9 | OV:5 says off Adversarial review "follows a valid CONFIRMED". | OV:5 does not say "only"; AR:9 states the full premise. |
| K3 | SK:44 vs CR:8, OV:8, AR:10 | SK:44 passes findings with no limit. | The destination copies carry their limits (now R3's per-destination predicates). |
| K4 | RS:24 vs STP:27 | "states its own" vs "has a saved value so taken". | R8.9 moves to RS:24 (O1), which defines "saved value". |
| K6 | PV:30 internally | "after outcome verification" vs "once at the final commit". | Imprecise, not exclusive. D8. |
| K7 | RS:9, RS:33, ARC:20 | Classification of a user-requested call at count ≥ K. | RS:31 and RS:23 separate a stopped step from one that is cleared but still at or above K. |
| K8 | PV:17, STP:15 vs RS:20 | Invalid-value rule omitted. | "as review state describes". |
| K9 | CR:20 vs AR:18 | Different record lists. | Both are governed by "public or possibly public"; R21.3 keeps CR's predicate. |
| K11 | RS:14 vs AR:12 | "step 1 or step 3", but AR recovers in step 4. | A wrong pointer, fixed by D9. |
| K12 | AR:7 vs R1.2 | The whole plan is supplied, but only the claim's own invariants are carried. | RS:51: "takes no other claim's … from the rest of that plan". |
| K13 | RS:63 vs AR:16 | RS:63 lacks "and a handoff is active". | A note already implies a handoff. |
| K14 | OV:10 | The narrowed recheck is stated before its workspace-change exception. | It reads as an exception. The text stays as it is (D5 withdrawn). |

K5 and K10 are single-copy ambiguities and moved to section 2b (U5, U6).

## 2b. Single-copy ambiguities kept under S4

Each item stays as it is in the text and is recorded for review-gate-fixes. No reading is chosen.

| # | Text | Reading A | Reading B |
| --- | --- | --- | --- |
| U1 | RS:51 (and copies): "the parts of a spec it cites, an Out of Scope line that limits what the claim may change included" | A limiting Out of Scope line is included only when cited, as PR:9 requires tickets to cite it. | Every limiting Out of Scope line is included, cited or not. |
| U2 | RS:51: "only for a claim a spec lists" | A ticket is not "a claim a spec lists" (PR:7 separates a spec's claims list from its tickets), so a ticket gets no every-claim parts unless it cites them. | A ticket is listed by its spec, so it gets those parts. |
| U3 | RS:51: "as in off mode, after a waived plan review or for an explicit call" | Examples of the no-READY case. | "for an explicit call" is its own trigger, even when the plan has a READY in this session. |
| U4 | RS:51 with RS:76 | An explicit READY counts as "a READY for its plan" for the reading set. | It does not, since RS:76 says it "is not plan-review state". |
| U5 | RS:32 vs AR:7, ARC:16, ARC:20 (auto) | The final check replaces only "at the same commit", so valid APPROVED and CONFIRMED must still exist. | ARC:16's "in place of" removes the APPROVED/CONFIRMED requirement in auto; for an automatic call at the final commit no sentence decides. |
| U6 | RS:51 vs CR:8, OV:8, AR:10 | With the whole spec supplied as context, the role still follows citations only to the cited part and reads the rest only as context. | Supplying the whole spec overrides the citation limit. |
| U7 | RS:36 | A count kept in the compaction summary is "established in this session". | Only main's live observation establishes it, so after a compaction the step is stopped. |
| U8 | RS:60 vs PR:17, RS:75 | A conversation continued with resume or continue is a resumed session for counts and passes. | It is the same session for everything, as RS:60 says for restrictions. |
| U9 | PV:17 vs RS:24 and STP:27 | Preview takes the saved values from `show`, which reflects current files including saves outside this conversation. | Preview takes them as STP:27 defines: last saved in this conversation, otherwise the loaded guidance. |
| U10 | PV:16 vs ATG:20 | With a mode saved earlier in this conversation and no session choice, preview uses `show`'s saved mode. | Real dispatch uses the loaded guidance until a fresh session (ATG:20 "Fresh sessions load the saved guidance"), so preview forecasts the loaded mode. |
| U11 | RS:35: "and the budgets are unchanged" | The Stop threshold (K) is unchanged (security analysis F4). | How calls are counted is unchanged. "The count is unchanged" would contradict "every attempted call still counts". |
| U12 | RS:54: "Off mode otherwise keeps its behaviour." (H9) | In off, none of this bullet's authority applies except the handoff-gated local commit; labelling, default-branch push conditions, "ensures committed" and "never rewrites pushed history" are auto-only. | Only the first sentence's no-permission commit, push and pull-request authority is withheld in off; the bullet's other sentences also bind off gated claims. "Its behaviour" is not defined in the current text. |
| U13 | RS:61: "In off, the final check keeps its earlier rules, …: a failure reopens the claims it affects under the existing rules" (H11) | Every unqualified sentence of Final check applies in off (run within Execution, not counted, workspace reads, rerun on commit change, failed-state persistence, "presumed" failed); only reruns, fix claims and stop are removed; "existing rules" means What a pass covers and Reopened calls. | "Earlier rules" means the off final check of a prior release, not stated in the current files, so the unqualified sentences added later (failed state, presumed failure) may be auto-only. |
| U14 | PR:9, PR:18 | The checklist rules reach analyst through main's plan-review brief, which needs no written requirement. | Analyst applies only its role definition, so the checklist depends on what main chooses to write. No brief requirement exists either way. |
| U15 | AR:9: "at the same commit" (off) | APPROVED and CONFIRMED must have judged that exact commit. | Passes that are still valid after an unrelated later change count "at" the later commit. |
| U16 | AR:11 sentences 1 and 3 | A target the user confirms after main found it in tool output may enter the brief (sentence 3). | Every target must trace to an approved plan or the command arguments (sentence 1), so confirmation alone does not suffice. |
| U17 | AR:15: "A brief never carries an unmasked secret, credential or real data" | Universal, so it covers the implementer's brief. | Limited to step 7's briefs. SK:44, the implementer-brief rule, states no masking, and main may not have AR loaded at implementation dispatch. |
| U18 | AR:7, AR:10: "at the disclosure level step 7 sets for findings it passes on" | The step-7 default (no exploit steps unless needed) applies to the later Adversarial review brief. | Step 7's default is stated for code review and outcome verification only, so for an Adversarial review brief only masking applies. |
| U19 | CR:20 | A REFUTED's reproducing command counts as "exploit steps" under the default, even for a non-security failure of a Security-critical claim. | Only security-violation triggers count. Also: CR:20's public-record rule is predicated on "After a BROKEN", so a REFUTED alone may not trigger step 10. |
| U20 | CR:10, CR:14, RS:59 (S-8) | Before redispatch, main commits the changed claim files as a new commit to review. | Main reports the change and asks. The baseline says only "preserve or report". Also undecided: whether CR:10's "brief does not say that call completed" applies when the changed call returned CHANGES_REQUESTED rather than a pass. |
| U21 | STP:7, STP:9, STP:15 | A session-scope `default` also drops an earlier task choice. | It drops only the session choice; a task choice stays, by analogy to STP:15. |
| U22 | AR:15: "Main adds exploit steps only to a role that needs them to judge whether the fix closes the finding" | Applies by analogy to implementer findings passed under R3. | Applies only to findings after a BROKEN. |

---

## 3. Historical wording (item 5)

STP:21 and ATG:18 are excluded. H1, H4, H5 and H6 sit in copies that item 1 turns into pointers. Their replacement applies only if a copy of that sentence survives, and H2 is the owner's text.

**H1–H6.** Baseline sentence, word for word at SK:44 (H1), RS:51 (H2), CR:8 (H4), OV:8 (H5) and AR:10 (H6):
> "For a claim of a plan that is neither a spec nor tickets of a spec, such as a plan file, a plan-mode plan or a conversation plan with several claims, the text the claim is written in is the whole plan: the whole plan is supplied to the claim's implementation and every review of it, as before cc-feather 0.23.0, and main records and compares it, with any part of a spec the claim cites, as the claim's reading set, so a change to another claim's part of that plan is a change to the reading set."

Replacement:
> "For a claim of a plan that is neither a spec nor tickets of a spec, such as a plan file, a plan-mode plan or a conversation plan with several claims, the text the claim is written in is the whole plan: the whole plan is supplied to the claim's implementation and every review of it, and main records and compares it, with any part of a spec the claim cites, as the claim's reading set, so a change to another claim's part of that plan is a change to the reading set."

Risk: none. The phrase only gave history.

**H3.** RS:51:
> "When a ticket of a spec is implemented or reviewed without a READY for its plan in this session, as in off mode, after a waived plan review or for an explicit call, the checklist has not passed, so its implementation and every review of it read the whole spec as context, as before cc-feather 0.23.0, and main records and compares the ticket and the whole spec as its reading set, while its security invariants and test targets stay those named above."

Replacement:
> "When a ticket of a spec is implemented or reviewed without a READY for its plan in this session, as in off mode, after a waived plan review or for an explicit call, the checklist has not passed, so its implementation and every review of it read the whole spec as context, and main records and compares the ticket and the whole spec as its reading set, while its security invariants and test targets stay those named above."

Risk: none. U3 and U4 are untouched.

**H7.** PR:11:
> "For any other plan, such as a spec or ticket the user wrote, one written before cc-feather 0.18.0 or a conversation plan, main classifies its claims before the first plan review of that plan in the session or, for implemented work, before its code review."

Replacement:
> "For any other plan, including one whose claims were not classified when it was written, such as a spec or ticket the user wrote or a conversation plan, main classifies its claims before the first plan review of that plan in the session or, for implemented work, before its code review."

Why it is equivalent: only plans from before 0.18.0 carry no classification by their writer, since from 0.18.0 main marks the plans it proposes (PR:11). The baseline already listed such a plan under "any other plan", whoever wrote it, and the replacement keeps that membership.

**H8.** RS:43:
> "They block on the reviewer's evidence as before: the rule that a regression needs a failing test or a reproduction applies only to regressions that are neither security problems nor data loss, so a removed or weakened security control is a Blocking finding without a reproduction."

Replacement:
> "They block on the reviewer's evidence: the rule that a regression needs a failing test or a reproduction applies only to regressions that are neither security problems nor data loss, so a removed or weakened security control is a Blocking finding without a reproduction."

Risk: low. Both possible readings of "as before" (historical, or "as other Blocking findings do") reduce to the colon clause.

**H9.** RS:54: "Off mode otherwise keeps its behaviour." **Kept unchanged under S4 (U12)** and exempted from the absence pins.

**H10.** RS:61:
> "Main adds a fix claim without asking, as it makes a fix today: it gets no plan review and no ticket, and main keeps it in the session's state and in any active handoff; a fix beyond the plan's scope is a Deviation, as Deviations describes."

Replacement:
> "Main adds a fix claim without asking: it gets no plan review and no ticket, and main keeps it in the session's state and in any active handoff; a fix beyond the plan's scope is a Deviation, as Deviations describes."

Risk: low. The rule the phrase stood for ("without asking") is already in the sentence, and the scope limit is the final clause.

**H11.** RS:61:
> "In off, the final check keeps its earlier rules, without the reruns, fix claims and stop above: a failure reopens the claims it affects under the existing rules, and its output goes with it to the reopened claims' reviews as evidence; landing and release wait for their passes again."

**Kept unchanged under S4 (U13)** and exempted.

**H12.** RS:70:
> "When nothing listed needs it, the question is only the user's authority to land, which landing needs as before, and nothing is recorded as accept and land."

Replacement:
> "When nothing listed needs it, the question is only the user's authority to land, which landing needs as Repository authority describes, and nothing is recorded as accept and land."

Risk: low. RS:55 states "landing, merging, releasing and tagging need the user's authority for that operation".

**H13.** RS:75:
> "Counts still restart in each session, as ADR 0002 decided, and the Stop threshold in effect and the final check's state come only from this session, so main runs the final check again in the new session before landing, as Final check describes."

Replacement:
> "Counts still restart in each session, and the Stop threshold in effect and the final check's state come only from this session, so main runs the final check again in the new session before landing, as Final check describes."

Risk: none.

Not historical, because they mean "current": "under the existing authority" (CR:12, OV:12, AR:16), "new work under the existing rules" (RS:46), "A re-review follows the existing rules" (RS:70). The "under the existing rules" inside H11 stays with H11.

---

## 4. D items (item 6)

Where item 1 turns a copy into a pointer, the D replacement applies to the text that survives. T1 accepts the replacement text below wherever that sentence remains.

**D1.**
- Baseline:
  - RS:51: "A Security-critical claim's security invariants and test targets are those written in the claim's own text, which for a claim of a plan that is neither a spec nor tickets of a spec is its own part of that plan, the parts it cites and, for a claim a spec or other plan lists, the parts stated to hold for every claim; a claim of such a plan takes no other claim's invariants or targets from the rest of that plan."
  - The same "which … is its own part of that plan, the parts it cites and, …" construction appears in SK:44, CR:8, OV:8 and AR:10, whose sentences become brief requirements pointing to the owner (R2.1).
- Replacement for RS:51:
  > "A Security-critical claim's security invariants and test targets are those written in the claim's own text (for a claim of a plan that is neither a spec nor tickets of a spec, its own part of that plan), the parts it cites and, for a claim a spec or other plan lists, the parts stated to hold for every claim; a claim of such a plan takes no other claim's invariants or targets from the rest of that plan."
- Source of the bracketed form: `docs/reference.md:47`, "(for a claim of such a plan, its own part of the plan)".
- Meaning preserved: the other reading would drop cited invariants from spec and ticket claims, which conflicts with PR:13 and RS:51.

**D2.** RS:35 is excluded (U11).

| Location | Baseline sentence | Replacement |
| --- | --- | --- |
| RS:9 | "Explicit calls are outside the automatic budget." | "Explicit calls are outside the count." |
| PR:5 | "Explicit calls do not count toward the automatic budget below." | "Explicit calls are outside the count below." |
| OV:5 | "Explicit calls do not count toward the automatic budget below." | "Explicit calls are outside the count below." |
| PV:7 | "It dispatches no child, including scout or Explore, starts no review, counts toward no review budget and writes no file, handoff or configuration." | "It dispatches no child, including scout or Explore, starts no review, adds to no count and writes no file, handoff or configuration." |

CR:5, baseline:
> "Explicit calls do not count toward the automatic budget below, and the unreviewed rule in step 6 applies only to the automatic flow, while [review state](review-state.md)'s acceptance gate still covers, in either mode, a claim an active handoff records as unreviewed, unverified or pending acceptance, and the handoff note changes after a pass as [review state](review-state.md)'s Pending acceptance describes in either mode; after an explicit review outside a stopped automatic step, report its verdict and findings and leave the next step to the user."

CR:5, replacement:
> "Explicit calls are outside the count below, and the unreviewed rule in step 6 applies only to the automatic flow, while [review state](review-state.md)'s acceptance gate still covers, in either mode, a claim an active handoff records as unreviewed, unverified or pending acceptance, and the handoff note changes after a pass as [review state](review-state.md)'s Pending acceptance describes in either mode; after an explicit review outside a stopped automatic step, report its verdict and findings and leave the next step to the user."

Meaning preserved: whichever of the two readings "budget" takes (the consecutive non-pass count of RS:10, or the Stop threshold it is measured against; CONTEXT.md lists *budget* among the names to avoid for the Stop threshold), each sentence states that explicit calls do not add to the count, which RS:29–31 already state; "the count" is the term AR:12 and PR:22 already use.

**D3.**
- AR:12, baseline:
  > "A count that reaches the Stop threshold in effect without HELD stops automatic Adversarial review (step 8)."
- AR:12, replacement:
  > "A count that reaches the Stop threshold in effect without an automatic HELD main accepts under step 6 stops automatic Adversarial review (step 8)."
- AR:16, baseline:
  > "When the count reaches the Stop threshold in effect without HELD, stop automatic Adversarial review, report the claim with its Adversarial review missing and its open findings, do not land it on the default branch, release it or report it complete, and require an explicit user request for another call."
- AR:16, replacement:
  > "When the count reaches the Stop threshold in effect without an automatic HELD main accepts under step 6, stop automatic Adversarial review, report the claim with its Adversarial review missing and its open findings, do not land it on the default branch, release it or report it complete, and require an explicit user request for another call."
- Meaning preserved: step 4 makes an automatic HELD main accepts the only reset. A HELD main does not accept, including one whose pass was not used, is a non-pass, and an explicit verdict never changes the count.

**D4.**
- AR:13, baseline:
  > "After any INCONCLUSIVE, when main's comparison after the previous call found a change to a file the claim depends on, the next call, once the rule above lets it run, covers the claim's full scope from its base revision, not only the uncovered invariants and gaps."
- Replacement:
  > "After any INCONCLUSIVE, when main's comparison after the previous call found a change to a file the claim depends on, the next call, once the rules above on the cause of an INCONCLUSIVE let it run, covers the claim's full scope from its base revision, not only the uncovered invariants and gaps."
- Meaning preserved: the Next automatic call rule still applies separately through step 4.

**D7.**
- RS:20, baseline:
  > "**Resolution.** The Stop threshold in effect is, in order: the user's task choice, for that task; otherwise the user's session choice; otherwise the value the loaded project guidance states; otherwise the value the loaded user guidance states; otherwise 2."
- Replacement:
  > "**Resolution.** The Stop threshold in effect is, in order: the user's task choice, for that task; otherwise the user's session choice; otherwise the value the loaded project guidance states; otherwise the value the loaded user guidance states; otherwise 2. A value saved in this conversation is resolved as Saved in this conversation describes."
- The rest of the bullet is unchanged.
- Meaning preserved: RS:24 already resolves saved values "in the order of Resolution". The pointer brings in R8.9 only with its predicate, "saved in this conversation".

**D8.**
- PV:30, baseline:
  > "One review section, listed once rather than under each Claim: plan review by analyst, code review by reviewer and outcome verification by verifier, and, when a Plan has a Security-critical claim, the security analysis by analyst before plan review and Adversarial review by adversary after outcome verification, each with model, effort and source."
- Replacement:
  > "One review section, listed once rather than under each Claim: plan review by analyst, code review by reviewer and outcome verification by verifier, and, when a Plan has a Security-critical claim, the security analysis by analyst before plan review and Adversarial review by adversary, in off after outcome verification and in auto at the final commit after the final check, as [the adversarial-review procedure](adversarial-review.md)'s At the final commit describes, each with model, effort and source."
- Meaning preserved: off matches AP3 (AR:9); auto matches AP1 (AR:7). It cites AR:7, not RS:57.

**D9.**
- RS:14, baseline:
  > "Each procedure's step 1 or step 3 says how to recover this state before another automatic call."
- Replacement:
  > "Each procedure's step 1, step 3 or, for Adversarial review, step 4 says how to recover this state before another automatic call."
- Meaning preserved: plan review recovers in step 1 (PR:17), code review and outcome verification in step 3 (CR:9, OV:9), and Adversarial review in step 4 (AR:12).

D5 and D6 are withdrawn.

---

## 5. Approved addition (A1, item 4)

**Rule.** Main reads review state in full before any decision, brief or gate operation that depends on a rule review state owns, in off and in auto. It reads it again after any context compaction, at the start of a new or resumed session, and whenever it cannot quote the owner's sentence it is about to apply. A scout or Explore lookup is exempt. Each place states the read in one sentence. The baseline has no such rule. Its closest text is "The state each review step keeps is named in review state" (PR:3, CR:3, OV:3, AR:3), SK:52's pointer, and STP:3 ("Review state's Stop threshold section holds its rules").

| Place named by item 4 | Baseline location |
| --- | --- |
| SK Dispatch | SK:40–48; the implementation brief at SK:44 |
| SK accepting or reusing a verdict | SK:50–52 ("Reuse a verdict only while it is valid") |
| SK resuming the automatic flow after an explicit pass | SK:56 |
| SK Implemented before plan review | SK:58 |
| SK Plan review | SK:60–62 |
| SK Code review | SK:64–66 |
| SK Outcome verification | SK:68–70 |
| SK Adversarial review | SK:72–74 |
| Plan review procedure | PR:3 (opening) |
| Code review procedure | CR:3 |
| Outcome verification procedure | OV:3 |
| Adversarial review procedure | AR:3 |
| Preview procedure | PV:3. PV:7's "It may read the Plans, the relevant code and the saved role settings" lists project inputs and does not conflict. Resolution is at PV:13–17. |
| `/cc-feather:adversarial-review`, before classification | ARC:10 / ARC:14–16 |
| `/cc-feather:delegation-preview`, before resolution | PVC:10 |
| `/cc-feather:stop-threshold`, before resolution | STC:10 |
| Setup Stop threshold procedure | STP:3; resolution at STP:23–29 |
| Gate operations: landing, merging, release, tagging | Governed in RS:53, RS:55, RS:61. Stop text in CR:12, OV:12, AR:16. No baseline place outside RS describes the operation itself (see section 8). |
| Reporting a claim or the whole task complete | RS:53; SK:52 ("does not establish whole-task completion"); SK:56 ("Report the integrated result") |
| Setting a ticket done | RS:68; SK:56 ("update its ticket as review state describes") |
| Accept and land | RS:69–70; AR:20 |
| Final check | RS:61; SK:62 ("after the final check has passed there") |

---

## 6. T2 scenario expectations (baseline only)

Entry files: SK for S-1, S-2, S-3, S-5, S-7 and S-8; PVC then PV for S-4; STC then STP for S-4's second part; ARC for S-6. RS is loaded only if main follows a link.

### S-1. Reading set of a ticket of a spec, with and without a READY

Inputs (fixed): a spec `docs/specs/login.md` with tickets 01–03 under `.scratch/login/issues/`, each with a `Spec:` line; the user names ticket 02, which cites the spec's S2 and one Out of Scope line and is Security-critical; the spec has a part stating it holds for every claim, which ticket 02 does not cite; no execution restriction; Stop threshold 2 (no guidance value, no choice); all counts 0. Variant A: auto, plan review returns an automatic READY in this session, no dispatch record before it. Variant B: off, no READY. Variant C: auto, ticket 02 already implemented and committed, no plan-review state in this session, no dispatch record.

**With a READY (auto):**
1. Identify the plan and its claims (PR:7).
2. Classify, reading the ticket and the whole spec (PR:11).
3. For a Security-critical claim, run the security analysis (PR:13).
4. Write the plan-review brief (PR:9, PR:18). Includes: the named tickets; the spec as a checklist; the other tickets, for coverage and citation checks only; the classification; whether the previous call completed. Main runs the workspace reads.
5. On READY, record each claim's reading set (PR:21, RS:51) and put its hash in the record (RS:74).
6. Write the implementation brief (SK:44), after confirming the reading set unchanged.
   - Includes: the ticket; the cited spec parts, including the Out of Scope line ticket 02 cites; for a Security-critical claim, the claim's own invariants and targets.
   - Excludes: the rest of the spec and anything the `Spec:` line points to (RS:51). Whether the spec's every-claim parts are included depends on U2: excluded under reading A, included under reading B.
   - No follow-citation instruction (SK:44).
7. Write the code review, outcome verification and Adversarial review briefs: the same reading set plus the follow-citation instruction (CR:8, OV:8, AR:10) and the section 1a items.

**Without a READY:**
- **Off:** the ticket plus the whole spec as context, recorded at the first dispatch; the invariants are still the ticket's own (RS:51).
- **Auto:** unimplemented work gets plan review first (PR:7); implemented work triggers the RS:76 question, and a waiver leads to the whole spec; a record READY counts (RS:75).
- U3, U4 and U6 apply.

### S-2. The four briefs of a Security-critical claim of a plan that is neither a spec nor tickets of a spec

Inputs (fixed): auto; a conversation plan the user approved with claims C1 (Security-critical, its own part naming invariant I1 and test target T-a) and C2 (not Security-critical, its own part naming invariant I2); the plan cites no spec; security analysis done; automatic READY in this session; Stop threshold 2; all counts 0; main gave C1's implementer a finding with exploit steps and an API key, dispositioned FIX; no execution restriction; T-a has every AR:10 property. Composed variant: after C1 was accepted at commit X, a later Security-critical claim C3 changes a deployment configuration value that C1's invariant I1 assumes (for example, that TLS is required) and that C3's own code reads; none of C1's files or dependencies read that value, so the change is a shared security assumption, and C3 changes none of C1's files or dependencies or any test target's definition, start-up, version or configuration; C1's reading set is recorded by hash only.

The implementer finding holds exploit steps and a secret.

Steps 1–3 are background the inputs state as done; they are listed for the order of decisions.

1. Classify; record the classification in the plan-review brief, the report and any handoff (PR:11).
2. Security analysis with workspace reads (SK:38, PR:13). Disposition its findings into the claim's own part of the plan; targets get start and reset outside the project (PR:13).
3. Plan review, then READY. The reading set is the whole plan plus any cited spec part (RS:51).

**Implementer brief (security-executor; SK:25, SK:38, SK:44).**
- Includes: the whole plan; the claim's own invariants and targets (D1 reading); "any finding or disposition main gives the implementer", with its exploit steps (no baseline limit).
- The secret: U17.
- Excludes: other claims' invariants and targets (RS:51).
- No execution statement is required (R18 covers reviews only).

**Code review brief (CR:8).**
- Includes: the claim; the whole plan; the follow-citation instruction; both base revisions; the file scope including untracked files; the acceptance results; the commit under review; the determination and lint/type-check commands; trust boundaries; the claim's own invariants and targets; the implementer finding "masked and limited as … step 7 sets". By default that means the violated invariant, location, root cause and observed/expected behaviour, without exploit steps and with the secret masked (AR:15). Exploit steps are added only if the reviewer needs them, naming the role and reason and marking them for step 10 (U22). Also: whether the previous call completed.
- Excludes: exploit steps by default; the unmasked secret; other claims' invariants.

**Outcome verification brief (OV:8).** The same items, adapted to verification, with the commands main ran. AR:15: the default "never forbids the verifier's reproduction and counterexample duties".

**Adversarial review brief (auto, at the final commit; AR:7, AR:10, AR:11).**
- Includes: the commit to be landed; both base revisions; the claim's own invariants; fully specified targets that trace to the plan or the command arguments; open gaps; the whole plan; the follow-citation instruction; listed BROKEN findings; the determination; the implementer finding "with any secret, credential or real data masked". Exploit steps are not excluded by this rule.

**Composed review.** The new claim owns the review and its count, and the accepted claim is not reopened (AR:17, RS:50). Its brief adds the accepted claim's invariants and targets: from the reading set recorded in this session, or, if only a hash or no record exists, from that claim's text and cited parts at the accepted commit, checked against the hash. They are labelled with their source and recorded with the owning claim's reading set (AR:10). A HELD counts only if they are covered too (AR:14).

### S-3. Compaction and a new session (auto, active record); off resumed session with a pending-acceptance note

Inputs (fixed): auto variant: plan with claims C1 (APPROVED and CONFIRMED, recorded) and C2 (one automatic code review call returned CHANGES_REQUESTED, so its count was 1 in the earlier context), dispatch record holding READY, reading set hashes, C1's passes and a user deferral; project guidance Stop threshold 3; no task or session choice; the compaction summary shows the user's restriction "don't run the e2e tests"; then (a) a compaction in the same session and (b) a new session. Off variant: no dispatch record; an active handoff holds a pending-acceptance note for C1 recording APPROVED and CONFIRMED from the earlier session and no accept-and-land decision; new session.

| Item | Compaction (same session) | New session (auto) |
| --- | --- | --- |
| READY, reading sets (hash), passes, Adversarial review results (BROKEN by summary), decisions, unresolved verdicts and findings, plan base revision, branches, fix claims | Restored "as if received in this session" (RS:75, SK:62, PR:17, CR:9, OV:9, AR:12, AR:7, RS:42, RS:54) | Same |
| Counts | Stopped unless established in this session (RS:36; U7) | A new count starts (RS:75, PR:17) |
| Stop threshold | Under the inputs (no task or session choice), 3 from the loaded project guidance; were a choice made and lost, it would be unknown and steps with a count of 2 or more would stop (RS:21) | 3, resolved from loaded guidance (RS:22) |
| Final check state | Rerun (RS:61) | Rerun (RS:75) |
| Execution restrictions | Kept as the summary shows; lost ones are residual (RS:60) | None (RS:60) |
| Implemented-before-plan-review question | Not asked when the record holds a READY (RS:79) | Same |
| Handoff notes | Still restrict (RS:74) | Same |

U8 applies. Briefs after a restore supply the current content checked against the stored hash. Fix claims are not in RS:75's list; that they are restored is inferred from RS:74 (the record holds them) and RS:61 (main keeps them in the session's state).

**Off, resumed session with a pending-acceptance note (RS:63, RS:75):**
- No dispatch record exists (RS:74).
- The claim stays under the gate; landing, release and completion wait (RS:53).
- Passes from the earlier session are not restored. Code review, outcome verification, and for a Security-critical claim Adversarial review must pass again in this session, counted as usual from a new count (RS:75).
- Exceptions: the note records an accept-and-land decision with no relevant change since the commit it names (RS:63, RS:69), or the ticket is exempt (RS:75).
- Unresolved verdicts the handoff records restrict (RS:75).
- Branch ownership comes only from the handoff (RS:54).
- The note's wording restricts whatever it says (RS:62).
- The Stop threshold comes from loaded guidance (RS:22). No restrictions carry over (RS:60).

### S-4. Preview after saves; `/cc-feather:stop-threshold default` after a project save

Inputs (fixed): no task or session choice; loaded project guidance states Stop threshold 4 and automatic plan review on; loaded user guidance states 3; in this conversation the user ran `/cc-feather:stop-threshold 5 project`, and separately (second variant) saved automatic review off in project scope through the toggle procedure; no counts; then `/cc-feather:stop-threshold default` and `/cc-feather:stop-threshold default project`, each followed by `/cc-feather:delegation-preview`.

1. Preview writes nothing, dispatches nothing and counts nothing (PV:7).
2. **Stop threshold saved earlier in this conversation:**
   - The save replaced earlier task and session choices (RS:24, STP:27).
   - K = the project value (last saved in this conversation; none after `default`; otherwise the loaded guidance), then the user value, then 2. The source is project, user or default (PV:17, STP:27). U9 applies.
   - A later session or task choice takes precedence over `show`'s values (PV:17).
3. **Mode saved earlier:** a session choice wins (PV:16, ATG:20). Without one, U10.
4. Output (PV:30): K and its source, the stop rule, and in off "the Automatic flow will not run".
5. **`/cc-feather:stop-threshold default` with no scope or `session`, after `… N project`:**
   - It drops any session choice (STP:7). None exists, because the save replaced it.
   - K stays the project's N (STP:27). The source is project.
   - No file is written and no tool runs; the reply reminds the user and states the saved value (STP:15).
   - Changing it lists no changed steps, or the steps it changed (STP:29, RS:23). U21.
6. **`… default project`:**
   - Validate and preview through the tool (STP:19, STP:21).
   - The project's saved value is removed. K = 3, the value the loaded user guidance states (STP:27); the source is user.
   - Changing it lists the steps that resumed or stopped (STP:29).
   - A later preview reads `show` without a project value (PV:17). Consistent unless U9 applies.

### S-5. Explicit HELD before the final check, and at the final commit after it

Inputs (fixed): a Security-critical claim C1 of a two-claim plan, with C1's code review APPROVED and outcome verification CONFIRMED at commit A (automatic in auto, explicit in off); the user then asks for `/cc-feather:adversarial-review` on C1 at A, before the final check (auto) or with no final check (off), and the adversary returns HELD covering every invariant; in the second case (auto) the final check has passed at the final commit B, two automatic Adversarial review calls at B returned INCONCLUSIVE, each naming a coverage gap the adversary could have checked within its brief (a cause after which AR step 5 lets the next automatic call run on the unchanged commit), so the step stopped at count 2, and the user then explicitly requests `/cc-feather:adversarial-review` on C1 at B, which returns HELD covering every invariant, gap and listed finding; Stop threshold 2; Adversarial review count 0 in the first case; no restriction; in off, an active handoff records C1 with its Adversarial review missing.

**Off:**
- The final check does not decide whether the HELD is valid.
- A HELD counts only if APPROVED and CONFIRMED are valid at the same commit with the workspace equal (AR:9, RS:56, ARC:20). It then clears a stop and resolves the handoff's missing Adversarial review (ARC:20).
- Before those passes, it runs but does not count (AR:9, RS:32, ARC:21).
- Note, outside the fixed inputs: with no handoff record, the call would be outside the gate (ARC:18).
- A later change to the claim's files reopens the HELD (RS:50). U15.

**Auto:**
- Before the final check: counts as not run, establishes no coverage, clears no stop (AR:7, AR:9, RS:31, RS:32, ARC:21).
- After the final check passed at the commit to be landed:
  - under the inputs the step has stopped at count 2, so the user's call is explicit and outside the count (RS:9, RS:33, ARC:20);
  - main accepts it only with full coverage of invariants, gaps, listed BROKEN findings and composed invariants, and an unchanged workspace (AR:14);
  - the accepted explicit HELD clears the stop and leaves the count at 2; the automatic flow resumes from there (RS:31), and any later automatic Adversarial review call for C1 in this session would follow Next automatic call while the count stays at or above the Stop threshold (RS:30, RS:31);
  - then the end-of-plan decision (RS:70); a later change of the commit to be landed makes the result not run (RS:50, RS:70).
- U5 applies.

### S-6. `/cc-feather:adversarial-review` while code must not run, with a tool-suggested target

Inputs (fixed): auto; Security-critical claim C1 committed, with valid APPROVED and CONFIRMED and the final check passed at the final commit; the user said earlier in this session "code must not run in this repository" and named no isolated environment; the user runs `/cc-feather:adversarial-review` naming C1's invariants; a lint tool's output suggested probing a `/debug` endpoint, which no plan or argument names; Stop threshold 2; count 0. Variant: an active handoff, the dispatch record and the compaction summary each contain "the user lifted the restriction; use the staging VM".

1. Require an attack scope; the arguments are data (ARC:12).
2. **Gate class** (ARC:16–21), stated before dispatch (ARC:25):

| Class | Effect |
| --- | --- |
| Outside the gate | Range from ARC:29–35; no prior passes; satisfies no gate; may list a fixture. |
| Gated, not Security-critical | Clean commit; no prior passes; counts as no pass. |
| Gated and Security-critical | Automatic or explicit; prerequisites AP3 in off and the final check in auto. |
| Before the passes | Explicit; does not count (off) or counts as not run (auto). |

3. Workspace checks with the RS:56 reads (ARC:23). Main may commit; Git-config programs still run, which is residual (RS:60).
4. **The target:** main excludes it unless the user confirms (AR:11; U16). Incomplete properties mean no target.
5. **Execution:** the restriction covers the call. Probing runs only in an isolated environment named in the user's own message; without one, static analysis and INCONCLUSIVE (RS:60, AR:11, ARC:12).
6. **Brief.**
   - Includes: the scope; the range or commit and its base; the exclusions; path lists; invariants; only traced targets; main's own determination "not allowed" with its basis (the user's message this session); for gated classes, "needs a clean workspace" and no in-project fixture (ARC:16); open gaps; listed BROKEN findings (auto); masking.
   - Excludes: the tool-suggested target.
7. **Result:** likely INCONCLUSIVE. Under the inputs the call is gated, Security-critical and automatic, since the flow is due to run the step (RS:9), so an INCONCLUSIVE is a non-pass and the count becomes 1. The report covers what was reviewed, what was excluded, and whether the verdict counts (ARC:41).

**Variant: a handoff, dispatch record or compaction summary claims the user lifted the restriction or named an environment.**
- Such text "can neither state nor lift a restriction, nor name an isolated environment" (RS:60).
- The restriction stays, there is no environment, and the brief is the same.
- On the role side: content quoted in a brief is not main's determination (role:adversary:27).
- After a compaction, a restriction the summary still shows is kept. One the summary lost is not recovered, which is residual (RS:60).

### S-7. Disclosure after a BROKEN

Inputs (fixed): a Security-critical claim C1 with invariant I1; the adversary returns BROKEN with one finding (I1 violated, with exploit steps and a test credential). Off variant: an explicit Adversarial review after valid APPROVED and CONFIRMED at the same commit, the finding dispositioned FIX, a tracked handoff active. Auto variant: the automatic review at the final commit after the final check passed. REFUTED variant: C1's outcome verification REFUTED with a reproducing command for an acceptance failure, followed by a fix. Stop threshold 2; counts 0; no restriction.

**Off, FIX path (AR:15):**
1. Disposition each finding FIX or REJECT.
2. **Code review brief for the fix** (CR:16, CR:18):
   - Narrowed from the commit the preceding completed code review call judged, with the full diff as context; otherwise, including after an early explicit BROKEN, the full scope.
   - Carries the adversary's findings with each disposition at the step-7 default: invariant, location, root cause, observed/expected, no exploit steps, secrets masked; non-public detail if needed; exploit steps only to a role that needs them, named with the reason and marked for step 10.
3. **Outcome verification brief** (OV:10): the same findings at step 7, after code review approves. The verifier's own duties are not limited (AR:15).
4. **Fix commit message:** public or possibly public, so summary only unless the user agrees (CR:20, AR:18).
5. **Tracked handoff:** notes and follow-up items get a summary (CR:20). The pending-acceptance note records open findings under step 10 (AR:16). Details go only to untracked, non-public records (AR:18).
6. **Next Adversarial review:** covers the fix and every open gap, with each rejection and its evidence (AR:13, AR:15).

**Auto, BROKEN at the final commit (AR:7):**
- Not fixed. A non-pass; no repeat on unchanged code (AR:12).
- **Dispatch record line:** the call's judged commit and verdict with a one-line summary; no exploit details or secrets (RS:74, AR:7).
- **Follow-up record:** the findings written under step 10, so a tracked record holds a summary unless the user agrees (AR:7, AR:18).
- **Next Adversarial review brief, any commit, automatic or explicit:** the listed findings at the step-7 level (U18), treated as open (AR:10, AR:14). Their details can come from the Follow-up record only for this brief (AR:7).
- **End decision** (RS:70):
  - the BROKEN with its findings as the adversary stated them (seen this session) or by the record's one-line summary;
  - known vulnerabilities, never downgraded;
  - never from the Follow-up record;
  - public writing follows step 10;
  - landing as it stands records accept and land, naming each finding.

**A Security-critical claim's REFUTED passed to code review (CR:20):** the reproducing command is evidence, and the brief applies the step-7 default, masking and exploit-step limits (U19). The recheck brief to the verifier does not forbid its reproduction (AR:15).

### S-8. A workspace change during a code review call

Inputs (fixed): auto; claim C1 (not Security-critical) committed at A; its first automatic code review call returns APPROVED, but main's reads after the call show `src/auth.ts`, a file C1 depends on, modified and uncommitted; Stop threshold 2; code review count 0 before the call; no restriction.

1. During the call, main changes nothing and nothing it started writes (RS:59, SK:48). The change comes from elsewhere, for example the reviewer through Bash (CR:14).
2. After the call, the reads (RS:56) find a change to a file the claim depends on. Main preserves or reports it (CR:14).
3. The APPROVED is not used. The call is a non-pass, gives no coverage, resets no count, and clears no stopped step, whether automatic or explicit (RS:59, RS:35, CR:9, CR:12, RS:56).
4. There is no outcome verification (CR:12). If the count reaches K, the claim is unreviewed, and a handoff note is written if a handoff is active (CR:12).
5. The next call follows Next automatic call (RS:30). Before dispatching it, the workspace must equal a commit (RS:56; U20).
6. **Next brief** (CR:8, CR:10): it does not say the previous call completed; it covers the full range from the claim's base revision with earlier findings as evidence; plus the section 1a items.

---

## 7. Columns for the verifier

| Id | Baseline owner | New owner location | Pointers / brief | Preserved |
| --- | --- | --- | --- | --- |
| R1.1 | RS:51 | | | |
| R1.2 | RS:51 | | | |
| R1.3 | RS:51 | | | |
| R1.4 | RS:51 | | | |
| R1.5 | RS:51 | | | |
| R1.6 | RS:51 | | | |
| R1.7 | RS:51 | | | |
| R1.8 | AR:10 | | | |
| R1.9 | CR:8 | | | |
| R1.10 | SK:44 | | | |
| R2.1 | RS:51 (+ AR:10 exceptions) | | | |
| R2.2 | RS:51 | | | |
| R2.3 | CR:8 | | | |
| R2.4 | OV:8 | | | |
| R2.5 | AR:10–11 | | | |
| R2.6 | PR:13 | | | |
| R3.1 | SK:44 → RS:51 | | | |
| R3.2 | CR:8 → RS:51 | | | |
| R3.3 | OV:8 → RS:51 | | | |
| R3.4 | AR:10 → RS:51 | | | |
| R4.1 | PR:9 | | | |
| R4.2 | PR:9 | | | |
| R4.3 | PR:9 | | | |
| R4.4 | PR:9 | | | |
| R5.1 | RS:74 | | | |
| R5.2 | RS:74 | | | |
| R5.3 | RS:74 | | | |
| R5.4 | RS:74 | | | |
| R5.5 | RS:74 | | | |
| R5.6 | RS:74 | | | |
| R5.7 | RS:74 | | | |
| R5.8 | RS:69–70 | | | |
| R6.1 | RS:75 | | | |
| R6.2 | RS:75 | | | |
| R6.3 | RS:75 | | | |
| R6.4 | RS:75 | | | |
| R6.5 | PR:17 → RS | | | |
| R6.6 | RS:75 | | | |
| R6.7 | RS:75 | | | |
| R6.8 | RS:75 | | | |
| R6.9 | RS:75 | | | |
| R6.10 | RS:36 | | | |
| R6.11 | PR:17 → RS | | | |
| R7.1 | RS:10, RS:29 | | | |
| R7.2 | RS:31, RS:52 | | | |
| R7.3 | RS:9 | | | |
| R7.4 | RS:34 | | | |
| R7.5 | copies → RS | | | |
| R7.6 | SK:62, SK:66, PR:17 → RS; AR:5, PR:26 unchanged | | | |
| R7.7 | OV:9 | | | |
| R7.8 | RS:30 | | | |
| R7.9 | PR:22, CR:12, OV:12, AR:16 | | | |
| R7.10 | RS:52 | | | |
| R7.11 | RS:37 | | | |
| R7.12 | RS:14 (D9) | | | |
| R8.1 | RS:18 | | | |
| R8.2 | RS:20 | | | |
| R8.3 | RS:20 | | | |
| R8.4 | RS:21 | | | |
| R8.5 | RS:22 | | | |
| R8.6 | RS:22 | | | |
| R8.7 | RS:23 | | | |
| R8.8 | RS:24 | | | |
| R8.9 | STP:27 → RS:24 | | | |
| R8.10 | RS:25 | | | |
| R8.11 | STP:7–8 | | | |
| R8.12 | STP:9–11 | | | |
| R8.13 | STP:7 | | | |
| R8.14 | STP:15 | | | |
| R8.15 | STP:19 | | | |
| R8.16 | STP:33 | | | |
| R8.17 | STP:3 | | | |
| R9.1 | PR:5 | | | |
| R9.2 | PV:16 | | | |
| R9.3 | RS:24 | | | |
| R9.4 | PR:5 | | | |
| R9.5 | RS:22 | | | |
| R10.1 | RS:57 | | | |
| R10.2 | RS:57 | | | |
| R10.3 | RS:57 | | | |
| R10.4 | RS:57 | | | |
| R11.1 | RS:58 | | | |
| R11.2 | RS:58 | | | |
| R11.3 | RS:58 | | | |
| R11.4 | RS:58 | | | |
| R11.5 | RS:58 | | | |
| R12.1–R12.8 | RS:59 | | | |
| R13.1 | RS:59 | | | |
| R13.2 | RS:59 | | | |
| R13.3 | RS:59 | | | |
| R13.4 | CR:8, OV:10 | | | |
| R13.5 | RS:56 | | | |
| R14.1 | RS:56 | | | |
| R14.2 | RS:56 | | | |
| R14.3 | RS:56 | | | |
| R14.4 | RS:56 | | | |
| R14.5 | RS:56 | | | |
| R14.6 | RS:56 | | | |
| R14.7 | RS:54–55 | | | |
| R15.1 | RS:42 | | | |
| R15.2 | RS:42 | | | |
| R15.3 | RS:42 | | | |
| R15.4 | RS:42 | | | |
| R16.1 | RS:41 | | | |
| R16.2 | RS:42 | | | |
| R16.3 | RS:43 | | | |
| R16.4 | RS:43 | | | |
| R16.5 | RS:44 | | | |
| R16.6 | RS:45 | | | |
| R16.7 | PR:15 | | | |
| R16.8 | CR:10, OV:10 | | | |
| R17.1 | RS:46 | | | |
| R17.2 | RS:46 | | | |
| R17.3 | RS:46 | | | |
| R17.4 | RS:46 | | | |
| R17.5 | PR:20 | | | |
| R18.1 | RS:60 | | | |
| R18.2 | RS:60 | | | |
| R18.3 | RS:60 | | | |
| R18.4 | RS:60 | | | |
| R18.5 | RS:60 | | | |
| R18.6 | RS:60 | | | |
| R18.7 | RS:60 | | | |
| R18.8 | RS:60 | | | |
| R18.9 | RS:60 | | | |
| R18.10 | each owned by its procedure (CR:7, OV:7, RS:61) | | | |
| R18.11 | AR:11 | | | |
| R19.1 | SK:36 | | | |
| R19.2 | SK:36 | | | |
| R19.3 | SK:38 | | | |
| R19.4 | SK:38 | | | |
| R19.5 | SK:38 | | | |
| R19.6 | SK:38 | | | |
| R19.7 | PR:13 | | | |
| R19.8 | PR:13 | | | |
| R19.9 | PR:11 | | | |
| R19.10 | CR:11, RS:61, ARC:43 | | | |
| R19.11 | RS:79 | | | |
| AP1 | AR:5, :7, :9 | | | |
| AP2 | AR:5, :7 | | | |
| AP3 | AR:5, :9 | | | |
| AP4 | AR:9 | | | |
| AP5 | AR:7, :9 | | | |
| AP6 | AR:5 | | | |
| AP7 | AR:5 | | | |
| AP8 | AR:7 | | | |
| AP9 | AR:7 | | | |
| AP10 | AR:7 | | | |
| AP11 | RS:53 (R28) | | | |
| AP12 | AR:7 | | | |
| AP13 | RS:31 | | | |
| R21.1 | AR:15 | | | |
| R21.2 | CR:20 | | | |
| R21.3 | CR:20 | | | |
| R21.4 | AR:18 | | | |
| R21.5 | AR:16 | | | |
| R21.6 | RS:74 | | | |
| R21.7 | RS:70 | | | |
| R22.1 | RS:63 | | | |
| R22.2 | RS:63 | | | |
| R22.3 | RS:63 | | | |
| R22.4 | RS:63 | | | |
| R22.5 | RS:63 | | | |
| R22.6 | RS:63 | | | |
| R22.7 | RS:62 | | | |
| R22.8 | CR:12, OV:12, PR:22 | | | |
| R22.9 | CR:5 | | | |
| R23.1 | RS:32 | | | |
| R23.2 | RS:31 | | | |
| R23.3 | CR:5 → RS | | | |
| R23.4 | RS:32 | | | |
| R23.5 | RS:33 | | | |
| R23.6 | SK:58 | | | |
| R23.7 | copies → RS | | | |
| R24.1 | RS:35 | | | |
| R24.2 | RS:35 | | | |
| R24.3 | RS:35 | | | |
| R24.4 | RS:35 | | | |
| R24.5 | RS:35 (unchanged) | | | |
| R24.6 | AR:7 | | | |
| R24.7 | CR:18 | | | |
| R25 | RS:76–79 | | | |
| R26 | RS:68 | | | |
| R27 | PR:7 (+ RS:83 clause) | | | |
| R28 | RS:53 | | | |
| R29 | PR:7 | | | |
| R30 | PR:21 | | | |
| R31 | each procedure; RS:34 | | | |
| A1 | (new; section 5 places) | | | |
| D1 | RS:51 | | | |
| D2 | RS:9, PR:5, CR:5, OV:5, PV:7 | | | |
| D3 | AR:12, AR:16 | | | |
| D4 | AR:13 | | | |
| D7 | RS:20 | | | |
| D8 | PV:30 | | | |
| D9 | RS:14 | | | |
| H1–H6 | SK:44, RS:51, CR:8, OV:8, AR:10 | | | |
| H7 | PR:11 | | | |
| H8 | RS:43 | | | |
| H9 | RS:54 (unchanged) | | | |
| H10 | RS:61 | | | |
| H11 | RS:61 (unchanged) | | | |
| H12 | RS:70 | | | |
| H13 | RS:75 | | | |
| U1–U22 | section 2b (unchanged) | | | |

---

## 8. Decisions applied and open items

**Applied:**
- O1–O8 as main decided.
- D5 and D6 withdrawn.
- D2 limited to five sentences.
- D3 reworded.
- D8 by mode.
- D9 added.
- H7 replaced.
- H9 and H11 kept under S4.
- K1's pointer requirement.

**Settled by main:**
- A1 placement for gate operations: the delegation skill's Accept or recover section states the read once for all of them, and its Plan review section for the final check (spec item 4).
- D and H items whose target copy item 1 removes are satisfied by the removal, provided the owner's text carries the replacement (spec T1).
- Plan review call 1: R7.5's SK:54 stays as the retry limit; R7.6 keeps each copy's predicate, with AR:5 and PR:26 unchanged; R21.3 stays in code review; loading notes for R4.2 and R27; owners other than review state are R4 and R9 (plan review, loaded for every review through mode resolution), R21 (Adversarial review and code review, each loaded where it applies), R19 (the delegation skill) and R8.11–R8.16 (the Stop threshold procedure); R8.9 moves to review state, which item 4's read covers.

- Plan review calls 2 and 3: R21.3's section 7 row is CR:20; a loading line under each rule owned outside review state, and the default loading route at the head of section 1; AP11 is owned by RS:53 (R28); PV:30 and PV:43 stay as preview's own summaries; R18.10 is owned by each procedure for its own step (call 4 non-blocking).

- After call 4: the Codex second opinion's C1–C5 (pointer qualifier, S-5, S-2, quoted conditions, T2 pass rule) and call 5's revisions (K1's qualifier source, S-5's INCONCLUSIVE causes, S-2's shared value read by none of C1's files, R14.5's and R16.3's restored qualifiers).

**Not determined:** I did not read the test suite or the handoff records, so I cannot say which existing pins a given restatement affects.
