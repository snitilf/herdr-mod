import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'hooks' / 'subagent_events.py'
spec = importlib.util.spec_from_file_location('subagent_events', SCRIPT)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def event(kind, session='session-1', **extra):
    return {'hook_event_name': kind, 'session_id': session, **extra}


class LifecycleTests(unittest.TestCase):
    def test_default_type_has_a_concise_label(self):
        for provider in ('codex', 'claude'):
            state = {'version': 1, 'terminals': {}}
            bridge.update(state, provider, 't9', event('SubagentStart', agent_id='a', agent_type='default'))
            self.assertEqual(state['terminals']['t9']['agents']['a']['name'], 'Agent')

    def test_records_transcript_path_without_conversation_content(self):
        state = {'version': 1, 'terminals': {}}
        bridge.update(state, 'codex', 't9', event('SubagentStart', agent_id='a', transcript_path='/example/session.jsonl', prompt='private'))
        self.assertEqual(state['terminals']['t9']['agents']['a']['transcript'], '/example/session.jsonl')
        self.assertNotIn('private', json.dumps(state))

    def test_provider_lifecycle_and_session_isolation(self):
        for provider in ('codex', 'claude'):
            state = {'version': 1, 'terminals': {}}
            bridge.update(state, provider, 't9', event('SessionStart'))
            bridge.update(state, provider, 't9', event('SubagentStart', agent_id='a', agent_type='Explore'))
            self.assertEqual(state['terminals']['t9']['agents'], {'a': {'name': 'Explore'}})
            bridge.update(state, provider, 't9', event('SubagentStop', session='other', agent_id='a'))
            self.assertIn('a', state['terminals']['t9']['agents'])
            bridge.update(state, provider, 't9', event('SubagentStop', agent_id='a', last_assistant_message='private'))
            self.assertEqual(state['terminals']['t9']['agents'], {})
            bridge.update(state, provider, 't9', event('SessionEnd'))
            self.assertEqual(state['terminals'], {})
            self.assertNotIn('private', json.dumps(state))

    def test_inflight_session_and_new_session_replacement(self):
        state = {'version': 1, 'terminals': {}}
        bridge.update(state, 'codex', 't2', event('SubagentStart', agent_id='old', agent_type='Review'))
        bridge.update(state, 'codex', 't2', event('SessionStart', session='new'))
        bridge.update(state, 'codex', 't2', event('SubagentStop', agent_id='old'))
        self.assertEqual(state['terminals']['t2']['session'], 'new')
        self.assertEqual(state['terminals']['t2']['agents'], {})

    def test_new_subagent_replaces_empty_old_session(self):
        state = {'version': 1, 'terminals': {}}
        bridge.update(state, 'codex', 't2', event('SessionStart', session='old'))
        bridge.update(state, 'codex', 't2', event('SubagentStart', session='new', agent_id='a'))
        self.assertEqual(state['terminals']['t2']['session'], 'new')
        self.assertIn('a', state['terminals']['t2']['agents'])

    def test_concurrent_events_are_not_lost(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, HERDR_APP_HOME=tmp, HC_TERMINAL_ID='t5')
            processes = []
            for i in range(15):
                data = json.dumps(event('SubagentStart', agent_id=str(i), agent_type='worker'))
                p = subprocess.Popen([sys.executable, str(SCRIPT), 'claude'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
                p.stdin.write(data)
                p.stdin.close()
                processes.append(p)
            for p in processes:
                self.assertEqual(p.wait(timeout=10), 0)
                self.assertEqual(json.loads(p.stdout.read()), {})
                p.stdout.close()
                p.stderr.close()
            state = json.loads((Path(tmp) / 'data' / 'iris-subagents.json').read_text())
            self.assertEqual(len(state['terminals']['t5']['agents']), 15)

    def test_no_terminal_means_no_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge.record('codex', '../bad', event('SessionStart'), Path(tmp))
            self.assertFalse((Path(tmp) / 'data').exists())

    def test_hexadecimal_terminal_address(self):
        state = {'version': 1, 'terminals': {}}
        bridge.update(state, 'codex', 't1b', event('SubagentStart', agent_id='a', agent_type='default'))
        self.assertEqual(state['terminals']['t1b']['agents']['a']['name'], 'Agent')

if __name__ == '__main__':
    unittest.main()
