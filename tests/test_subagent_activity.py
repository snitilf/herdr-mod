import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'mods/iris-agents/read_activity.py'
ID = '01234567-89ab-cdef-0123-456789abcdef'


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.env = dict(os.environ, HOME=str(self.home))

    def invoke(self, provider, path, agent=ID):
        process = subprocess.run([sys.executable, str(SCRIPT), provider, str(path), agent],
                                 env=self.env, capture_output=True, text=True, check=True)
        self.assertEqual(process.stderr, '')
        return json.loads(process.stdout)

    def write(self, path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def codex(self):
        return self.home / '.codex/sessions/2026/01/01' / ('rollout-2026-01-01-' + ID + '.jsonl')

    def test_codex_only_thread_specific_completed_activity(self):
        path = self.codex()
        self.write(path, [
            {'type': 'session_meta', 'payload': {'id': ID, 'parent_thread_id': 'parent'}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': 'inherited secret'}},
            {'type': 'response_item', 'payload': {'type': 'reasoning', 'encrypted_content': 'encrypted secret'}},
            {'type': 'event_msg', 'payload': {'type': 'item_completed', 'thread_id': 'other', 'item': {'type': 'AgentMessage', 'content': [{'type': 'text', 'text': 'other secret'}]}}},
            {'type': 'event_msg', 'payload': {'type': 'item_completed', 'thread_id': ID, 'item': {'type': 'CommandExecution', 'parsed_cmd': [{'cmd': 'ls src'}], 'aggregated_output': 'private output'}}},
            {'type': 'event_msg', 'payload': {'type': 'item_completed', 'thread_id': ID, 'item': {'type': 'AgentMessage', 'content': [{'type': 'Text', 'text': 'Working on it'}]}}},
        ])
        self.assertEqual(self.invoke('codex', path), {'task': None, 'activity': ['ran: ls src', 'Working on it'], 'error': None})

    def test_record_crossing_read_boundary_is_not_lost(self):
        path = self.codex()
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = json.dumps({'type': 'session_meta', 'payload': {'id': ID, 'parent_thread_id': 'parent'}}) + '\n'
        padding = json.dumps({'padding': 'x' * (1024 * 1024 - len(meta) - 30)}) + '\n'
        activity = {'type': 'event_msg', 'payload': {'type': 'item_completed', 'thread_id': ID, 'item': {'type': 'AgentMessage', 'content': [{'type': 'Text', 'text': 'Boundary activity'}]}}}
        path.write_text(meta + padding + json.dumps(activity) + '\n')
        self.assertEqual(self.invoke('codex', path)['activity'], ['Boundary activity'])

    def test_codex_task_requires_exact_parent_call_association(self):
        parent_id = '11111111-2222-3333-4444-555555555555'
        child = self.codex()
        parent = child.parent / ('rollout-2026-01-01-' + parent_id + '.jsonl')
        self.write(child, [{'type': 'session_meta', 'payload': {'id': ID, 'parent_thread_id': parent_id}}])
        metadata = {'type': 'session_meta', 'payload': {'id': parent_id}}
        start = {'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': {'type': 'SubAgentActivity', 'kind': 'started', 'agent_thread_id': ID, 'id': 'call-1'}}}
        call = {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'spawn_agent', 'call_id': 'call-1', 'arguments': json.dumps({'message': 'Child task'})}}
        self.write(parent, [metadata, start, call])
        self.assertEqual(self.invoke('codex', child)['task'], 'Child task')
        encrypted = {'type': 'response_item', 'payload': dict(call['payload'], arguments=json.dumps({'message': 'gAAAAAopaque-token'}))}
        self.write(parent, [metadata, start, encrypted])
        self.assertIsNone(self.invoke('codex', child)['task'])
        wrong_call = {'type': 'response_item', 'payload': dict(call['payload'], call_id='wrong')}
        self.write(parent, [metadata, start, wrong_call])
        self.assertIsNone(self.invoke('codex', child)['task'])
        wrong_start = {'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': dict(start['payload']['item'], agent_thread_id='other')}}
        self.write(parent, [metadata, wrong_start, call])
        self.assertIsNone(self.invoke('codex', child)['task'])
        self.write(parent, [metadata, start, call, call])
        self.assertIsNone(self.invoke('codex', child)['task'])
        self.write(parent, [{'type': 'session_meta', 'payload': {'id': ID}}, start, call])
        self.assertIsNone(self.invoke('codex', child)['task'])
        self.write(parent, [metadata, start, call])
        duplicate = self.home / '.codex/sessions/2025/01/01' / parent.name
        self.write(duplicate, [metadata, start, call])
        self.assertIsNone(self.invoke('codex', child)['task'])

    def test_codex_parent_symlink_does_not_disclose_task(self):
        parent_id = '11111111-2222-3333-4444-555555555555'
        child = self.codex()
        self.write(child, [{'type': 'session_meta', 'payload': {'id': ID, 'parent_thread_id': parent_id}}])
        parent = child.parent / ('rollout-2026-01-01-' + parent_id + '.jsonl')
        target = self.home / 'private'
        target.write_text('secret')
        parent.symlink_to(target)
        self.assertIsNone(self.invoke('codex', child)['task'])

    def test_claude_child_and_partial_line(self):
        parent = self.home / '.claude/projects/project/session.jsonl'
        child = parent.parent / parent.stem / 'subagents/agent-a1.jsonl'
        self.write(child, [
            {'agentId': 'a1', 'isSidechain': True, 'type': 'user', 'message': {'role': 'user', 'content': 'Fix the thing'}},
            {'agentId': 'a1', 'isSidechain': True, 'type': 'assistant', 'message': {'role': 'assistant', 'content': [{'type': 'thinking', 'thinking': 'private'}, {'type': 'text', 'text': 'Inspecting files'}]}},
            {'agentId': 'other', 'isSidechain': True, 'type': 'assistant', 'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': 'wrong'}]}},
        ])
        with child.open('a') as stream:
            stream.write('{"unfinished":')
        self.assertEqual(self.invoke('claude', parent, 'a1'), {'task': 'Fix the thing', 'activity': ['Inspecting files'], 'error': None})

    def test_wrong_identity_missing_and_traversal_fail_closed(self):
        path = self.codex()
        self.write(path, [{'type': 'session_meta', 'payload': {'id': 'wrong', 'parent_thread_id': 'parent'}}])
        self.assertIsNotNone(self.invoke('codex', path)['error'])
        self.assertIsNotNone(self.invoke('codex', path, 'other')['error'])
        self.assertIsNotNone(self.invoke('codex', path.parent / '..' / path.name)['error'])
        self.assertIsNotNone(self.invoke('claude', self.home / '.claude/projects/a.jsonl', '../bad')['error'])
        self.assertIsNotNone(self.invoke('claude', self.home / '.claude/projects/a.jsonl', 'a')['error'])

    def test_symlink_component_and_leaf_are_rejected(self):
        path = self.codex()
        path.parent.mkdir(parents=True)
        target = self.home / 'target'
        target.write_text('secret')
        path.symlink_to(target)
        self.assertIsNotNone(self.invoke('codex', path)['error'])
        parent = self.home / '.claude/projects/project/session.jsonl'
        parent.parent.mkdir(parents=True)
        (parent.parent / 'session').symlink_to(self.home, target_is_directory=True)
        self.assertIsNotNone(self.invoke('claude', parent, 'a')['error'])

    def test_activity_and_text_are_bounded(self):
        path = self.codex()
        rows = [{'type': 'session_meta', 'payload': {'id': ID, 'parent_thread_id': 'parent'}}]
        rows += [{'type': 'event_msg', 'payload': {'type': 'item_completed', 'thread_id': ID, 'item': {'type': 'AgentMessage', 'content': [{'type': 'text', 'text': str(i) * 1000}]}}} for i in range(12)]
        self.write(path, rows)
        result = self.invoke('codex', path)
        self.assertEqual(len(result['activity']), 8)
        self.assertTrue(all(len(text) <= 500 for text in result['activity']))


if __name__ == '__main__':
    unittest.main()
