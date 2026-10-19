"""Completion criteria ticket 01 (docs/specs/completion-criteria.md, Acceptance items 1, 2, 3 and 7 and the parts of
items 8 and 9 for these rules, Security invariants S1, S2 and S3): a Claim's reviews judge it against its acceptance as
written, unbroken existing behaviour, no security problem or data loss and no Deviation; every other finding is a
Non-blocking finding recorded in the work's Follow-up record; security findings, BROKEN and Adversarial review are
unchanged.

Completion criteria ticket 02 (Acceptance items 4 and 5 and the parts of items 7, 8 and 9 for these rules, Security
invariants S7 and S8): reviews are serial within a working tree, and main runs a final check of the Plan's overall
acceptance at the commit to be landed or tagged.

Completion criteria ticket 03 (Acceptance items 6 and 7 and the parts of items 8 and 9 for these rules, Security
invariants S3, S4, S5 and S8): one Accept and land decision may name several Claims, main asks for it once at the end of
the Plan, or earlier only for the whole branch, and builds its list from the review results it received in this
session."""

from __future__ import annotations

import hashlib
import subprocess
import unittest

from tests import feather_support
from tests.feather_support import config


class CompletionCriteriaTests(unittest.TestCase):
    """Whole-sentence pins of the new statements, absence pins of the old blocking criteria, and a check that every new
    pin fails on the text at tag v0.23.0."""

    ADR_0013 = "0013-only-what-a-claims-acceptance-needs-holds-its-completion.md"
    ADR_0006 = "0006-review-state-validity-and-completion.md"
    ADR_0008 = "0008-repository-authority-acceptance-and-gate-lifetime.md"
    # The repository path behind each place, for reading the same place at the tag.
    PATHS = {
        "review-state.md": "skills/delegation/references/review-state.md",
        "plan-review.md": "skills/delegation/references/plan-review.md",
        "code-review.md": "skills/delegation/references/code-review.md",
        "outcome-verification.md": "skills/delegation/references/outcome-verification.md",
        "reviewer.md": "templates/agents/reviewer.md",
        "CONTEXT.md": "CONTEXT.md",
        "README.md": "README.md",
        "README.zh-TW.md": "README.zh-TW.md",
        "reference.md": "docs/reference.md",
        "reference.zh-TW.md": "docs/reference.zh-TW.md",
        "ADR 0013": f"docs/adr/{ADR_0013}",
        "ADR 0006": f"docs/adr/{ADR_0006}",
        "ADR 0008": f"docs/adr/{ADR_0008}",
        "adversarial-review.md": "skills/delegation/references/adversarial-review.md",
        "SKILL.md": "skills/delegation/SKILL.md",
    }
    # The reference was split out of the README after the revisions these tests read, so at them the text behind a
    # reference place is the README's.
    SPLIT_FROM = {"reference.md": "README.md", "reference.zh-TW.md": "README.zh-TW.md"}
    ADR_0013_SERIAL = "\n## Serial reviews and the final check\n"
    ADR_0013_ACCEPT = "\n## A single Accept and land decision\n"
    TAG = "v0.23.0"
    # The reference's read-only Git prefix (repository safety's Safe Git invocation).
    GIT_READ = ("git", "--no-pager", "--no-optional-locks", "-c", "core.fsmonitor=", "-c", "core.quotePath=true",
                "-c", "log.showSignature=false", "-c", "mailmap.file=", "-c", "mailmap.blob=",
                "-c", "blame.ignoreRevsFile=", "-c", "diff.orderFile=/dev/null", "-c", "submodule.recurse=false")

    @classmethod
    def source(cls, name: str) -> str:
        """'<file>', '<procedure>#<step number>', 'review-state.md#<bullet label>', 'CONTEXT.md#<term>',
            '<reference>#<rule label>', 'ADR 0013', 'ADR 0013#options', 'ADR 0013#serial' (the part on the serial rule
            and the final check), 'ADR 0013#accept' (the part on the single Accept and land decision), 'ADR 0006',
            'ADR 0008', 'adversarial-review.md' or 'SKILL.md#Dispatch' (the delegation skill's Dispatch section)."""
        path, _, part = name.partition("#")
        if path.startswith("ADR "):
            text = (config.ROOT / cls.PATHS[path]).read_text(encoding="utf-8")
            if part == "options":
                return text.split("\n## Considered Options\n", 1)[1].split("\n## ", 1)[0]
            if part == "serial":
                return text.split(cls.ADR_0013_SERIAL, 1)[1].split("\n## ", 1)[0]
            if part == "accept":
                return text.split(cls.ADR_0013_ACCEPT, 1)[1].split("\n## ", 1)[0]
            return text
        if path == "SKILL.md":
            text = (config.ROOT / cls.PATHS[path]).read_text(encoding="utf-8")
            return text.split(f"\n## {part}\n", 1)[1].split("\n## ", 1)[0]
        if part.isdigit() or path == "adversarial-review.md":
            return feather_support.post_fix_source(name)
        return feather_support.review_rules_source(name)

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    assert_pinned = feather_support.stop_threshold_assert_pinned

    # Acceptance item 1: the completion conditions, the evidence rule, the Deviation rule and the Non-blocking findings,
    # in review state.
    REVIEW_STATE = {
        "review-state.md#Completion conditions": (
            "A claim's reviews judge it against these conditions: its acceptance as written is met; existing behaviour is "
            "not broken, shown by a failing test or a reproduction; it introduces no security problem and no data loss, "
            "as Security findings below describes; and it has no deviation from the plan.",
            "A Blocking finding is a finding that shows one of these conditions unmet; every other finding is a "
            "Non-blocking finding.",
            "The criteria apply in both review modes and to every user; there is no setting that changes them.",
            # Retained passes ticket 04 (Acceptance item 16): the statement that BROKEN is unchanged now defers to the procedure.
            "Plan review checks a plan before these reviews, and Adversarial review and its BROKEN follow the "
            "[adversarial review](adversarial-review.md) procedure.",
        ),
        "review-state.md#Evidence for a regression": (
            "A regression that is only inferred and is neither a security problem nor data loss does not block: such a "
            "regression blocks only when a failing test or a reproduction shows it.",
        ),
        "review-state.md#Deviations": (
            "A finding that shows a deviation from the plan is a Blocking finding, and a Deviation still stops main to ask "
            "the user: a material deviation stops dependent work for another review of the revised plan and the user's "
            "approval, as [plan review](plan-review.md) step 5 describes.",
        ),
        "review-state.md#Non-blocking findings": (
            "Every other finding is a Non-blocking finding, including an issue that predates the change, a correctness "
            "problem outside what the acceptance states, a regression that is only inferred and is neither a security "
            "problem nor data loss, and style, naming or a refactoring suggestion.",
            "It does not hold completion and is recorded in the work's Follow-up record.",
        ),
    }

    # Acceptance item 1: plan review and the code review and outcome verification procedures state the criteria.
    PROCEDURES = {
        "plan-review.md": (
            # Retained passes ticket 01 (Acceptance item 18): per-Claim timing replaces "Once a plan is implemented, each
            # claim's reviews judge it".
            "Once a claim is implemented, its reviews judge it against the completion criteria [review "
            "state](review-state.md) states: its acceptance as written is met; existing behaviour is not broken, shown by "
            "a failing test or a reproduction judged against the claim's base revision; it introduces no security problem "
            "and no data loss; and it has no deviation from the plan.",
            "A regression that is only inferred and is neither a security problem nor data loss does not block, every "
            "other finding is a Non-blocking finding and is recorded in the work's Follow-up record, and a Deviation still "
            "stops main to ask the user.",
            "The criteria apply in both review modes and to every user; there is no setting.",
        ),
        "plan-review.md#4": (
            "Style preferences and optional improvements are non-blocking, and main records them in the work's Follow-up "
            "record, as [review state](review-state.md)'s Follow-up record describes.",
        ),
        "code-review.md": (
            "In both review modes, code review judges the claim against the completion criteria [review "
            "state](review-state.md) states: its acceptance as written is met; existing behaviour is not broken, shown by "
            "a failing test or a reproduction judged against the claim's base revision; it introduces no security problem "
            "and no data loss; and it has no deviation from the plan.",
            "A regression that is only inferred and is neither a security problem nor data loss does not block, every "
            "other finding is a Non-blocking finding and is recorded, and a Deviation still stops main to ask the user, "
            "as [review state](review-state.md)'s Completion criteria describes.",
        ),
        "code-review.md#4": (
            "A finding given as blocking that shows none of the completion conditions unmet, such as a regression that is "
            "only inferred and is neither a security problem nor data loss, is rejected with that evidence and recorded "
            "as a Non-blocking finding; a security problem or data loss the change introduced or made exploitable is never "
            "rejected for lacking a failing test or a reproduction, as [review state](review-state.md)'s Security findings "
            "describes.",
        ),
        "outcome-verification.md": (
            "In both review modes, outcome verification judges the claim against the completion criteria [review "
            "state](review-state.md) states: its acceptance as written is met; existing behaviour is not broken, shown by "
            "a failing test or a reproduction judged against the claim's base revision; it introduces no security problem "
            "and no data loss; and it has no deviation from the plan.",
            "A regression that is only inferred and is neither a security problem nor data loss does not block, every "
            "other finding is a Non-blocking finding and is recorded, and a Deviation still stops main to ask the user, "
            "as [review state](review-state.md)'s Completion criteria describes.",
        ),
        "outcome-verification.md#4": (
            "A finding that shows none of the completion conditions unmet, such as a failure outside what the acceptance "
            "states that also occurs at the claim's base revision, is rejected with that evidence and recorded as a "
            "Non-blocking finding; a security problem or data loss the change introduced or made exploitable is never "
            "rejected for lacking a failing test or a reproduction, as [review state](review-state.md)'s Security findings "
            "describes.",
        ),
    }

    # S1: security findings and data loss still block on the reviewer's evidence; BROKEN, Adversarial review and the
    # tracker rule for a pre-existing vulnerability are unchanged.
    S1 = {
        "review-state.md#Security findings": (
            "A security problem the change introduced or made exploitable, through a new route, permission or data flow "
            "even when the vulnerable code is outside the diff, and data loss the change introduced, are Blocking findings "
            "whatever the acceptance states.",
            "They block on the reviewer's evidence as before: the rule that a regression needs a failing test or a "
            "reproduction applies only to regressions that are neither security problems nor data loss, so a removed or "
            "weakened security control is a Blocking finding without a reproduction.",
            # Retained passes ticket 04 (Acceptance item 16): the statement that BROKEN is unchanged now defers to the procedure.
            "The adversary's BROKEN is handled as the [adversarial review](adversarial-review.md) procedure describes, "
            "and a pre-existing vulnerability still becomes separate work in the project's tracker, as its step 10 describes.",
        ),
        "code-review.md#5": (
            "A pre-existing vulnerability also becomes separate work in the project's tracker, as [Adversarial "
            "review](adversarial-review.md) step 10 describes.",
        ),
        "CONTEXT.md#Blocking finding": (
            "A security problem the change introduced or made exploitable, even outside the diff, and data loss it "
            "introduced block whatever the acceptance states and without a reproduction, so a removed or weakened "
            "security control blocks; a regression that is only inferred and is neither a security problem nor data loss "
            "does not block.",
        ),
    }

    # S1 after the first Adversarial round: a verifier's note main judges to be, or cannot rule out as, a security
    # problem or data loss withholds that call's CONFIRMED until the note is dispositioned, and "made exploitable" holds
    # where a security finding is never rejected for lacking a reproduction (code review and outcome verification step 4,
    # pinned in PROCEDURES).
    S1_VERIFIER_NOTE = {
        "review-state.md#Security findings": (
            "A verifier's note that main judges to be, or cannot rule out as, a security problem or data loss the change "
            "introduced or made exploitable is a Blocking finding, and that call's CONFIRMED is not used as a pass, the "
            "call counting as a call without a pass, until main dispositions the note as FIX or REJECT with evidence under "
            "[outcome verification](outcome-verification.md)'s rule for a REFUTED.",
        ),
        "outcome-verification.md#3": (
            "A CONFIRMED that is not used as a pass, as step 7 describes or after main's comparison as [review "
            "state](review-state.md)'s Serial within a working tree describes, counts as a call without a pass and does "
            "not reset the count.",
        ),
        "outcome-verification.md#6": (
            "A CONFIRMED that is not used as a pass, as step 3 describes, continues neither to completion nor to "
            "Adversarial review.",
        ),
        "outcome-verification.md#7": (
            "Non-blocking findings do not hold completion.",
            "A verifier's optional note is a Non-blocking finding unless main judges it to be, or cannot rule out as, a "
            "security problem or data loss the change introduced or made exploitable: such a note is a Blocking finding, "
            "and that call's CONFIRMED is not used as a pass, the call counting as a call without a pass, until main "
            "dispositions the note as FIX or REJECT with evidence under step 4's rule for a REFUTED.",
        ),
        "ADR 0013": (
            "A verifier's note that main judges to be, or cannot rule out as, a security problem or data loss the change "
            "introduced or made exploitable is a Blocking finding, and that call's CONFIRMED is not used as a pass, the "
            "call counting as a call without a pass, until the note is dispositioned as FIX or REJECT with evidence under "
            "outcome verification's rule for a REFUTED; the verifier's definition is unchanged, since main makes this "
            "call.",
            "ADR 0006's state model, validity rules and Acceptance gate are unchanged, apart from the verifier's note "
            "above, the call whose pass is not used and the final check, which the next part records.",
        ),
        "ADR 0006": (
            "A security problem or data loss the change introduced still blocks whatever the acceptance states, and the "
            "state model, validity rules and Acceptance gate are unchanged, apart from what ADR 0013 adds: a verifier's "
            "note that withholds a CONFIRMED, a call whose pass is not used after main's comparison, and the final check "
            "before landing and release.)",
        ),
    }

    # S2 after the first Adversarial round: every brief of a Claim's reviews, a narrowed follow-up's included, names the
    # Claim's base revision, which main establishes from Git in this session, and the reviewer judges against it.
    S2_BRIEFS = {
        "review-state.md#Evidence for a regression": (
            "Every brief of the claim's code review, outcome verification and Adversarial review, a narrowed follow-up's "
            "included, names the claim's base revision, which main establishes itself from Git in this session.",
        ),
        "code-review.md#2": (
            "Every brief of the claim's code review, a narrowed follow-up's included, names the claim's base revision, "
            "which main establishes itself from Git in this session, as [review state](review-state.md)'s Evidence for a "
            "regression describes.",
        ),
        "code-review.md#4": (
            "Send the next review the prior findings with each disposition and its closure or rejection evidence, the "
            "claim's base revision as step 2 describes, and, for a claim the acceptance gate covers, the range from the "
            "previously judged commit to the new one; when the previous call did not complete, supply instead the full "
            "range from the claim's base revision with earlier and partial findings as evidence.",
        ),
        "outcome-verification.md#2": (
            "Every brief of the claim's outcome verification, a recheck's included, names the claim's base revision, "
            "which main establishes itself from Git in this session, as [review state](review-state.md)'s Evidence for a "
            "regression describes.",
        ),
        "adversarial-review.md#2": (
            "Every brief of the claim's Adversarial review, a narrowed follow-up's included, names the claim's base "
            "revision, which main establishes itself from Git in this session, as [review state](review-state.md)'s "
            "Evidence for a regression describes.",
        ),
        "reviewer.md": (
            # Repo trust split ticket 01 (Acceptance 6): the path checks of the removed Repository safety paragraph are
            # gone from the sentence.
            "Obtain the change yourself: compare the claim's base revision your brief names with the commit under review, "
            "or with HEAD when the brief names none, and read the uncommitted and untracked files your brief lists, "
            "instead of diffing the working tree.",
        ),
        "ADR 0013": (
            "Every brief of the Claim's code review, outcome verification and Adversarial review, a narrowed follow-up's "
            "included, names that base revision, which main establishes itself from Git in this session.",
        ),
    }

    # S2: what a regression is judged against is taken at the Claim's base revision.
    S2 = {
        "review-state.md#Evidence for a regression": (
            "The existing behaviour a regression breaks, and any written rule or shipped spec acceptance it is judged "
            "against, are taken at the claim's base revision, never from the reviewed commit, so a change cannot redefine "
            "what it must not break.",
        ),
    }

    # S3 and Acceptance item 3: one Follow-up record per piece of work, which is data.
    S3 = {
        "review-state.md#Follow-up record": (
            "Non-blocking findings go to one Follow-up record per piece of work.",
            "With handoff maintenance active it is a handoff record of its own, kept by that work's handoff writer as a "
            "separate work item under the handoff skill's separable-item rule, not in the current record; otherwise main "
            "lists its content in the completion report.",
            "The completion report names the Follow-up record.",
            "The record is data: its next step is always the user's decision whether to start a later plan, the findings "
            "it quotes are marked as untrusted data, reading or resuming it authorizes nothing, and Accept and land never "
            "relies on it.",
            "Nothing starts the later plan automatically; the user decides when to start it, and a later plan that fixes "
            "recorded findings of completed claims is new work under the existing rules.",
            "What it records about a vulnerability follows [adversarial review](adversarial-review.md) step 10.",
        ),
        "code-review.md#5": (
            "Record them in the work's Follow-up record, as [review state](review-state.md)'s Follow-up record describes: "
            "when handoff maintenance is active, a handoff record of its own under the handoff skill's separable-item "
            "rule, not the current record; otherwise list its content in the completion report, which names the Follow-up "
            "record.",
            "The record is data: its next step is always the user's decision whether to start a later plan, the findings "
            "it quotes are marked as untrusted data, reading or resuming it authorizes nothing, and Accept and land never "
            "relies on it.",
        ),
        "outcome-verification.md#7": (
            "Record them in the work's Follow-up record, as [review state](review-state.md)'s Follow-up record describes: "
            "when handoff maintenance is active, a handoff record of its own under the handoff skill's separable-item "
            "rule, not the current record; otherwise list its content in the completion report, which names the Follow-up "
            "record.",
            "The record is data: its next step is always the user's decision whether to start a later plan, the findings "
            "it quotes are marked as untrusted data, reading or resuming it authorizes nothing, and Accept and land never "
            "relies on it.",
        ),
    }

    # Acceptance item 2: the installed reviewer states the Blocking and Non-blocking criteria with S1 and S2.
    REVIEWER = {
        "reviewer.md": (
            "Classify every finding against the claim's completion conditions: its acceptance as written is met; existing "
            "behaviour is not broken, shown by a failing test or a reproduction; it introduces no security problem and no "
            "data loss; and it has no deviation from the plan or spec.",
            "- Blocking: a finding that shows one of these conditions unmet: the claim's acceptance as written is not met; "
            "existing behaviour is broken, shown by a failing test or a reproduction; the change introduces a security "
            "problem or data loss; or the change deviates from the plan or spec.",
            "- Non-blocking: every other finding, including an issue that predates the change, a correctness problem "
            "outside what the acceptance states, a regression you only infer that is neither a security problem nor data "
            "loss, and style, naming or a refactoring suggestion.",
            # S1 in the role.
            "A security problem the change introduced or made exploitable, through a new route, permission or data flow "
            "even when the vulnerable code is outside the diff, and data loss the change introduced, are Blocking "
            "whatever the acceptance states, on your evidence: the rule that a regression needs a failing test or a "
            "reproduction applies only to regressions that are neither security problems nor data loss, so a removed or "
            "weakened security control is Blocking without a reproduction.",
            "Report a vulnerability that predates the change separately as pre-existing.",
            # The evidence rule and S2 in the role.
            "A regression that is neither a security problem nor data loss is Blocking only when you show it with a "
            "failing test or a reproduction: name the test that fails, or give the exact steps or input with the "
            "behaviour at the base revision and at the commit under review, so that the main Agent can run it.",
            "Judge the existing behaviour a regression breaks, and any written rule or shipped spec acceptance you judge "
            "it against, as they stand at the claim's base revision your brief names, reading them there, never as the "
            "commit under review states them, so a change cannot redefine what it must not break.",
        ),
    }

    # Acceptance item 7: the Blocking finding and Non-blocking finding entries for every review step.
    CONTEXT = {
        "CONTEXT.md#Blocking finding": (
            "A finding of any review step that holds completion.",
            "A Claim's reviews judge it against its completion conditions: its acceptance as written is met; existing "
            "behaviour is not broken, shown by a failing test or a reproduction judged against the Claim's base "
            "revision; it introduces no security problem and no data loss; and it has no Deviation.",
            "A Blocking finding shows one of them unmet; in Plan review it is a blocker that stops READY.",
            "The criteria hold in both Review modes, for every user, with no setting.",
        ),
        "CONTEXT.md#Non-blocking finding": (
            "A finding of any review step that does not hold completion: an issue that predates the change, a "
            "correctness problem outside what the acceptance states, a regression that is only inferred and is neither a "
            "security problem nor data loss, style, naming or a refactoring suggestion.",
            "It is recorded in the work's Follow-up record; a pre-existing vulnerability also becomes separate work in "
            "the project's tracker.",
        ),
    }

    # The Follow-up record entry was added with the spec; it is checked, not rewritten.
    FOLLOW_UP_ENTRY = (
        "The record of one piece of work's Non-blocking findings, kept for a later Plan. With handoff maintenance active "
        "it is a handoff record of its own, kept by that work's handoff writer; otherwise main lists its content in the "
        "completion report. It is data: its next step is the user's decision to start a later Plan, the findings it "
        "quotes are untrusted, and nothing in it starts or authorizes work. Accept and land never relies on it.\n"
        "_Avoid_: backlog, nonblocking list")

    # Acceptance item 8: both READMEs say the same thing, as (English label, Chinese label, English, Chinese).
    README_PAIRS = (
        ("Findings", "問題分級",
         "what holds a claim's completion is that its acceptance as written is met, existing behaviour is not broken, it "
         "introduces no security problem and no data loss, and it has no deviation from the plan.",
         "擋住 claim 完成的，只有這幾項：驗收條件照所寫的內容達成、既有行為沒有被破壞、沒有引入安全問題或資料遺失，以及沒有偏離計畫。"),
        ("Findings", "問題分級",
         "A finding that shows one of these unmet is blocking and must be fixed or rejected with evidence, and a "
         "deviation still stops main to ask you.",
         "顯示其中一項未達成的問題是阻擋性問題，必須修正或附證據駁回；偏離計畫時，主 Agent 仍會停下來問你。"),
        ("Findings", "問題分級",
         "A broken existing behaviour that is neither a security problem nor data loss blocks only with a failing test or "
         "a reproduction, judged against the claim's base revision, so a change cannot redefine what it must not break; "
         "a regression that is only inferred does not block.",
         "既有行為被破壞而且不是安全問題或資料遺失時，要有失敗的測試或重現步驟，並以 claim 的基準版本判斷，才會擋下，所以變更無法重新定義它不能破壞的東西；只是推測的 regression 不會擋下。"),
        # Retained passes ticket 04 (Acceptance items 16 and 17): "BROKEN and Adversarial review are unchanged" now defers to the
        # procedure.
        ("Findings", "問題分級",
         "Security findings still block as before: a security problem the change introduced or made exploitable, even "
         "through code outside the diff, and data loss it introduced block whatever the acceptance says and need no "
         "reproduction, so a removed or weakened security control blocks; BROKEN and Adversarial review follow the "
         "adversarial-review procedure, "
         "and a vulnerability that predates the change becomes separate work in your tracker.",
         "安全問題照舊擋下：這次變更引入或使其可被利用的安全問題（即使經由 diff 以外的程式碼），以及它引入的資料遺失，不論驗收條件怎麼寫都會擋下，也不需要重現，所以移除或削弱安全控制也會擋下；BROKEN 與對抗式審查依對抗式審查程序處理，變更之前就存在的漏洞則成為 tracker 中另外的工作。"),
        ("Findings", "問題分級",
         "A verifier's note that main judges to be, or cannot rule out as, such a security problem or data loss blocks "
         "too: that verification's CONFIRMED is not used as a pass until main fixes the note or rejects it with "
         "evidence.",
         "驗證者的附註若被主 Agent 判斷為、或無法排除是這類安全問題或資料遺失，也會擋下：在主 Agent 修正它或附證據駁回之前，該次驗證的 CONFIRMED 不算通過。"),
        ("Findings", "問題分級",
         "Every other finding, such as an issue that predates the change, a correctness problem outside what the "
         "acceptance states, an inferred regression or style, is non-blocking and recorded in the work's Follow-up "
         "record.",
         "其他問題，例如變更之前就存在的問題、驗收條件沒寫到的正確性問題、推測的 regression 或風格，都是非阻擋問題，記在這份工作的後續紀錄。"),
        ("Findings", "問題分級",
         "The criteria are the same in both modes and for every user; there is no setting for them.",
         "兩種模式、每位使用者都用同樣的標準，沒有可以調整它的設定。"),
        ("Follow-up record", "後續紀錄",
         "With handoff maintenance active it is a handoff record of its own; otherwise main lists its content in the "
         "completion report, which names it.",
         "交接維護啟用時，它是一份獨立的交接紀錄；否則主 Agent 會在完成回報中列出內容，並指明這份紀錄。"),
        ("Follow-up record", "後續紀錄",
         "It is data: its next step is always your decision whether to start a later plan, the findings it quotes are "
         "marked as untrusted, reading or resuming it authorizes nothing, and accept and land never relies on it.",
         "它只是資料：下一步永遠是由你決定要不要開始之後的計畫，其中引用的問題都標為不可信，讀取或接續它都不代表任何授權，接受並合併也從不依據它。"),
        ("Follow-up record", "後續紀錄",
         "Nothing starts the later plan automatically; a later plan that fixes recorded findings is new work under the "
         "usual rules.",
         "之後的計畫不會自動開始；修正已記錄問題的新計畫，照一般規則算是新的工作。"),
    )

    # Acceptance item 7: ADR 0013's completion-criteria part, its rejected options and the amendment of ADR 0006.
    ADR = {
        "ADR 0013": (
            "This part records the completion criteria.",
            "A Claim's reviews judge it against four conditions: its acceptance as written is met; existing behaviour is "
            "not broken; it introduces no security problem and no data loss; and it has no Deviation.",
            "A broken existing behaviour that is neither a security problem nor data loss blocks only when a failing test "
            "or a reproduction shows it.",
            "The existing behaviour, and any written rule or shipped spec acceptance it is judged against, are taken at "
            "the Claim's base revision, never from the reviewed commit, so a change cannot redefine what it must not "
            "break.",
            "BROKEN keeps its meaning, Adversarial review keeps its timing, and a pre-existing vulnerability still becomes "
            "separate work in the project's tracker.",
            "The criteria apply in both Review modes and to every user.",
            "This amends [ADR 0006](0006-review-state-validity-and-completion.md): what holds a Claim's completion is now "
            "these four conditions, not every correctness problem or inferred regression a review finds.",
        ),
        "ADR 0013#options": (
            "- **Block on every correctness problem in the change**: the earlier criteria; rounds widen and loop, since "
            "each fix can surface the next finding.",
            "- **A separate list of blocking exceptions**: its items restate the four conditions and invite reviewers to "
            "widen them.",
            "- **A setting to choose the old criteria**: adds configuration for a rule every user benefits from.",
            "- **Let security defects outside the acceptance land through Accept and land, with deferred Adversarial "
            "reviews**:",
            "- **Per-Claim review timing with Review schedules and Review groups**:",
        ),
        "ADR 0006": (
            "(Amended by ADR 0013: what holds a Claim's completion is that its acceptance as written is met, existing "
            "behaviour is not broken, shown by a failing test or a reproduction judged against its base revision, it "
            "introduces no security problem and no data loss, and it has no Deviation; every other finding is a "
            "Non-blocking finding recorded in the work's Follow-up record.",
        ),
    }

    # Replaced statements of the old blocking criteria: absent now, present at v0.23.0.
    OLD_CRITERIA = {
        "reviewer.md": (
            "- Blocking: a correctness bug, security problem, data loss, regression or deviation from the plan or spec "
            "introduced by this change.",
            "- Non-blocking: style, naming, a refactoring suggestion or an issue that predates the change.",
        ),
        "CONTEXT.md#Blocking finding": (
            "A Code review finding that holds completion: a correctness bug, security problem, data loss, regression or "
            "deviation from the Plan.",
        ),
        "CONTEXT.md#Non-blocking finding": (
            "A Code review finding that does not hold completion: style, naming, a refactoring suggestion or an issue that "
            "predates the change.",
            "It is recorded as follow-up work.",
        ),
        "code-review.md#5": ("List them in the final report.",),
        "reference.md#Findings": (
            "blocking ones (correctness, security, data loss, regression, deviation from the plan)",
            "Non-blocking ones are listed in the final report, or become separate follow-up work when a handoff is active.",
        ),
        "reference.zh-TW.md#問題分級": (
            "阻擋性問題（正確性、安全、資料遺失、regression、偏離計畫）",
            "非阻擋問題列在最終回報，有進行中的交接時另建獨立的後續工作。",
        ),
    }

    # Acceptance item 2: 0.24.0's completion criteria changed neither the installed verifier nor the adversary
    # definition. Each digest is the SHA-256 of the LF text with the shared Repository safety paragraph line removed, at
    # v0.23.0 and at v0.24.0 alike. Repo trust split ticket 01 (0.29.0) replaces that paragraph and changes both
    # templates, so the digests are compared at the two tags this record was written for, not at the current templates.
    UNCHANGED_ROLES = {
        "adversary": "ef555aa958fa8074d66eff4b821b92171b313bd53d5b3c8b1fd7bc2db3c0a12d",
        "verifier": "54b5f52cca68043c6829053859fd5aa376ee7ea050912334d2b2947260a93e10",
    }
    REPOSITORY_SAFETY_LINE = "**Repository safety.** "
    UNCHANGED_BETWEEN = ("v0.23.0", "v0.24.0")

    # Ticket 02, Acceptance item 4: the serial rule, the handoff records it includes, no review worktrees, the worktree
    # exception and shared test resources, in review state and in the delegation skill's rule on parallel work.
    SERIAL = {
        "review-state.md#Serial within a working tree": (
            "Within one working tree, reviews and implementation are serial.",
            "While a code review, outcome verification or Adversarial review call runs, main does not change the working "
            "tree it judges, and nothing main started writes to it; implementation in that working tree waits until the "
            "call ends.",
            "This includes main's own handoff records inside the project, which main updates only between calls.",
            "Main does not create a worktree for a review on its own.",
            "Work the user runs in separate worktrees may proceed in parallel, each worktree its own workspace and serial "
            "in itself.",
            "Shared test resources stay governed by each brief's target start and reset.",
        ),
        "SKILL.md#Dispatch": (
            "Reviews are serial within a working tree, as [review state](references/review-state.md)'s Serial within a "
            "working tree describes.",
            "While a code review, outcome verification or Adversarial review call runs, main does not change the working "
            "tree it judges, its own handoff records inside the project included, which it updates only between calls, "
            "and implementation in that working tree waits until the call ends.",
            "Main does not create a worktree for a review on its own.",
            # Repo trust split ticket 01 (Acceptance 1 and 3): each worktree gets the workspace reads.
            "Work the user runs in separate worktrees may proceed in parallel, each worktree serial in itself and still "
            "checked as [review state](references/review-state.md)'s What a gated pass judged describes.",
            "Shared test resources stay governed by each brief's target start and reset.",
        ),
    }

    # S7: nothing main started writes the tree a review judges, one gated call that executes code per tree, a changed
    # dependency voids the pass, and the worktree exception extends no trust.
    S7 = {
        "review-state.md#Serial within a working tree": (
            "Before dispatching a code review, outcome verification or Adversarial review call, main confirms that no "
            "Assignment or background process it started that may write the working tree is still running.",
            "At most one gated call that executes code runs in a working tree at a time.",
            # Repo trust split ticket 01 (Acceptance 1 and 3): the comparison uses the workspace reads, which each
            # worktree gets.
            "When main's comparison of the workspace after a call, with the reads What a gated pass judged states, finds "
            "a change to a file the claim depends on, its own files and what its acceptance checks depend on included, "
            "that call's pass is not used.",
            "Each worktree still gets the reads and comparisons What a gated pass judged states.",
            # After the first Adversarial round: a call whose pass is not used.
            "Such a call counts as a call without a pass, establishes no coverage and resets no count, and the next call "
            "for the claim reviews its full scope from its base revision, as Completed calls and coverage describes.",
        ),
        "review-state.md#Completed calls and coverage": (
            "The exception is a call whose pass main does not use after its comparison of the workspace, as Serial within "
            "a working tree describes: it counts as a call without a pass, establishes no coverage and resets no count, "
            "and the next call for the claim reviews its full scope from its base revision.",
        ),
        "SKILL.md#Dispatch": (
            "Before dispatching such a call, main confirms that no Assignment or background process it started that may "
            "write the working tree is still running, and at most one gated call that executes code runs in a working "
            "tree at a time.",
        ),
    }

    # S7 in the code review and Adversarial review procedures (code review call 2 of ticket 02): a call whose pass is
    # not used after main's comparison counts as a call without a pass, resets no count, does not continue to the next
    # step, and the next call is not narrowed but covers the claim's full scope from its base revision.
    S7_PROCEDURES = {
        "code-review.md#2": (
            "When main's comparison of the workspace after the previous call found a change to a file the claim depends "
            "on, so that call's pass is not used, as [review state](review-state.md)'s Serial within a working tree "
            "describes, the brief does not say that call completed with a verdict and supplies the claim's full scope "
            "from its base revision.",
        ),
        "code-review.md#3": (
            "An APPROVED that is not used as a pass, after main's comparison as [review state](review-state.md)'s Serial "
            "within a working tree describes, counts as a call without a pass and does not reset the count.",
        ),
        "code-review.md#4": (
            "When main's comparison after the previous call found a change to a file the claim depends on, as step 2 "
            "describes, the brief does not say that call completed with a verdict and supplies instead the full range "
            "from the claim's base revision with earlier findings as evidence.",
        ),
        "code-review.md#6": (
            "An APPROVED that is not used as a pass, as step 3 describes, whether automatic or explicit, does not "
            "continue to outcome verification and clears no stopped step.",
        ),
        # The paragraphs on the review of a fix.
        "code-review.md": (
            "An APPROVED that is not used as a pass, as step 3 describes, does not make it zero.",
            "When main's comparison after that call found a change to a file the claim depends on, as step 2 describes, "
            "the review of the fix is not narrowed: the brief does not say that call completed with a verdict, and the "
            "call reviews the claim's full scope from its base revision.",
        ),
        "adversarial-review.md#6": (
            "A HELD from a call whose pass main does not use after its comparison of the workspace, as [review "
            "state](review-state.md)'s Serial within a working tree describes, is not accepted: the call counts as a "
            "non-pass under step 4, establishes no coverage and resets no count, and the next call for the claim covers "
            "its full scope from its base revision.",
        ),
        # Code review call 3 of ticket 02: the recheck after REFUTED, the calls after BROKEN and INCONCLUSIVE, and the
        # continuation after HELD.
        "outcome-verification.md#4": (
            "When main's comparison after the previous call found a change to a file the claim depends on, as [review "
            "state](review-state.md)'s Serial within a working tree describes, the brief does not say that call completed "
            "with a verdict and the next call verifies the claim's full acceptance from its base revision, not only the "
            "original failure.",
        ),
        "adversarial-review.md#5": (
            "When main's comparison after the previous call found a change to a file the claim depends on, as [review "
            "state](review-state.md)'s Serial within a working tree describes, the call after BROKEN covers the claim's "
            "full scope from its base revision, not only the fix and the open gaps.",
            "After any INCONCLUSIVE, when main's comparison after the previous call found a change to a file the claim "
            "depends on, the next call, once the rule above lets it run, covers the claim's full scope from its base "
            "revision, not only the uncovered invariants and gaps.",
        ),
        "adversarial-review.md#8": (
            "With a HELD in the automatic flow that main accepts under step 6, continue to completion under the existing "
            "authority.",
            "A HELD that main does not accept under step 6, one whose pass is not used after main's comparison of the "
            "workspace included, whether automatic or explicit, does not continue to completion and clears no stopped "
            "step.",
        ),
    }

    # Ticket 02, Acceptance item 5: the final check, not counted and adding no verdict, a failure reopening Claims.
    FINAL_CHECK = {
        "review-state.md#Final check": (
            # Repo trust split ticket 01 (Acceptance 3 and 5): the Execution rules are review state's own bullet.
            "Before landing or release, main runs the plan's overall acceptance checks, such as the full test suite, at "
            "the commit to be landed or tagged, within the Execution rules above.",
            "It is main's own run, not a review step: it is not a counted step and adds no verdict.",
        ),
        "review-state.md#Not counted": (
            "The final check before landing or release, as Validity and completion's Final check describes, is not a "
            "counted step either.",
        ),
    }

    # S8 as amended after the first Adversarial round: the final check judges the landing commit, is a condition of
    # the landings and releases the Acceptance gate covers, and fails closed.
    S8 = {
        "review-state.md#Final check": (
            # Repo trust split ticket 01 (Acceptance 3): the workspace reads before and after the check, ignored files
            # outside them.
            "It runs only when the workspace equals the commit to be landed or tagged, established with the reads What a "
            "gated pass judged states; ignored files and files marked assume-unchanged or skip-worktree are outside "
            "those reads, so they can take part in it.",
            "It runs again whenever the commit to be landed changes, after a fix or any other commit.",
            "After it runs, main runs the same reads again and compares them with those before it: a change to a "
            "tracked file or a file the check depends on, or a read that counts as a change, makes that run a failed "
            "run, with the change as its output, while files the check writes elsewhere, such as its artefacts, do not.",
            "Landing and release that the acceptance gate covers wait until the final check passes at the commit to be "
            "landed; otherwise only an accept-and-land decision that states its actual state lets them proceed, as Accept "
            "and land at the end of the plan describes.",
            "When Execution does not allow it, it is recorded as not run, and main states that it has not run before "
            "landing and in any accept-and-land decision.",
            "Once it has failed at a commit, that commit's state is failed, and a later pass at the same commit lets "
            "landing proceed only through an accept-and-land decision that names the failure.",
            "Its state comes only from main's own run in this session at that commit, never passed from a record or an "
            "earlier session, and after a context compaction main runs it again.",
            "When main cannot establish from this session that the commit has not failed, it treats the commit as failed, "
            "and a decision states that state as \"failed (presumed: not established as unfailed in this session)\", with "
            "the reason and this session's outputs.",
            "A record can only make the state failed, never passed.",
            # Retained passes ticket 03 (Acceptance items 7 and 15): a failure reopens claims in off only; in auto it
            # is fixed by its claim or a fix claim, as tests/test_feather_retained_passes.py pins.
            "In off, the final check keeps its earlier rules, without the reruns, fix claims and stop above: a failure "
            "reopens the claims it affects under the existing rules, and its output goes with it to the reopened claims' "
            "reviews as evidence; landing and release wait for their passes again.",
            "In off, a failure that cannot be attributed with evidence reopens every claim the check covers.",
            "For a landing or release the acceptance gate does not cover, main runs the final check when Execution "
            "allows, reports its state before landing, and waits for the user's instruction given after that report.",
        ),
        "review-state.md#Commit and completion": (
            "Landing and release that the acceptance gate covers also wait for the final check, as Final check below "
            "describes.",
        ),
        "CONTEXT.md#Acceptance gate": (
            "Landing and release also wait for the final check at the commit to be landed, as review state's Final check "
            "states: until it passes there, only an Accept and land decision that states its actual state lets them "
            "proceed.",
        ),
    }

    # Ticket 02, Acceptance item 7: ADR 0013's part on the serial rule and the final check, with its rejected options.
    SERIAL_ADR = {
        "ADR 0013#serial": (
            "This part records the serial rule and the final check.",
            "While a code review, outcome verification or Adversarial review call runs, main does not change the working "
            "tree it judges, its own handoff records inside the project included, which it updates only between calls, "
            "and implementation in that working tree waits until the call ends.",
            "Before dispatching such a call, main confirms that no Assignment or background process it started that may "
            "write the working tree is still running, and at most one gated call that executes code runs in a working "
            "tree at a time.",
            "When main's comparison after a call finds a change to a file the Claim depends on, that call's pass is not "
            "used.",
            "Such a call counts as a call without a pass, establishes no coverage and resets no count, and the next call "
            "for the Claim reviews its full scope from its base revision.",
            "Main does not create a worktree for a review on its own.",
            "The worktree exception extends no trust: each worktree still gets repository safety's preparation and "
            "checks.",
            "Before landing or release, main runs the Plan's overall acceptance checks at the commit to be landed or "
            "tagged, within repository safety's Execution rules.",
            "It is main's own run, not a review step: it is not a counted step and adds no verdict.",
            "It runs only when the workspace equals the commit to be landed or tagged, established as for a gated pass, "
            "so an untracked or changed file cannot take part in it.",
            "It runs again whenever the commit to be landed changes, after a fix or any other commit.",
            "After it runs, main compares the workspace as after a review call, and a change to a tracked file or a file "
            "the check depends on makes that run a failed run, with the change as its output.",
            "A failure reopens the Claims it affects under the existing rules, with its output supplied to their reviews "
            "as evidence, and landing and release wait for their passes again; a failure that cannot be attributed with "
            "evidence reopens every Claim the check covers.",
            "- **A condition of the gate.** Landing and release the Acceptance gate covers wait until the final check "
            "passes at the commit to be landed; otherwise only an Accept and land decision that states its actual state "
            "lets them proceed.",
            "When Execution does not allow it, it is recorded as not run, and that is stated before landing and in any "
            "Accept and land decision.",
            "For a landing the gate does not cover, main runs it when Execution allows, reports its state before landing, "
            "and waits for the user's instruction given after that report.",
            "- **Fail closed.** Once the final check has failed at a commit, that commit's state is failed, and a later "
            "pass at the same commit lets landing proceed only through an Accept and land decision that names the "
            "failure.",
            "Its state comes only from main's own run in this session at that commit, never passed from a record or an "
            "earlier session, and after a context compaction main runs it again.",
            "When main cannot establish from this session that the commit has not failed, it treats the commit as failed, "
            "which a decision states as \"failed (presumed: not established as unfailed in this session)\" with the "
            "reason and this session's outputs.",
            "A record can only make the state failed, never passed.",
            "- **Take the final check's state from a record or an earlier session**: anyone who can edit the working "
            "tree could record a pass, and an earlier session's run cannot show that nothing failed since; a record can "
            "only make the state failed.",
            "Because the final check's state never crosses a context compaction or a session, a final commit whose check "
            "ran before one can no longer pass cleanly without a rerun: main runs the check again, and if that commit had "
            "failed, or main cannot establish that it had not, landing needs a decision that names the failure or a new "
            "commit.",
            "- **Main creates a worktree for each review**: it would let implementation continue while a review runs, "
            "but setting up a worktree can mean reinstalling dependencies or rebuilding in other projects, and each new "
            "worktree would need repository safety's preparation and checks again.",
            "- **Parallel review calls in one working tree**:",
            "- **No final check, relying on each Claim's passes**:",
            "- **A counted final review step with its own verdict**:",
        ),
    }

    # Ticket 02, Acceptance item 8: both READMEs explain serial reviews and the final check, paired as README_PAIRS.
    SERIAL_README_PAIRS = (
        ("Serial reviews", "審查依序進行",
         "within one working tree, reviews and implementation take turns.",
         "在同一個工作樹裡，審查與實作輪流進行。"),
        ("Serial reviews", "審查依序進行",
         "While a code review, verification or Adversarial review runs, main changes nothing in the working tree it "
         "judges, not even its own handoff records inside the project, which it updates only between calls, and "
         "implementation there waits until the call ends.",
         "程式碼審查、驗證或對抗式審查執行期間，主 Agent 不會改動它審查的工作樹，連專案內自己的交接紀錄也不改，只在兩次呼叫之間更新；"
         "在那個工作樹裡的實作也要等呼叫結束。"),
        ("Serial reviews", "審查依序進行",
         "Before dispatching such a call, main confirms that no assignment or background process it started that may "
         "write the working tree is still running, and at most one gated call that runs code runs in a working tree at "
         "a time.",
         "派出這類呼叫前，主 Agent 會確認它啟動、可能寫入工作樹的 assignment 或背景程序都已結束，而且同一個工作樹一次最多只跑一個會執行程式碼的"
         "受把關呼叫。"),
        ("Serial reviews", "審查依序進行",
         "If main's comparison after a call finds a change to a file the claim depends on, that call's pass is not used.",
         "呼叫結束後，主 Agent 的比對若發現 claim 依賴的檔案有變動，該次呼叫的通過不予採用。"),
        ("Serial reviews", "審查依序進行",
         "Such a call counts as a call without a pass, covers nothing and resets no count, and the next call reviews the "
         "claim's full scope from its base revision.",
         "這樣的呼叫算作沒有通過的呼叫，不算涵蓋任何範圍，也不重設計數，下一次呼叫會從 claim 的基準版本審查完整範圍。"),
        ("Serial reviews", "審查依序進行",
         "Main never creates a worktree for a review on its own, since setting one up can mean reinstalling dependencies "
         "or rebuilding the project.",
         "主 Agent 不會自行為審查建立 worktree，因為建立 worktree 可能要重新安裝相依套件或重新建置專案。"),
        ("Serial reviews", "審查依序進行",
         "Work you run in separate worktrees may proceed in parallel, each worktree serial in itself and each still "
         "prepared and checked as [Repository safety](#repository-safety) describes.",
         "你分開在不同 worktree 進行的工作可以平行，每個 worktree 內部仍依序進行，也仍各自依[儲存庫安全](#儲存庫安全)所說的方式準備與檢查。"),
        ("Serial reviews", "審查依序進行",
         "Shared test resources stay governed by each brief's target start and reset.",
         "共用的測試資源仍由每份 brief 中測試目標的啟動與重設方式管理。"),
        # Repo trust split ticket 01 (Acceptance 3): the check runs under review state's Execution rule.
        ("Final check", "最終檢查",
         "before landing or release, main runs the plan's overall acceptance checks, such as the full test suite, at the "
         "commit to be landed, as its own run under the Execution rule of [review "
         "state](../skills/delegation/references/review-state.md).",
         "進入預設 branch 或 release 之前，主 Agent 會在要進入預設 branch 的 commit 上執行計畫的整體驗收檢查（例如完整測試），這是它自己的執行，"
         "遵守[審查狀態規則](../skills/delegation/references/review-state.md)中的 Execution 規則。"),
        ("Final check", "最終檢查",
         "It is not a review step: it does not count toward the Stop threshold and adds no verdict.",
         "它不是審查步驟：不計入停止門檻，也不產生新的結論。"),
        # Repo trust split ticket 01 (Acceptance 3): ignored files are outside the workspace reads.
        ("Final check", "最終檢查",
         "It runs only when the workspace equals the commit to be landed or tagged, as main's workspace reads show; "
         "ignored files are outside those reads.",
         "只有在主 Agent 的工作區讀取顯示工作區與要進入預設 branch 或要加 tag 的 commit 相同時才會執行；被忽略的檔案不在這些讀取的範圍內。"),
        ("Final check", "最終檢查",
         "When running the repository's code is not allowed, the check is recorded as not run, and main tells you so "
         "before landing and in any accept-and-land decision.",
         "不允許執行儲存庫程式碼時，這項檢查會記為未執行，主 Agent 會在進入預設 branch 之前，以及任何接受並合併的決定中告訴你。"),
        ("Final check", "最終檢查",
         "It runs again whenever the commit to be landed changes, after a fix or any other commit.",
         "要進入預設 branch 的 commit 只要改變，不論是修正還是其他任何 commit，都會再執行一次。"),
        ("Final check", "最終檢查",
         "If main's comparison after the run finds a change to a tracked file or a file the check depends on, the run "
         "counts as failed, with the change as its output.",
         "執行之後，主 Agent 的比對若發現已追蹤的檔案或檢查依賴的檔案有變動，這次執行就算失敗，變動就是它的輸出。"),
        ("Final check", "最終檢查",
         "Landing and release wait until the check passes at the commit to be landed; otherwise only an accept-and-land "
         "decision that states its actual state lets them proceed.",
         "進入預設 branch 與 release 都要等這項檢查在要進入預設 branch 的 commit 上通過；否則只有寫明它實際狀態的接受並合併決定，才能讓它們繼續。"),
        ("Final check", "最終檢查",
         "Once the check has failed at a commit, that commit stays failed, and a later pass there lets landing proceed "
         "only through a decision that names the failure.",
         "檢查在某個 commit 上失敗後，該 commit 就維持失敗，之後在同一個 commit 上通過，也只有透過寫明這次失敗的決定才能進入預設 branch。"),
        ("Final check", "最終檢查",
         "Main takes the check's state only from its own run in this session at that commit, never from a record or an "
         "earlier session, and runs it again after context compaction; when it cannot establish from this session that "
         "the commit has not failed, it treats the commit as failed.",
         "主 Agent 只採用它在這個 session 於該 commit 上自己執行的結果，絕不採用紀錄或先前 session 的結果，context 壓縮之後也會再執行一次；"
         "無法從這個 session 確定該 commit 沒有失敗時，就視為失敗。"),
        # Retained passes ticket 03 (Acceptance items 7 and 15): a failure reopens claims in off only.
        ("Final check", "最終檢查",
         "In `off`, a failure reopens the claims it affects, with its output as evidence for their reviews, and landing "
         "and release wait for their passes again; a failure main cannot attribute with evidence reopens every claim the "
         "check covers.",
         "在 `off` 下，檢查失敗會重新打開受影響的 claim，並把輸出當作它們審查的證據，進入預設 branch 與 release 都要等它們"
         "再次通過；主 Agent 無法以證據歸因的失敗，會重新打開這項檢查涵蓋的每個 claim。"),
        ("Final check", "最終檢查",
         "For a landing the acceptance gate does not cover, main runs the check when running code is allowed, tells you "
         "its state before landing and waits for your instruction.",
         "驗收把關不涵蓋的合併，主 Agent 在允許執行程式碼時會執行這項檢查，在進入預設 branch 之前告訴你它的狀態，並等你指示。"),
    )

    ACCEPT_LABEL = "review-state.md#Accept and land at the end of the plan"

    # Ticket 03, Acceptance item 6: one decision may name several Claims, asked once at the end of the Plan, with the
    # earlier-landing exception; User decisions and Adversarial review point to it.
    ACCEPT_ONCE = {
        ACCEPT_LABEL: (
            "One accept-and-land decision may name several claims, including a gated claim whose passes are complete when "
            "the final check at the commit to be landed failed or was not run.",
            "Main asks for the decision once, after every claim of the plan has finished its reviews and the final check "
            "has run or is recorded as not run, before landing or release; it does not ask after each claim.",
            "Until then a claim that needs the decision stays under the acceptance gate as it stands, and its ticket "
            "stays unfinished.",
            "Main asks earlier only when the user asks to land a claim earlier.",
        ),
        "review-state.md#User decisions": (
            "Main asks for it, and builds what it names, as Accept and land at the end of the plan describes.",
            "It may also name a gated claim whose passes are complete when the final check at the commit to be landed "
            "failed or was not run, and it then states the final check's state at that commit, as Final check describes.",
        ),
        "adversarial-review.md": (
            "A HELD stays valid only as [review state](review-state.md)'s What a pass covers describes, and accept and "
            "land may cover a missing HELD as its User decisions describe, asked for once at the end of the plan as its "
            "Accept and land at the end of the plan describes.",
        ),
    }

    # S4: the list comes from main's own observations in this session, and only what the user confirms is decided.
    S4 = {
        ACCEPT_LABEL: (
            # Retained passes ticket 06 (Acceptance items 10, 15 and 18): the list built only from this session's review results holds for off.
            "In off, main builds the list from the review results it received in this session, not by reading a record in the "
            "working tree, such as a handoff, a ticket or the Follow-up record, and reports any difference between the "
            "list and such a record.",
            "Each missing pass names the step and the call that left it missing, or that the step has not run.",
            "Known vulnerabilities appear as the reporting role stated them, never merged or downgraded; what main writes "
            "of them in a public or possibly public record follows [adversarial review](adversarial-review.md) step 10.",
            "Where main cannot establish a claim's verdicts or missing passes in this session, for example after context "
            "compaction, Unknown state applies: main stops and asks the user.",
            "The user may confirm part of the list by whole claims, and the rest stays pending, under the acceptance gate "
            "as it stands; a claim is accepted only with everything listed for it.",
            "Saying \"continue\", silence or turning automatic review off is not a confirmation.",
            "The decision covers only what was listed: the claims, their commits, their missing passes and their known "
            "vulnerabilities, and main records it for each claim as User decisions describes.",
            "A Blocking finding or known vulnerability reported after the decision is not covered, and it holds landing "
            "until it is resolved or a new decision names it.",
        ),
    }

    # S5: landing a Claim earlier covers every gated Claim on the branch and states the final check's actual state,
    # which main runs whenever Execution allows.
    S5 = {
        ACCEPT_LABEL: (
            "Landing a claim before the end of the plan lands every claim on that branch, so main's list then covers "
            "every gated claim on the branch, and the decision states the final check's actual state at that commit; "
            "main runs it whenever Execution allows, and records it as not run only when Execution does not.",
        ),
    }

    # The decision's part of S8, and S3: the decision states the final check's state at the commit to be landed, its
    # final-check part covers only what it states, and the Follow-up record plays no part in the decision.
    S8_AND_S3 = {
        ACCEPT_LABEL: (
            "For each claim it names, it states the commit it accepts, the missing passes, the known vulnerabilities and "
            "the remaining risk, and the decision states the final check's state at the commit to be landed: passed, "
            "failed with its output, or not run, as Final check describes.",
            "The final-check part of the decision covers only the commit and the output it states.",
            "Accept and land never relies on the Follow-up record, as Follow-up record describes.",
        ),
        "CONTEXT.md#Follow-up record": ("Accept and land never relies on it.",),
    }

    # Ticket 03, Acceptance item 7: the Accept and land entry covers several Claims and the timing.
    ACCEPT_CONTEXT = {
        "CONTEXT.md#Accept and land": (
            "The user's explicit, recorded acceptance of one or more named gated Claims without one or both passes, or of "
            "a Security-critical claim without its HELD, or of a gated Claim whose passes are complete when the final "
            "check at the commit to be landed failed or was not run, stating for each Claim the commit it accepts, the "
            "missing passes, the known vulnerabilities and the remaining risk, and the final check's state at the commit "
            "to be landed: passed, failed with its output, or not run.",
            "Main asks for it once, after every Claim of the Plan has finished its reviews and the final check has run or "
            "is recorded as not run, before landing or release; until then such a Claim stays under the Acceptance gate "
            "as it stands.",
            "Main asks earlier only when the user asks to land a Claim earlier, and then the decision covers every gated "
            "Claim on that branch and states the final check's actual state at that commit, which main runs whenever "
            "Execution allows.",
            # Retained passes ticket 06 (Acceptance items 10, 15 and 18): the list built only from this session's review results holds for off.
            "In off, main builds the list from the review results it received in this session, never from a record "
            "in the working tree.",
            "The user may confirm part of the list by whole Claims, a Claim being accepted only with everything "
            "listed for it; \"continue\", silence or turning automatic review off is not a confirmation.",
            "A Blocking finding or known vulnerability reported after the decision is not covered and holds landing until "
            "it is resolved or a new decision names it, and its final-check part covers only the commit and output it "
            "states.",
            "It satisfies the Acceptance gate for each Claim it covers until a relevant change, is never READY, APPROVED, "
            "CONFIRMED or HELD, and a casual \"done\" becomes one only after main confirms and records it.",
        ),
    }

    # Ticket 03, Acceptance item 7: ADR 0013's part on the single decision, its rejected options, the note that it
    # amends ADR 0008, and ADR 0008's amendment note.
    ACCEPT_ADR = {
        "ADR 0013#accept": (
            "This part records the single Accept and land decision.",
            "- **Several Claims in one decision.** One Accept and land decision may name several Claims, including a gated "
            "Claim whose passes are complete when the final check at the commit to be landed failed or was not run, "
            "stating for each the commit it accepts, the missing passes, the known vulnerabilities and the remaining "
            "risk, and the final check's state at the commit to be landed: passed, failed with its output, or not run.",
            "Main asks once, after every Claim of the Plan has finished its reviews and the final check has run or is "
            "recorded as not run, before landing or release.",
            "Until then a Claim that needs the decision stays under the Acceptance gate as it stands, and its ticket "
            "stays unfinished.",
            "Landing a Claim before the end of the Plan lands every Claim on that branch, so main's list covers every "
            "gated Claim on the branch, and the decision states the final check's actual state at that commit; main runs "
            "it whenever Execution allows, and records it as not run only when Execution does not.",
            "Main builds the list from the review results it received in this session, not by reading a record in the "
            "working tree, and reports any difference from such a record.",
            "Each missing pass names the step and the call that left it missing, and the known vulnerabilities appear as "
            "the reporting role stated them, never merged or downgraded.",
            "Where main cannot establish a Claim's verdicts or missing passes, as after a context compaction, Unknown "
            "state applies and main stops and asks.",
            "Accept and land never relies on the Follow-up record.",
            "- **What counts as the decision.** The user may confirm part of the list by whole Claims, the rest staying "
            "pending, and a Claim is accepted only with everything listed for it; \"continue\", silence or turning "
            "automatic review off is not a confirmation, and the decision covers only what was listed.",
            "A Blocking finding or known vulnerability reported after the decision is not covered and holds landing until "
            "it is resolved or a new decision names it, and the final-check part covers only the commit and output it "
            "states.",
            "This amends [ADR 0008](0008-repository-authority-acceptance-and-gate-lifetime.md): an Accept and land "
            "decision may name several Claims, including one whose passes are complete when the final check failed or "
            "was not run, and main asks for it once at the end of the Plan, or earlier only for the whole branch when the "
            "user asks to land a Claim earlier, with a list built from its own observations in this session.",
            "A Claim whose passes are complete still needs the decision when the final check at the commit to be landed "
            "failed or was not run, and after a compaction or in a new session the check must run again before that "
            "state is known.",
            "- **Ask after every Claim that needs the decision**:",
            "- **Build the list from a record in the working tree**, such as a handoff or the Follow-up record:",
            "- **Merge or summarise known vulnerabilities across Claims**:",
            "- **Take \"continue\" or silence as a confirmation of the whole list**:",
        ),
        "ADR 0008": (
            "(Amended by ADR 0013: one Accept and land decision may name several Claims, including a gated Claim whose "
            "passes are complete when the final check at the commit to be landed failed or was not run, stating for each "
            "the commit it accepts, the missing passes, the known vulnerabilities and the remaining risk, and the final "
            "check's state at the commit to be landed: passed, failed with its output, or not run.",
            "Main asks for it once, after every Claim of the Plan has finished its reviews and the final check has run or "
            "is recorded as not run, before landing or release, and earlier only when the user asks to land a Claim "
            "earlier, which covers every gated Claim on that branch and states the final check's actual state at that "
            "commit.",
            "Main builds the list from the review results it received in this session, not from a record in the working "
            "tree, and the user may confirm part of it by whole Claims; a Blocking finding or known vulnerability "
            "reported after the decision is not covered.",
            "Landing and release the Acceptance gate covers also wait for the final check to pass at the commit to be "
            "landed, unless such a decision states its actual state; the rest of this record is unchanged.)",
        ),
    }

    # Ticket 03, Acceptance item 8: both READMEs explain the single decision, paired as README_PAIRS.
    ACCEPT_README_PAIRS = (
        ("Accept and land at the end", "最後一次決定接受並合併",
         "when claims of a plan need an accept-and-land decision, main asks you once, after every claim of the plan has "
         "finished its reviews and the final check has run or is recorded as not run, before landing or release, not "
         "after each claim.",
         "計畫中有 claim 需要你決定接受並合併時，主 Agent 只問你一次：在計畫的每個 claim 都完成審查、最終檢查已執行或記為未執行之後，"
         "進入預設 branch 或 release 之前，而不是每個 claim 各問一次。"),
        ("Accept and land at the end", "最後一次決定接受並合併",
         "One decision may name several claims, including a claim whose passes are complete when the final check at the "
         "commit to be landed failed or was not run, stating for each the commit it accepts, the missing passes, the "
         "known vulnerabilities and the remaining risk, and the final check's state at the commit to be landed: passed, "
         "failed with its output, or not run.",
         "一個決定可以涵蓋多個 claim，包括關卡都已通過、但最終檢查在要進入預設 branch 的 commit 上失敗或未執行的 claim，並為每個 claim 寫明所接受的"
         " commit、缺少的關卡、已知漏洞與剩餘風險，以及最終檢查在要進入預設 branch 的 commit 上的狀態：通過、失敗（附上輸出）或未執行。"),
        ("Accept and land at the end", "最後一次決定接受並合併",
         "Until then such a claim stays under the acceptance gate as it stands and its ticket stays unfinished.",
         "在那之前，這類 claim 照原樣受驗收把關，它的 ticket 也維持未完成。"),
        ("Accept and land at the end", "最後一次決定接受並合併",
         "Main asks earlier only when you ask to land a claim earlier; since that lands every claim on the branch, the "
         "list then covers every gated claim on that branch and states the final check's actual state at that commit, "
         "which main runs whenever running code is allowed.",
         "只有你要求提早合併某個 claim 時，主 Agent 才會提早問；因為那會讓整個 branch 上的 claim 一起合併，清單就涵蓋該 branch "
         "上每個受把關的 claim，並寫明最終檢查在那個 commit 上的實際狀態，只要允許執行程式碼，主 Agent 都會執行它。"),
        # Retained passes ticket 06 (Acceptance items 10, 15 and 18): the list built only from this session's review results holds for off.
        ("Accept and land at the end", "最後一次決定接受並合併",
         "In `off`, main builds the list from the review results it received in this session, not from a record in "
         "the working tree such as a handoff or the Follow-up record, and tells you where such a record differs.",
         "在 `off` 下，主 Agent 依它在這個 session 收到的審查結果建立清單，不依據工作樹中的紀錄（例如交接或後續紀錄），並告訴你這類紀錄與清單的差異。"),
        ("Accept and land at the end", "最後一次決定接受並合併",
         "Each missing pass names the step and call that left it missing, or that the step has not run, and known "
         "vulnerabilities appear as the role that reported them stated them, never merged or downgraded.",
         "每個缺少的關卡都寫明是哪個步驟、哪次呼叫讓它缺少，或該步驟尚未執行；已知漏洞照回報角色的原話列出，絕不合併或降級。"),
        ("Accept and land at the end", "最後一次決定接受並合併",
         "When main cannot establish a claim's verdicts or missing passes, for example after context compaction, it "
         "stops and asks you.",
         "主 Agent 無法確定某個 claim 的結論或缺少的關卡時（例如 context 壓縮之後），會停下來問你。"),
        ("Accept and land at the end", "最後一次決定接受並合併",
         "You may confirm part of the list by whole claims, and the rest stays pending; a claim is accepted only with "
         "everything listed for it.",
         "你可以以整個 claim 為單位只確認清單的一部分，其餘維持待決；claim 只有連同為它列出的所有內容一起，才算被接受。"),
        ("Accept and land at the end", "最後一次決定接受並合併",
         "Saying \"continue\", silence or turning automatic review off is not a confirmation, and the decision covers "
         "only what was listed: a blocking finding or known vulnerability reported after it is not covered and holds "
         "landing until it is resolved or a new decision names it, and its final-check part covers only the commit and "
         "output it states.",
         "說「繼續」、沒有回應或關掉自動審查都不算確認，這個決定也只涵蓋清單上列出的內容：決定之後才回報的阻擋性問題或已知漏洞不在其中，在它解決或"
         "新的決定寫明它之前，都會擋住合併；決定中最終檢查的部分也只涵蓋它寫明的 commit 與輸出。"),
    )

    # The replaced Accept and land entry, which named one Claim and listed known vulnerabilities only for a missing
    # HELD: absent now, present at v0.23.0.
    OLD_ACCEPT_AND_LAND = {
        "CONTEXT.md#Accept and land": (
            "The user's explicit, recorded acceptance of a named gated Claim without one or both passes,",
            "with the commit it accepts, the missing passes and the remaining risk, and for a missing HELD the known "
            "vulnerabilities.",
            "It satisfies the Acceptance gate for that Claim until a relevant change,",
        ),
    }

    # The interim wording of tickets 01 to 03 at INTERIM that the spec's amendment after the first Adversarial round
    # replaced: absent now, present at INTERIM.
    INTERIM = "7e23fbf"
    INTERIM_WORDING = {
        "review-state.md#Final check": (
            "once at the final commit",
            "It runs again at the new final commit after any fix.",
        ),
        ACCEPT_LABEL: (
            "has passed or is recorded as not run",
            "the decision states that the final check has not run",
            "when the final check is recorded as not run, that the final check has not run",
            "The user may confirm part of the list, and the rest stays pending, under the acceptance gate as it stands.",
        ),
        "outcome-verification.md#7": ("including the verifier's optional notes, do not hold completion",),
        "outcome-verification.md#4": ("a security problem or data loss the change introduced is never rejected",),
        "code-review.md#4": ("a security problem or data loss the change introduced is never rejected",),
        "reviewer.md": ("the base revision you are given",),
        "CONTEXT.md#Accept and land": (
            "has passed or is recorded as not run",
            "states that the final check has not run",
            "and that the final check has not run when it is recorded as not run",
            "and the user may confirm part of it;",
        ),
        "ADR 0013": (
            "once at the final commit",
            "has passed or is recorded as not run",
            "the decision states that the final check has not run",
            "It runs again at the new final commit after any fix.",
            "ADR 0006's state model, validity rules and Acceptance gate are unchanged.",
        ),
        "ADR 0008": (
            "has passed or is recorded as not run",
            "and that the final check has not run when it is recorded as not run",
        ),
        "ADR 0006": ("the state model, validity rules and Acceptance gate are unchanged.)",),
        "reference.md#Final check": (
            "once at the final commit",
            "After any fix, the check runs again at the new final commit.",
        ),
        "reference.md#Accept and land at the end": (
            "has passed or is recorded as not run",
            "states that the final check has not run",
            "You may confirm part of the list, and the rest stays pending;",
        ),
        "reference.zh-TW.md#最終檢查": (
            "在最終 commit 上執行一次",
            "任何修正之後，都會在新的最終 commit 上再執行一次。",
        ),
        "reference.zh-TW.md#最後一次決定接受並合併": (
            "最終檢查已通過或記為未執行",
            "並寫明最終檢查尚未執行",
            "你可以只確認清單的一部分",
        ),
    }

    def new_pins(self):
        pins = {}
        for group in (self.REVIEW_STATE, self.PROCEDURES, self.S1, self.S2, self.S3, self.REVIEWER, self.CONTEXT,
                      self.ADR, self.SERIAL, self.S7, self.FINAL_CHECK, self.S8, self.SERIAL_ADR, self.ACCEPT_ONCE,
                      self.S4, self.S5, self.S8_AND_S3, self.ACCEPT_CONTEXT, self.ACCEPT_ADR, self.S1_VERIFIER_NOTE,
                      self.S2_BRIEFS, self.S7_PROCEDURES):
            for place, sentences in group.items():
                pins.setdefault(place, []).extend(sentences)
        for en_label, zh_label, english, chinese in (self.README_PAIRS + self.SERIAL_README_PAIRS
                                                     + self.ACCEPT_README_PAIRS):
            pins.setdefault(f"reference.md#{en_label}", []).append(english)
            pins.setdefault(f"reference.zh-TW.md#{zh_label}", []).append(chinese)
        return pins

    def test_review_state_states_the_completion_conditions(self):
        self.assert_pinned(self.REVIEW_STATE)

    def test_plan_review_and_the_procedures_state_the_criteria(self):
        self.assert_pinned(self.PROCEDURES)

    def test_s1_security_findings_still_block(self):
        self.assert_pinned(self.S1)

    def test_s1_a_verifiers_security_note_withholds_its_confirmed(self):
        self.assert_pinned(self.S1_VERIFIER_NOTE)

    def test_s2_regressions_are_judged_against_the_base_revision(self):
        self.assert_pinned(self.S2)

    def test_s2_every_brief_names_the_claims_base_revision(self):
        self.assert_pinned(self.S2_BRIEFS)
        for prefix in ("", "cc-"):
            rendered = config._render("reviewer", {"model": "sonnet", "effort": "high"}, prefix).decode("utf-8")
            with self.subTest(prefix=prefix):
                self.assertIn(self.S2_BRIEFS["reviewer.md"][0], rendered)
                self.assertNotIn("the base revision you are given", rendered)

    def test_s3_the_follow_up_record_is_data(self):
        self.assert_pinned(self.S3)

    def test_the_reviewer_template_states_the_new_criteria(self):
        self.assert_pinned(self.REVIEWER)

    def test_the_installed_reviewer_renders_the_new_criteria(self):
        choice = {"model": "sonnet", "effort": "high"}
        for prefix in ("", "cc-"):
            rendered = config._render("reviewer", choice, prefix).decode("utf-8")
            for sentence in self.REVIEWER["reviewer.md"]:
                with self.subTest(prefix=prefix, sentence=sentence[:60]):
                    self.assertIn(sentence, rendered)

    def test_the_verifier_and_adversary_templates_are_unchanged(self):
        for (role, digest), tag in ((item, tag) for item in self.UNCHANGED_ROLES.items() for tag in self.UNCHANGED_BETWEEN):
            text = self.tagged_path(f"templates/agents/{role}.md", tag)
            with self.subTest(role=role, tag=tag):
                lines = text.replace("\r\n", "\n").split("\n")
                # Exactly one line is the shared paragraph, so removing it hides nothing else.
                paragraph = [line for line in lines if line.startswith(self.REPOSITORY_SAFETY_LINE)]
                self.assertEqual(len(paragraph), 1)
                rest = "\n".join(line for line in lines if not line.startswith(self.REPOSITORY_SAFETY_LINE))
                self.assertEqual(hashlib.sha256(rest.encode("utf-8")).hexdigest(), digest)

    def test_glossary_states_the_criteria_for_every_review_step(self):
        self.assert_pinned(self.CONTEXT)
        entries = feather_support.glossary_entries((config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        self.assertEqual(entries["Follow-up record"], self.FOLLOW_UP_ENTRY)

    def test_both_readmes_explain_what_holds_completion_and_what_is_recorded(self):
        for en_label, zh_label, english, chinese in self.README_PAIRS:
            for place, sentence in ((f"reference.md#{en_label}", english), (f"reference.zh-TW.md#{zh_label}", chinese)):
                with self.subTest(place=place, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.source(place))

    def test_adr_0013_records_the_completion_criteria_and_amends_adr_0006(self):
        # The serial rule, the final check and the single Accept and land decision, with the note amending ADR 0008, are
        # added to ADR 0013 by the tickets that implement them.
        self.assert_pinned(self.ADR)
        lines = self.source("ADR 0006").splitlines()
        self.assertEqual(sum(line.startswith("(Amended by ADR 0013:") for line in lines), 1)

    def test_reviews_are_serial_within_a_working_tree(self):
        self.assert_pinned(self.SERIAL)

    def test_s7_nothing_writes_the_tree_a_review_judges(self):
        self.assert_pinned(self.S7)

    def test_s7_a_call_whose_pass_is_not_used_neither_passes_nor_narrows_in_the_procedures(self):
        self.assert_pinned(self.S7_PROCEDURES)
        # Each exception follows the rule it qualifies.
        step_3 = self.source("code-review.md#3")
        self.assertLess(step_3.index("An automatic APPROVED resets the count to zero"),
                        step_3.index(self.S7_PROCEDURES["code-review.md#3"][0]))
        step_6 = self.source("code-review.md#6")
        self.assertLess(step_6.index("With APPROVED in the automatic flow, continue to outcome verification"),
                        step_6.index(self.S7_PROCEDURES["code-review.md#6"][0]))
        held = self.source("adversarial-review.md#6")
        self.assertLess(held.index("Before accepting a HELD, main checks it"),
                        held.index(self.S7_PROCEDURES["adversarial-review.md#6"][0]))
        recheck = self.source("outcome-verification.md#4")
        self.assertLess(recheck.index("When the previous verification call completed, use the next call to recheck"),
                        recheck.index(self.S7_PROCEDURES["outcome-verification.md#4"][0]))
        coverage = self.source("adversarial-review.md#5")
        after_broken, after_inconclusive = self.S7_PROCEDURES["adversarial-review.md#5"]
        self.assertLess(coverage.index("A call after BROKEN covers the fix and every open gap"),
                        coverage.index(after_broken))
        self.assertLess(coverage.index(after_broken), coverage.index("After any INCONCLUSIVE, whether the adversary"))
        for rule in ("When the open item is coverage the role could have examined",
                     "When the call lacked a target, evidence or prerequisite, the next call runs only once"):
            with self.subTest(rule=rule[:40]):
                self.assertLess(coverage.index(rule), coverage.index(after_inconclusive))
        # Only a HELD main accepts continues to completion; the unqualified continuation is gone.
        step_8 = self.source("adversarial-review.md#8")
        accepted, not_accepted = self.S7_PROCEDURES["adversarial-review.md#8"]
        self.assertTrue(step_8.startswith(f"8. {accepted} {not_accepted} "))
        self.assertNotIn("With HELD in the automatic flow, continue to completion", step_8)

    def test_review_state_states_the_final_check(self):
        self.assert_pinned(self.FINAL_CHECK)

    def test_s8_the_final_check_judges_the_landing_commit(self):
        self.assert_pinned(self.S8)

    def test_the_serial_rule_and_final_check_sit_beside_what_a_gated_pass_judged(self):
        # Both rules sit in Validity and completion, right after the rule they extend and before the existing notes.
        text = (config.ROOT / self.PATHS["review-state.md"]).read_text(encoding="utf-8")
        section = text.split("## Validity and completion", 1)[1].split("\n## ", 1)[0]
        order = [section.index(f"\n- **{label}.**") for label in (
            "What a gated pass judged", "Serial within a working tree", "Final check", "Existing handoff notes")]
        self.assertEqual(order, sorted(order))

    def test_adr_0013_records_the_serial_rule_and_the_final_check(self):
        self.assert_pinned(self.SERIAL_ADR)
        text = self.source("ADR 0013")
        # The part follows ticket 01's Consequences; the single Accept and land decision is ticket 03's part.
        self.assertLess(text.index("\n## Consequences\n"), text.index(self.ADR_0013_SERIAL))
        self.assertNotIn("ADR 0008", self.source("ADR 0013#serial"))

    def test_both_readmes_explain_serial_reviews_and_the_final_check(self):
        for en_label, zh_label, english, chinese in self.SERIAL_README_PAIRS:
            for place, sentence in ((f"reference.md#{en_label}", english), (f"reference.zh-TW.md#{zh_label}", chinese)):
                with self.subTest(place=place, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.source(place))

    def test_review_state_asks_for_accept_and_land_once_at_the_end(self):
        self.assert_pinned(self.ACCEPT_ONCE)

    def test_s4_the_accept_and_land_list_comes_from_mains_own_observations(self):
        self.assert_pinned(self.S4)

    def test_s5_landing_earlier_covers_the_whole_branch(self):
        self.assert_pinned(self.S5)

    def test_s8_and_s3_the_decision_states_a_final_check_not_run_and_never_relies_on_the_follow_up_record(self):
        self.assert_pinned(self.S8_AND_S3)

    def test_the_decision_sits_with_the_users_decisions(self):
        # The rule follows User decisions, where Accept and land is defined, and names no Pending-acceptance claim for a
        # Claim waiting for the decision.
        text = (config.ROOT / self.PATHS["review-state.md"]).read_text(encoding="utf-8")
        section = text.split("## Ticket status and user decisions", 1)[1].split("\n## ", 1)[0]
        labels = [line.split("**", 2)[1] for line in section.splitlines() if line.startswith("- **")]
        self.assertEqual(labels[-2:], ["User decisions.", "Accept and land at the end of the plan."])
        self.assertNotIn("Pending-acceptance claim", self.source(self.ACCEPT_LABEL))

    def test_glossary_accept_and_land_covers_several_claims_and_the_timing(self):
        self.assert_pinned(self.ACCEPT_CONTEXT)

    def test_adr_0013_records_the_single_decision_and_amends_adr_0008(self):
        self.assert_pinned(self.ACCEPT_ADR)
        text = self.source("ADR 0013")
        # The part follows the serial rule and the final check, and only this part amends ADR 0008.
        self.assertLess(text.index(self.ADR_0013_SERIAL), text.index(self.ADR_0013_ACCEPT))
        self.assertIn("ADR 0008", self.source("ADR 0013#accept"))
        lines = self.source("ADR 0008").splitlines()
        self.assertEqual(sum(line.startswith("(Amended by ADR 0013:") for line in lines), 1)

    def test_both_readmes_explain_the_single_accept_and_land_decision(self):
        for en_label, zh_label, english, chinese in self.ACCEPT_README_PAIRS:
            for place, sentence in ((f"reference.md#{en_label}", english), (f"reference.zh-TW.md#{zh_label}", chinese)):
                with self.subTest(place=place, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.source(place))

    def test_the_old_accept_and_land_entry_is_gone(self):
        for place, phrases in self.OLD_ACCEPT_AND_LAND.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    def test_the_old_blocking_criteria_are_gone(self):
        for place, phrases in self.OLD_CRITERIA.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    def test_the_interim_wording_is_gone(self):
        for place, phrases in self.INTERIM_WORDING.items():
            text = self.source(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertNotIn(phrase, text)

    def tagged_path(self, path, revision):
        """A file's text at a revision; skips when Git cannot be run or the revision or the file cannot be read."""
        try:
            shown = subprocess.run([*self.GIT_READ, "cat-file", "blob", f"{revision}:{path}"], cwd=config.ROOT,
                                   stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.skipTest(f"Git cannot be run, so the {revision} text cannot be read: {error}")
        if shown.returncode != 0:
            self.skipTest(f"{path} cannot be read at {revision} in this checkout")
        return shown.stdout.decode("utf-8")

    def tagged(self, place, revision=None):
        """The whole file behind a place at the revision (the tag by default), '' when it did not exist there; skips
            without that revision."""
        revision = revision or self.TAG
        name = place.partition("#")[0]
        path = self.PATHS[self.SPLIT_FROM.get(name, name)]
        try:
            shown = subprocess.run([*self.GIT_READ, "cat-file", "blob", f"{revision}:{path}"], cwd=config.ROOT,
                                   stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
            known = subprocess.run([*self.GIT_READ, "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}"],
                                   cwd=config.ROOT, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.skipTest(f"Git cannot be run, so the {revision} text cannot be read: {error}")
        if known.returncode != 0:
            self.skipTest(f"no {revision} in this checkout")
        return shown.stdout.decode("utf-8") if shown.returncode == 0 else ""

    def test_every_interim_absence_pin_matches_the_interim_text(self):
        for place, phrases in self.INTERIM_WORDING.items():
            text = self.tagged(place, self.INTERIM)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertIn(phrase, text)

    def test_every_new_pin_fails_on_the_v0_23_0_text(self):
        for place, sentences in self.new_pins().items():
            text = self.tagged(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertFalse(sentence in text, f"{place} already said this at {self.TAG}")

    def test_every_absence_pin_matches_the_v0_23_0_text(self):
        for place, phrases in {**self.OLD_CRITERIA, **self.OLD_ACCEPT_AND_LAND}.items():
            text = self.tagged(place)
            for phrase in phrases:
                with self.subTest(place=place, phrase=phrase[:60]):
                    self.assertIn(phrase, text)


class WeighFindingsBeforeRulesTests(unittest.TestCase):
    """0.28.0 (docs/specs/weigh-findings-before-rules.md, Acceptance items 1 to 6): the delegation skill weighs a finding
    before main proposes or adopts a requirement or fix derived from it, in its own paragraph right after the paragraph on
    main's ownership; the installed policy loads the skill for that; both references describe it in one sentence."""

    SKILL = "skills/delegation/SKILL.md"
    OWNERSHIP = "Run this workflow in the main conversation. Main owns decisions and final acceptance;"
    # Acceptance items 1, 2 and 3, in order: the paragraph is exactly these sentences, so it lists no paths, defines no
    # attacker model and adds no approval step.
    PARAGRAPH = (
        "Before proposing or adopting a requirement or fix derived from any finding, main briefly states, alongside the "
        "proposed remedy and without a separate recap, grouping findings that share one remedy and reason, when the case "
        "can occur in normal use or under the applicable threat model, its worst credible outcome, and whether an "
        "existing rule covers it, preferring to reuse or correct a rule.",
        "For optional work, main recommends fixes for cases normal use encounters, data loss, or security problems under "
        "that threat model.",
        "Normal-use rarity alone never justifies discounting such a security problem.",
        "This weighing selects remedies and recommendations only: existing blocking conditions, rejection evidence, "
        "security-disposition procedures and user decisions still govern, and rarity or a minor outcome alone is not "
        "rejection evidence for a Blocking finding or a plan-review blocker.",
    )
    # Acceptance item 4: the policy's loading sentence with the new trigger.
    POLICY = ("Also use it for requested security analysis, explicitly requested plan review, code review or outcome "
              "verification, requests to turn automatic review on or off, before proposing or adopting a requirement or "
              "fix derived from a finding, and before implementing a Security-critical change.")
    TRIGGER = "before proposing or adopting a requirement or fix derived from a finding"
    # Acceptance item 5: one sentence in each reference, in the Follow-up record bullet beside Findings.
    REFERENCES = (
        ("reference.md#Follow-up record",
         "Before main proposes or adopts a requirement or fix derived from any finding, it briefly states when the case "
         "can occur in normal use or under the applicable threat model, its worst credible outcome and whether an "
         "existing rule already covers it, prefers reusing or correcting a rule, and for optional work recommends fixes "
         "for what normal use encounters, data loss and security problems, which normal-use rarity never discounts; the "
         "weighing never changes what blocks, what counts as rejection evidence, how security findings are "
         "dispositioned or your decisions."),
        ("reference.zh-TW.md#後續紀錄",
         "主 Agent 依任何問題提出或採用一項要求或修正之前，會先簡短說明這個情況在一般使用中或適用的威脅模型下何時會發生、"
         "最壞而可信的後果，以及既有規則是否已經涵蓋，並優先沿用或修正既有規則；對可選的工作，它會建議修正一般使用會遇到的"
         "情況、資料遺失與安全問題，安全問題不會只因一般使用中少見就被輕忽；這項權衡從不改變什麼會擋下、什麼算駁回證據、"
         "安全問題的處置方式或你的決定。"),
    )
    PREVIOUS = "v0.27.1"
    GIT_READ = CompletionCriteriaTests.GIT_READ

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    @classmethod
    def paragraphs(cls, text):
        body = text.replace("\r\n", "\n").split("\n---\n", 1)[1]
        return [paragraph.strip() for paragraph in body.split("\n\n") if paragraph.strip()]

    def test_the_paragraph_follows_the_ownership_paragraph(self):
        paragraphs = self.paragraphs((config.ROOT / self.SKILL).read_text(encoding="utf-8"))
        owners = [index for index, paragraph in enumerate(paragraphs) if paragraph.startswith(self.OWNERSHIP)]
        self.assertEqual(len(owners), 1)
        self.assertEqual(paragraphs[owners[0] + 1], " ".join(self.PARAGRAPH))
        # Stated once, in the skill only: no section or other paragraph repeats it.
        self.assertEqual(sum(self.PARAGRAPH[0] in paragraph for paragraph in paragraphs), 1)

    def test_the_paragraph_names_only_the_existing_limits(self):
        paragraph = " ".join(self.PARAGRAPH)
        for phrase in ("existing blocking conditions", "rejection evidence", "security-disposition procedures",
                       "user decisions still govern", "the applicable threat model"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, paragraph)
        for absent in ("approval", "approve", "attacker", "`", "](", "references/"):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, paragraph)

    def test_the_policy_template_loads_the_skill_for_it(self):
        template = (config.ROOT / "templates" / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertEqual(template.count(self.POLICY), 1)
        self.assertEqual(template.count(self.TRIGGER), 1)

    def test_every_rendered_policy_carries_the_trigger(self):
        for mode in ("auto", "off"):
            for scope in ("project", "user"):
                for prefix in ("", config.ROLE_PREFIX):
                    with self.subTest(mode=mode, scope=scope, prefix=prefix):
                        self.assertEqual(config._delegation_block(mode, prefix, scope, None).count(self.POLICY), 1)

    def test_both_references_describe_the_rule_in_one_sentence(self):
        for place, sentence in self.REFERENCES:
            with self.subTest(place=place):
                self.assert_whole_sentence(sentence, feather_support.review_rules_source(place))
                whole = (config.ROOT / "docs" / place.partition("#")[0]).read_text(encoding="utf-8")
                self.assertEqual(whole.count(sentence), 1)

    def previous(self, path):
        try:
            shown = subprocess.run([*self.GIT_READ, "cat-file", "blob", f"{self.PREVIOUS}:{path}"], cwd=config.ROOT,
                                   stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.skipTest(f"Git cannot be run, so the {self.PREVIOUS} text cannot be read: {error}")
        if shown.returncode != 0:
            self.skipTest(f"no {self.PREVIOUS} in this checkout")
        return shown.stdout.decode("utf-8")

    def test_every_new_pin_fails_on_the_v0_27_1_text(self):
        pins = [(self.SKILL, sentence) for sentence in self.PARAGRAPH]
        pins += [("templates/CLAUDE.md", self.TRIGGER)]
        pins += [(f"docs/{place.partition('#')[0]}", sentence) for place, sentence in self.REFERENCES]
        for path, sentence in pins:
            with self.subTest(path=path, sentence=sentence[:60]):
                self.assertNotIn(sentence, self.previous(path))


if __name__ == "__main__":
    unittest.main()
