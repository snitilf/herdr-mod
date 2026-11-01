#!/usr/bin/env python3
"""Record local subagent lifecycle events without storing prompts or transcripts."""
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile

VALID_TERMINAL = re.compile(r'^t[0-9a-f]+$')
EVENTS = {'SessionStart', 'SessionEnd', 'SubagentStart', 'SubagentStop'}


def update(state, provider, terminal, event):
    """Apply one event to a state object. Unknown or incomplete events are ignored."""
    if provider not in ('codex', 'claude') or not VALID_TERMINAL.fullmatch(terminal or ''):
        return state
    if not isinstance(event, dict):
        return state
    kind = event.get('hook_event_name')
    session = event.get('session_id')
    if kind not in EVENTS or not isinstance(session, str) or not session or len(session) > 200:
        return state
    if kind == 'SessionStart' and event.get('agent_id'):
        return state
    terminals = state.setdefault('terminals', {})
    current = terminals.get(terminal)
    if kind == 'SessionStart':
        if not current or current.get('session') != session or current.get('provider') != provider:
            terminals[terminal] = {'provider': provider, 'session': session, 'agents': {}}
        return state
    if kind == 'SubagentStart' and (not current or (
        not current.get('agents') and (current.get('session') != session or current.get('provider') != provider)
    )):
        current = {'provider': provider, 'session': session, 'agents': {}}
        terminals[terminal] = current
    if not current or current.get('session') != session or current.get('provider') != provider:
        return state
    if kind == 'SessionEnd':
        del terminals[terminal]
        return state
    agent = event.get('agent_id')
    if not isinstance(agent, str) or not agent or len(agent) > 200:
        return state
    agents = current.setdefault('agents', {})
    if kind == 'SubagentStart':
        name = event.get('agent_type')
        if not isinstance(name, str) or not name.strip():
            name = 'Subagent'
        name = ''.join(c if c.isprintable() else ' ' for c in name).strip()[:80] or 'Subagent'
        if name.casefold() == 'default':
            name = 'Agent'
        child = {'name': name}
        transcript = event.get('transcript_path')
        if isinstance(transcript, str) and transcript and len(transcript) <= 4096:
            child['transcript'] = transcript
        agents[agent] = child
    elif kind == 'SubagentStop':
        agents.pop(agent, None)
    return state


def record(provider, terminal, event, app_home):
    if provider not in ('codex', 'claude') or not VALID_TERMINAL.fullmatch(terminal or ''):
        return
    if not isinstance(event, dict) or event.get('hook_event_name') not in EVENTS:
        return
    folder = app_home / 'data'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'iris-subagents.json'
    with (folder / 'iris-subagents.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = json.loads(target.read_text()) if target.exists() else {'version': 1, 'terminals': {}}
            if not isinstance(state, dict) or state.get('version') != 1 or not isinstance(state.get('terminals'), dict):
                return
            updated = update(state, provider, terminal, event)
            fd, name = tempfile.mkstemp(prefix='.iris-subagents-', dir=folder)
            try:
                with os.fdopen(fd, 'w') as out:
                    json.dump(updated, out, separators=(',', ':'))
                os.replace(name, target)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def main():
    # A hook must never block or inject text into the agent session.
    try:
        event = json.load(sys.stdin)
        provider = sys.argv[1] if len(sys.argv) > 1 else ''
        app_home = Path(os.environ.get('HERDR_APP_HOME') or Path.home() / '.config/herdr-app')
        record(provider, os.environ.get('HC_TERMINAL_ID', ''), event, app_home)
    except Exception:
        pass
    print('{}')


if __name__ == '__main__':
    main()
