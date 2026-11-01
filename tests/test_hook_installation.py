import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'install_subagent_hooks.py'
spec = importlib.util.spec_from_file_location('install_hooks', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class HookInstallationTests(unittest.TestCase):
    def test_preserves_existing_hooks_and_is_idempotent(self):
        original = {'model': 'example', 'hooks': {'SubagentStart': [{'matcher': 'Explore', 'hooks': [{'type': 'command', 'command': 'existing'}]}]}}
        result = installer.add_hooks(original, 'claude')
        self.assertEqual(len(result), 4)
        self.assertEqual(original['model'], 'example')
        self.assertEqual(original['hooks']['SubagentStart'][0]['hooks'][0]['command'], 'existing')
        snapshot = json.dumps(original, sort_keys=True)
        self.assertEqual(installer.add_hooks(original, 'claude'), [])
        self.assertEqual(json.dumps(original, sort_keys=True), snapshot)

    def test_refuses_to_overwrite_concurrent_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'settings.json'
            target.write_text('{}')
            original, content, _ = installer.prepare(target, 'codex')
            target.write_text('{"changed":true}')
            with self.assertRaises(RuntimeError):
                installer.write(target, original, content)
            self.assertEqual(json.loads(target.read_text()), {'changed': True})

    def test_rejects_invalid_hook_shape(self):
        with self.assertRaises(ValueError):
            installer.add_hooks({'hooks': {'SubagentStop': 'bad'}}, 'codex')

if __name__ == '__main__':
    unittest.main()
