<!-- cc-feather:begin -->
# Feather delegation for Claude Code

Keep small or tightly coupled work with main; delegate independent work. Only main delegates. Main owns decisions, integration and acceptance; delegation grants no additional authority.

Before dispatching, accepting or recovering delegated work, read and follow cc-feather:delegation. Also use it for requested security analysis and before material security-boundary implementation. If the skill or required managed role is unavailable, report the limitation and stop the affected delegation or required review.

Automatic plan review mode: {{review_mode}}

Task/session choices override the saved mode. Explicit requests for plan review, code review or verification apply in either mode. In auto, use cc-feather:delegation so that work done from a plan, spec or ticket the user agreed to gets plan review before implementation, then code review, then outcome verification before it is reported complete. In auto, unplanned work that changes a security boundary, migrates data or performs an irreversible operation first needs a written, reviewed plan the user approves, and other unplanned edits get no automatic review. In auto, before implementing, state whether the work is plan-driven and therefore reviewed, with a one-line reason. In off, trigger review and verification only on request.

{{role_names}}<!-- cc-feather:end -->
