import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'sync.py'
spec = importlib.util.spec_from_file_location('herdr_sync', SCRIPT)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.source = root / 'source'
        self.live = root / 'live'
        self.codex = root / 'codex'
        for folder in ('layouts', 'themes', 'mods', 'fonts', 'codex-themes'):
            (self.source / folder).mkdir(parents=True)
        self.asset = self.source / 'themes' / 'iris.json'
        self.asset.write_text('original')
        self.target = self.live / 'themes' / 'iris.json'
        self.patches = [patch.object(sync, 'ROOT', self.source), patch.object(sync, 'HERDR', self.live), patch.object(sync, 'CODEX', self.codex), patch.object(sync, 'MANIFEST', self.source / '.sync-state.json')]
        for p in self.patches:
            p.start()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])

    def run_sync(self, *args):
        with patch.object(sys, 'argv', ['sync.py', *args]), contextlib.redirect_stdout(io.StringIO()):
            return sync.main()

    def test_apply_and_update_unchanged_live_file(self):
        self.assertEqual(self.run_sync('--apply'), 0)
        self.asset.write_text('updated')
        self.assertEqual(self.run_sync('--apply'), 0)
        self.assertEqual(self.target.read_text(), 'updated')

    def test_drift_prevents_all_copies(self):
        self.assertEqual(self.run_sync('--apply'), 0)
        self.asset.write_text('source update')
        self.target.write_text('live update')
        other = self.source / 'layouts' / 'new.json'
        other.write_text('{}')
        self.assertEqual(self.run_sync('--apply'), 1)
        self.assertEqual(self.target.read_text(), 'live update')
        self.assertFalse((self.live / 'layouts' / 'new.json').exists())

    def test_initial_conflict_does_not_overwrite(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('existing')
        self.assertEqual(self.run_sync('--apply'), 1)
        self.assertEqual(self.target.read_text(), 'existing')

    def test_python_cache_is_not_synced(self):
        cache = self.source / 'mods' / 'iris-agents' / '__pycache__' / 'reader.pyc'
        cache.parent.mkdir(parents=True)
        cache.write_bytes(b'cached')
        self.assertEqual(self.run_sync('--apply'), 0)
        self.assertFalse((self.live / 'mods' / 'iris-agents' / '__pycache__').exists())

if __name__ == '__main__':
    unittest.main()
