# Agent instructions

This repository contains the Iris layout, themes, mods, and tools for Herdr.
See [README.md](README.md) for setup and an overview.

## Working on changes

- Edit the source files in this repository before syncing to a live Herdr installation.
- Read the installed `~/.config/herdr-app/AGENTS.md` before changing Herdr behavior.
- Do not edit Herdr's generated files, shipped mods, or application-managed layout state.
- Keep Codex and Claude Code support aligned where both providers expose reliable data.
- Do not use em dashes in project writing or interface text.

## Validation

- Run `python3 -m unittest discover -s tests -v` for relevant code changes.
- Run `herdr-app check mods/<mod-name>` for each changed mod, then inspect it in Herdr.
- Run `python3 scripts/sync.py` to preview live changes and `python3 scripts/sync.py --apply` to apply them.
- Do not overwrite live changes that the sync tool reports as conflicts.

## Git

- Do not push to a real remote or a default branch.
- Keep commits small and focused, using `type(scope): summary`.
- `CLAUDE.md` is a symlink to this file; edit `AGENTS.md` to update both.
