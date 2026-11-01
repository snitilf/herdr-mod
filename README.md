# Iris for Herdr

A dark, pastel-blue workspace for [Herdr](https://github.com/herdrdev/herdr-app), with a matching terminal palette, custom sidebars, and tools for working across repositories.

## Features

- **Iris theme:** a dark interface and terminal palette, plus a matching Codex theme.
- **Spaces and agents:** custom sidebars with nested active subagents for local Codex and Claude Code sessions.
- **Files and changes:** browse a folder and see changes grouped by repository, even when the folder itself is not a repository.
- **Paper Mono:** a monospaced font included with the workspace.

## Setup

Install Herdr and Python 3, then clone this repository.
From the repository directory, preview and copy the files into your local Herdr configuration:

```sh
python3 scripts/sync.py
python3 scripts/sync.py --apply
```

Select the layout in Herdr, or run:

```sh
herdr-app do layout.switch '{"name":"iris-workspace"}'
```

The layout uses the Iris theme.
The sync also copies the matching Codex theme and font files, but does not select the Codex theme or install a system font.

The sync tool checks for changes made directly to live files and stops if it finds a conflict.
It does not delete live files or change the active layout.

## Subagents

To show active Codex and Claude Code subagents in the Agents sidebar, preview and install the hooks:

```sh
python3 scripts/install_subagent_hooks.py
python3 scripts/install_subagent_hooks.py --apply
```

The installer adds hooks without replacing existing ones.
Start a new agent session to pick up changes and review the hooks in Codex with `/hooks` if prompted.
The hooks refer to this checkout by its absolute path, so remove the old bridge entries and rerun the installer if you move it.

The sidebar shows activity and agent types, but does not open a subagent's conversation.
It supports local Herdr sessions that provide `HC_TERMINAL_ID`.
The bridge stores session and agent IDs, agent types, and terminal IDs in a local state file.
It does not store conversation transcripts.
An unexpected exit can leave stale state until a new session starts in that terminal.

## Development

Run the tests with:

```sh
python3 -m unittest discover -s tests -v
```

Check a changed mod with `herdr-app check mods/<mod-name>` and inspect it in Herdr.
See [AGENTS.md](AGENTS.md) for repository instructions.

## Credits

The layout and mods build on [Herdr App](https://github.com/herdrdev/herdr-app), which is available under the Apache 2.0 license.
Paper Mono is distributed under the SIL Open Font License; see [fonts/OFL.txt](fonts/OFL.txt).
