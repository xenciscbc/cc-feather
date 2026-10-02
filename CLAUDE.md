# cc-feather

## Releases

- A release tag is `v<version>`, where `<version>` is exactly the `version` in `.claude-plugin/plugin.json` at the tagged commit. Check the two match before creating the tag.
- Claude Code plugin updates follow `plugin.json`, so once a version has been pushed to main, any later change that will be released needs a new version in `plugin.json` before it is tagged. Never reuse, move or re-point an existing tag.
- Record the release's validation under its version heading in `docs/setup-validation.md`.
