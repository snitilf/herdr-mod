# Herdr customizations

This repository is the source of truth for the Iris Herdr workspace and its customizations.
Herdr reads its live configuration from `~/.config/herdr-app`, and Codex reads themes from `~/.codex/themes`.

## Contents

- `layouts/`: the Iris workspace layout.
- `mods/`: the customized Spaces and Agents panels.
- `themes/`: the Iris interface and terminal palette.
- `codex-themes/`: the matching Codex syntax theme.
- `fonts/`: Paper Mono and its license.
- `scripts/`: the local sync tool.
- `docs/`: customization decisions.
- `tests/`: tests for this repository.

The Herdr layout and mods derive from Herdr App, available under the Apache 2.0 license at https://github.com/herdrdev/herdr-app.
Paper Mono is distributed under the SIL Open Font License in `fonts/OFL.txt`.

## Sync

Run `python3 scripts/sync.py` to preview changes and detect drift.
Run `python3 scripts/sync.py --apply` to copy source files to the live configuration.
The script refuses to overwrite live files changed since the last successful sync.
It does not delete live files or change application state.
Validate changed mods with `herdr-app check` and inspect them in Herdr.

## Status

The Iris theme and sidebar layout are active in Herdr.
The Agents mod passed `herdr-app check` when run in the user's terminal on November 1, 2026.
The Spaces mod check has not yet been confirmed.
The multi-repository panel and Codex and Claude Code subagent integration are not implemented.
