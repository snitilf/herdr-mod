# Herdr customizations

This repository is the source of truth for the Iris Herdr workspace and its customizations.
Herdr reads its live configuration from `~/.config/herdr-app`, and Codex reads themes from `~/.codex/themes`.

## Contents

- `layouts/`: the Iris workspace layout.
- `mods/`: the customized Spaces, Agents, Files, and Changes panels.
- `themes/`: the Iris interface and terminal palette.
- `codex-themes/`: the matching Codex syntax theme.
- `fonts/`: Paper Mono and its license.
- `hooks/`: the local Codex and Claude Code subagent lifecycle bridge.
- `scripts/`: local sync and hook installation tools.
- `tests/`: tests for this repository.

The Herdr layout and mods derive from Herdr App, available under the Apache 2.0 license at https://github.com/herdrdev/herdr-app.
Paper Mono is distributed under the SIL Open Font License in `fonts/OFL.txt`.

Customization decisions live in `../docs/` outside this repository.

## Sync

Run `python3 scripts/sync.py` to preview changes and detect drift.
Run `python3 scripts/sync.py --apply` to copy source files to the live configuration.
The script refuses to overwrite live files changed since the last successful sync.
It does not delete live files or change application state.
Validate changed mods with `herdr-app check` and inspect them in Herdr.

## Subagent visibility

The Agents panel can show active Codex and Claude Code subagents beneath their local parent agent.
The integration uses provider lifecycle hooks and the Herdr terminal ID, and does not read or store conversation transcripts.
The state file contains session and agent identifiers, agent types, and the associated terminal ID.
Remote sessions and processes without `HC_TERMINAL_ID` are not supported.
Unexpected termination can leave stale state until the next session starts in that terminal.

Run `python3 scripts/install_subagent_hooks.py` to preview hook installation, then `python3 scripts/install_subagent_hooks.py --apply` to install it without replacing existing hooks.
The hook command points to this repository by absolute path.
After moving the repository, remove the old bridge entries from the provider hook files and rerun the installer.
New provider sessions may be needed to pick up hook changes.
In Codex, review and trust the installed hook in `/hooks` if prompted.

## Verification

Run `python3 -m unittest discover -s tests -v` for the repository tests.
Validate changed mods with `herdr-app check` and inspect them in Herdr.
Real Codex and Claude Code subagent lifecycles should also be checked in active Herdr sessions after hook installation.
