---
name: setup
description: "Set up, check, update or remove Claude Feather delegation roles and CLAUDE.md guidance, including a low-cost native Explore override. Use for installation scope and ownership changes."
---

# Feather Setup for Claude Code

The plugin supplies handoff, setup, model, auto-on and auto-off skills. Setup deploys native roles and a marked CLAUDE.md policy to a user or project scope. It includes an exact-name Explore override because the built-in Explore inherits the main model. It does not change the main model, concurrency, settings.json, permission policy or handoff records.

Use [the bundled Python tool](../../scripts/feather_config.py) for managed operations; do not recreate its writes with an editor or shell. Resolve it from this skill's actual loaded installation (`../../scripts/feather_config.py`), not the user's project. Keep the complete plugin tree together. Python 3.11+ and its standard library are sufficient. If unavailable, report the prerequisite; installing Python needs the user's authorization.

## Resolve and inspect

1. Establish the intended project root, operation and scope from the current workspace/user request. Use a confirmed absolute root, not a plugin cache or arbitrary launch subdirectory. For a new installation with no stated scope, ask project-only or user-wide while continuing read-only checks. Preserve an existing scope; scope migration is an explicit remove/install operation.
2. Run `check --project <root> --scope <project|user>`. User scope uses CLAUDE_CONFIG_DIR or the user's .claude directory; `--claude-home <absolute-path>` explicitly selects another configuration root. Do not scan unrelated homes or alter environment variables to make a check pass.
3. Read [lifecycle and runtime limits](../../docs/setup.md) when an existing installation, Explore collision, role shadowing, force-model setting, tracking choice or removal is involved. A local check cannot prove managed/CLI/provider configuration or live model selection. Existing unrelated Explore definitions require reconciliation with the user; never silently overwrite them or report protection active while a conflict remains.

## Automatic plan review setting

Dedicated `/cc-feather:auto-on` and `/cc-feather:auto-off` commands follow [the toggle procedure](references/auto-review.md); no argument means session-only, while `project`/`user` persist.

Use this skill to persist the user's automatic plan review preference in the selected owning scope. `off` is the default and disables automatic triggering. When enabled, `auto` triggers review only for material risk, while an explicit request to review a plan still runs it. A task/session enable/disable instruction takes priority without writing files. Neither setting resets the two-call budget for a review already in progress.

Inspect the current `review_mode` with show/check. Preview `review --project <root> --scope <scope> --review-mode <auto|off>`, then apply with the same arguments, `--apply` and its `--expected-plan`. An install can also take `--review-mode`; updates preserve the saved choice. This controls the managed policy text; it is not a hook-enforced runtime switch. The user must have an installed scope for a permanent toggle.

## Preview and apply

```text
python -B <tool> install --project <root> --scope project
python -B <tool> install --project <root> --scope project --apply --expected-plan <plan_id>
python -B <tool> check --project <root> --scope project
```

Use `update` or `remove` in place of `install` for an owned installation. Commands default to preview; copy the returned plan identifier exactly when applying the same operation/arguments. Summarize the concrete target paths, role values, guidance changes and any warnings before writing. A prior explicit request to set up/update/remove that scope is authorization; do not add a routine confirmation gate. Ask only for missing scope, replacement of unrelated content or required environment permission. A stale plan requires a new preview and reconciliation; it is not permission to override current files.

After apply, run check and show. Report saved configuration separately from live loading, ownership conflicts, backup/recovery paths and next action. Updates retain saved model/effort choices; use cc-feather:model to change them. Setup does not edit the plugin cache or deploy Codex role files. Existing local modifications are preserved as conflicts, including during removal.

Fresh sessions are the reliable pickup instruction, especially when the agents directory did not exist at session startup. When native runtime evidence is available, confirm Explore uses the intended definition and model with /tasks; model aliases, provider restrictions, CLI overrides and force settings may change execution. Do not promise a token-count reduction; routing primarily avoids unintended expensive-model use.

Before plugin uninstall, remove each authorized managed scope if the user wants its external roles/policy removed. Disabling/removing the plugin alone leaves those files. Keep .feather handoffs and unrelated CLAUDE.md content intact. Do not remove a user-wide installation as part of project-only removal.

## Unprefixed role names and migration

Native names are scout, analyst, mech-executor, executor, security-executor and Explore. During setup, report existing same-name roles (including different filenames or subdirectories), preserve their files and ask the user how to resolve the conflict. Options include keeping the existing configuration, renaming the existing role, or backing it up and replacing it after explicit authorization. Do not automatically adopt or overwrite a role. Check applicable user/project precedence when definitions exist in different scopes.

For an owned legacy installation, run setup update in its owning scope. It previews migration from feather-* names, retains saved model/effort and review mode, and removes only intact owned legacy files. Occupied target names or modified owned files block migration until resolved by the user. Restart the session afterward. Model/review mutations and session export require migration first; removal of an intact legacy installation remains supported. Use the managed tool for migration, not manual edits to ownership state.
