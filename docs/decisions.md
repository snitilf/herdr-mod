# Herdr customization decisions

## Source of truth

`~/Documents/herdr/src` owns the personal Herdr layout, mods, themes, and Codex syntax theme.
From `~/Documents/herdr/src`, use `scripts/sync.py` to compare and `scripts/sync.py --apply` to publish those files locally.
The sync refuses to overwrite a live file changed since the last successful sync.
It does not delete live files or synchronize application state.

## Parent folders and agents

When the active working folder contains several repositories, the interface should show all detected repositories and their changes grouped by repository.
Each file and operation must remain associated with its own repository.
Subagents should appear under their parent with a visible count when the provider exposes reliable parent and lifecycle information.
Support Codex and Claude Code without presenting inferred or stale activity as live state.
