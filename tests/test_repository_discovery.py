import ast
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def scan_script(path, name):
    for line in path.read_text().splitlines():
        if line.strip().startswith(f'const {name} = '):
            return ast.literal_eval(line.strip()[len(f'const {name} = '):-1])
    raise AssertionError('missing discovery script')


class RepositoryDiscoveryTests(unittest.TestCase):
    def test_nested_repositories_and_worktree_markers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'workspace with spaces'
            for relative, is_file in [('repo one', False), ('group/deep-repo', False), ('group/worktree', True), ('node_modules/ignored', False), ('.hidden/ignored', False), ('one/two/three/four/too-deep', False)]:
                marker = root / relative / '.git'
                marker.parent.mkdir(parents=True, exist_ok=True)
                if is_file:
                    marker.write_text('gitdir: /tmp/example')
                else:
                    marker.mkdir()
            expected = {str(root / name / '.git') for name in ('repo one', 'group/deep-repo', 'group/worktree')}
            for path, variable in [('mods/iris-repositories/main.js', 'script'), ('mods/iris-files/main.js', 'discover')]:
                script = scan_script(ROOT / path, variable)
                output = subprocess.check_output(['sh', '-c', script, 'scan', str(root)])
                self.assertEqual(set(output.decode().split('\0')) - {''}, expected)

if __name__ == '__main__':
    unittest.main()
