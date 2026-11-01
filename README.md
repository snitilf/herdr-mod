# Iris for Herdr

Iris is a dark workspace for [Herdr](https://github.com/herdrdev/herdr-app) with pastel blue colors.
It includes custom sidebars and a matching terminal palette.
It also includes tools to work across repositories.
A repository holds a project and its Git history.

## Features

Iris includes these components:

- An Iris theme for the interface and terminal, plus a matching Codex theme.
- Custom sidebars for spaces and agents, with active subagents under their local parent.
- Files and changes grouped by repository, even when the selected folder is not a repository.
- Paper Mono, a monospaced font.

A subagent is an agent that another agent starts.
The subagent view supports local Codex and Claude Code sessions.

## Setup

Install Herdr and Python 3.
Clone this repository.
In the repository directory, preview the files that the sync tool will copy:

```sh
python3 scripts/sync.py
```

If the preview reports no conflicts, copy the files to the local Herdr configuration:

```sh
python3 scripts/sync.py --apply
```

A conflict means that a live file changed outside the repository.
The sync tool stops if it finds a conflict.
It does not delete live files or change the active layout.
It excludes Python caches, which hold temporary Python files.

Select the layout in Herdr, or run this command:

```sh
herdr-app do layout.switch '{"name":"iris-workspace"}'
```

The layout uses the Iris theme.
The sync tool also copies the Codex theme and font files.
It does not select the Codex theme or install a system font.

## Files and changes

Files and Changes use the same selected folder for each tab.
The tools search up to three folder levels for repositories.
They skip hidden folders and common dependency folders.
A dependency folder contains files that a project needs to run or build.

## Subagents

A hook is a command that runs when an event occurs.
The hooks in this repository report when Codex and Claude Code subagents start and stop.
In the repository directory, preview the hook installation:

```sh
python3 scripts/install_subagent_hooks.py
```

Install the hooks:

```sh
python3 scripts/install_subagent_hooks.py --apply
```

The installer adds the hooks and keeps existing hooks.
Start a new agent session to load the changes.
If Codex asks you to review the hooks, use `/hooks`.

The hook commands use the absolute path to this repository.
If you move the repository, remove the old bridge entries from the hook files.
Run the installer again after you remove the old entries.
A bridge is the code that passes information to the Agents sidebar.

Click a Codex or Claude Code subagent to view its task and recent recorded activity.
The view can show progress messages and completed commands.
The providers do not always supply all details.
For example, Codex can store a task in encrypted form, so the view cannot display it.

The bridge supports local Herdr sessions that supply `HC_TERMINAL_ID`.
The bridge stores session IDs, agent IDs, agent types, terminal IDs, and transcript paths in a local state file.
A transcript is a record of an agent session.
The activity view reads the selected local transcript.
It does not copy the transcript into the state file.
If a session exits unexpectedly, old state can remain until a new session starts in that terminal.

## Development

A mod is a custom Herdr component.
In the repository directory, run the tests:

```sh
python3 -m unittest discover -s tests -v
```

For each changed mod, run `herdr-app check mods/<mod-name>`.
Inspect the result in Herdr.
The workspace includes custom copies of Herdr components.
These include the chrome, status bar, tabs, pane header, menus, and picker.
Chrome is the set of controls around the workspace.
The copies do not receive updates to the original Herdr components.
When you update Herdr, review the copies.
See [AGENTS.md](AGENTS.md) for repository instructions.

## Credits

The layout and mods build on [Herdr App](https://github.com/herdrdev/herdr-app).
Herdr App is available under the Apache 2.0 license.
Paper Mono is distributed under the SIL Open Font License.
See [fonts/OFL.txt](fonts/OFL.txt) for the font license.
