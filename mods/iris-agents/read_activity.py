#!/usr/bin/env python3
"""Read a bounded, provider-specific view of a subagent transcript."""
import json
import os
from pathlib import Path
import re
import stat
import sys

MAX_BYTES = 1024 * 1024
MAX_TEXT = 500
MAX_ACTIVITY = 8
UUID = re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z')
AGENT = re.compile(r'[A-Za-z0-9_-]{1,128}\Z')


def clean(value):
    if not isinstance(value, str):
        return None
    value = ' '.join(value.split())
    return value[:MAX_TEXT] if value else None


def open_file(path):
    # Walk from the filesystem root so no component can be replaced by a symlink.
    parts = path.parts
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for index, part in enumerate(parts[1:]):
            flags = os.O_RDONLY | os.O_NOFOLLOW
            if index < len(parts) - 2:
                flags |= os.O_DIRECTORY
            else:
                flags |= os.O_NONBLOCK
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('transcript is not a regular file')
        with os.fdopen(fd, 'rb') as stream:
            fd = -1
            head = stream.read(MAX_BYTES)
            if len(head) < MAX_BYTES:
                return head, b''
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            if size <= MAX_BYTES:
                return head, b''
            if size <= 2 * MAX_BYTES:
                stream.seek(MAX_BYTES)
                return head + stream.read(MAX_BYTES), b''
            start = max(MAX_BYTES, size - MAX_BYTES)
            stream.seek(start - 1)
            return head, stream.read(MAX_BYTES + 1)
    finally:
        if fd >= 0:
            os.close(fd)


def records(data, skip_first=False):
    if skip_first:
        data = data.partition(b'\n')[2]
    # The last record may still be in the process of being written.
    lines = data.split(b'\n')[:-1]
    for line in lines:
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                yield value
        except (ValueError, UnicodeDecodeError, RecursionError):
            continue


def codex_task(root, parent_id, agent_id):
    if not isinstance(parent_id, str) or not UUID.fullmatch(parent_id):
        return None
    # The documented rollout layout has exactly three date directories.
    # More than one match is ambiguous, even if one cannot be read.
    matches = []
    try:
        for path in root.glob('*/*/*/rollout-*-'+parent_id+'.jsonl'):
            matches.append(path)
            if len(matches) > 1:
                return None
        if len(matches) != 1:
            return None
        head, tail = open_file(matches[0])
    except (OSError, ValueError):
        return None
    first = list(records(head))
    rows = first + (list(records(tail, skip_first=True)) if tail else [])
    metadata = [row.get('payload') for row in first if row.get('type') == 'session_meta']
    if len(metadata) != 1 or not isinstance(metadata[0], dict) or metadata[0].get('id') != parent_id:
        return None
    starts = []
    for row in rows:
        payload = row.get('payload')
        if row.get('type') != 'event_msg' or not isinstance(payload, dict):
            continue
        item = payload.get('item')
        if (payload.get('type') == 'item_completed' and isinstance(item, dict)
                and item.get('type') == 'SubAgentActivity' and item.get('kind') == 'started'
                and item.get('agent_thread_id') == agent_id and isinstance(item.get('id'), str)):
            starts.append(item['id'])
    if len(starts) != 1:
        return None
    calls = []
    for row in rows:
        payload = row.get('payload')
        if (row.get('type') == 'response_item' and isinstance(payload, dict)
                and payload.get('type') == 'function_call' and payload.get('name') == 'spawn_agent'
                and payload.get('call_id') == starts[0]):
            calls.append(payload.get('arguments'))
    if len(calls) != 1 or not isinstance(calls[0], str):
        return None
    try:
        arguments = json.loads(calls[0])
    except (ValueError, RecursionError):
        return None
    message = clean(arguments.get('message')) if isinstance(arguments, dict) else None
    # Some Codex runtimes persist the task as an opaque encrypted token.
    return None if message and message.startswith('gAAAAA') else message


def read(provider, transcript, agent_id):
    if provider not in ('codex', 'claude') or not AGENT.fullmatch(agent_id):
        raise ValueError('invalid provider or agent id')
    root = Path.home() / ('.codex/sessions' if provider == 'codex' else '.claude/projects')
    path = Path(transcript)
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(root):
        raise ValueError('invalid transcript path')
    if provider == 'codex':
        if not UUID.fullmatch(agent_id) or not re.fullmatch(r'rollout-.+-' + re.escape(agent_id) + r'\.jsonl', path.name):
            raise ValueError('transcript does not match agent id')
    else:
        if path.suffix != '.jsonl' or path.name.startswith('agent-') or 'subagents' in path.relative_to(root).parts:
            raise ValueError('invalid parent transcript path')
        path = path.parent / path.stem / 'subagents' / ('agent-' + agent_id + '.jsonl')

    head, tail = open_file(path)
    first = list(records(head))
    later = list(records(tail, skip_first=True)) if tail else []
    result = {'task': None, 'activity': [], 'error': None}
    if provider == 'codex':
        meta = next((x.get('payload') for x in first if x.get('type') == 'session_meta'), None)
        if not isinstance(meta, dict) or meta.get('id') != agent_id or not meta.get('parent_thread_id'):
            raise ValueError('transcript identity could not be verified')
        result['task'] = codex_task(root, meta.get('parent_thread_id'), agent_id)
        for row in first + later:
            payload = row.get('payload')
            if row.get('type') != 'event_msg' or not isinstance(payload, dict) or payload.get('type') != 'item_completed' or payload.get('thread_id') != agent_id:
                continue
            item = payload.get('item')
            if not isinstance(item, dict):
                continue
            if item.get('type') == 'CommandExecution':
                parsed = item.get('parsed_cmd')
                commands = [clean(p.get('cmd')) for p in parsed if isinstance(p, dict)] if isinstance(parsed, list) else []
                command = next((c for c in commands if c), None)
                result['activity'].append('ran: ' + command[:160] if command else 'ran a command')
                continue
            if item.get('type') != 'AgentMessage':
                continue
            content = item.get('content')
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') in ('Text', 'text', 'output_text'):
                        text = clean(block.get('text'))
                        if text:
                            result['activity'].append(text)
    else:
        task_seen = False
        for row in first + later:
            if row.get('agentId') != agent_id or row.get('isSidechain') is not True:
                continue
            message = row.get('message')
            if not isinstance(message, dict):
                continue
            content = message.get('content')
            if not task_seen and row.get('type') == 'user' and message.get('role') == 'user':
                task_seen = True
                if row in first and isinstance(content, str):
                    result['task'] = clean(content)
            if row.get('type') == 'assistant' and message.get('role') == 'assistant' and isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        text = clean(block.get('text'))
                        if text:
                            result['activity'].append(text)
    result['activity'] = result['activity'][-MAX_ACTIVITY:]
    return result


def main():
    try:
        if len(sys.argv) != 4:
            raise ValueError('expected provider, transcript path, and agent id')
        result = read(*sys.argv[1:])
    except (OSError, ValueError) as exc:
        result = {'task': None, 'activity': [], 'error': str(exc) if isinstance(exc, ValueError) else 'transcript unavailable'}
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
