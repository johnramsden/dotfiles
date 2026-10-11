#!/usr/bin/python3
"""Exercise the production repository task graph against isolated APT boundaries."""

import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


BOOTSTRAP = Path(__file__).resolve().parents[1]
CANONICAL = BOOTSTRAP / 'tasks/canonical.yml'
CONFIGURE = BOOTSTRAP / 'tasks/configure_external_repos.yml'
INSTALL = BOOTSTRAP / 'tasks/external_repos.yml'

# This module cannot touch system APT. It models the observable repository and
# package effects in the fixture directory, and rejects package operations while
# an obsolete source is still present. Real Ansible still evaluates the original
# conditions, registered results, includes, loops, and host-variable merging.
FAKE_APT_MODULE = '''#!/usr/bin/python3
import json
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule

module = AnsibleModule(argument_spec=dict(
    kind=dict(type='str', required=True, choices=['probe', 'repo', 'apt']),
    state_path=dict(type='path', required=True), root=dict(type='path', required=True),
    argv=dict(type='list', elements='str'), name=dict(type='raw'),
    types=dict(type='list', elements='str'), uris=dict(type='str'),
    suites=dict(type='str'), components=dict(type='list', elements='str'),
    signed_by=dict(type='str'), state=dict(type='str'),
    update_cache=dict(type='bool'), cache_valid_time=dict(type='int'),
    deb=dict(type='str'),
), supports_check_mode=True)
p = module.params
path = Path(p['state_path'])
state = json.loads(path.read_text())
root = Path(p['root'])
kind = p['kind']
if kind == 'probe':
    state['events'].append(['probe', p['argv']])
    path.write_text(json.dumps(state))
    module.exit_json(changed=False, rc=0 if state['probe_ok'] else 1)

if kind == 'repo':
    name = p['name']
    state['events'].append(['repo', name])
    path.write_text(json.dumps(state))
    if name == state['fail_repo']:
        module.fail_json(msg='repository key retrieval failed for ' + name)
    configuration = {key: p[key] for key in ('types', 'uris', 'suites', 'components', 'signed_by')}
    target = root / 'etc/apt/sources.list.d' / (name + '.sources')
    changed = not target.exists() or json.loads(target.read_text()) != configuration
    if changed and not module.check_mode:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(configuration))
    module.exit_json(changed=changed)

# APT must not see duplicate legacy and replacement definitions. In check mode
# the replacement is only predicted; an existing legacy file alone is safe.
for legacy in state['legacy_paths']:
    replacement = root / 'etc/apt/sources.list.d' / (Path(legacy).stem + '.sources')
    if (root / legacy.lstrip('/')).exists() and replacement.exists():
        module.fail_json(msg='APT encountered duplicate source: ' + legacy)
if p['update_cache'] and p['name'] is None:
    event = ['refresh']
elif p['deb'] is not None:
    event = ['deb', p['deb']]
else:
    event = ['packages', p['name']]
state['events'].append(event)
path.write_text(json.dumps(state))
if p['name'] == ['python3-debian', 'ca-certificates'] and not state['probe_ok']:
    module.exit_json(changed=not module.check_mode)
module.exit_json(changed=False)
'''


def fixture_tasks(root, state_path):
    """Retain production tasks and expressions; substitute only unsafe actions."""
    canonical = copy.deepcopy(yaml.safe_load(CANONICAL.read_text()))
    configure = copy.deepcopy(yaml.safe_load(CONFIGURE.read_text()))
    install = copy.deepcopy(yaml.safe_load(INSTALL.read_text()))
    # Include real host vars, but keep all created sources beneath the fixture.
    for task in canonical:
        if 'include_vars' in task:
            task['include_vars'] = task['include_vars'].replace('{{ playbook_dir }}', str(BOOTSTRAP))
        if 'with_first_found' in task:
            task['with_first_found'][0]['files'] = [
                filename.replace('{{ playbook_dir }}', str(BOOTSTRAP))
                for filename in task['with_first_found'][0]['files']]
        if 'include_tasks' in task:
            original = task['include_tasks']
            if original.endswith('/configure_external_repos.yml'):
                task['include_tasks'] = str(root / 'configure.yml')
            elif original.endswith('/external_repos.yml'):
                task['include_tasks'] = str(root / 'install.yml')
    # Run the contiguous var-resolution through package-install sequence. The
    # workspace task is unrelated; all other new actions must be isolated here.
    names = [task['name'] for task in canonical]
    selected = [task for task in canonical[
        names.index('Load Ubuntu base vars'):names.index('Setup external APT repositories') + 1]
        if task['name'] != 'Create Canonical workspace directory']

    def isolate(tasks):
        for task in tasks:
            task.pop('become', None)
            if 'ansible.builtin.command' in task:
                args = task.pop('ansible.builtin.command')
                task['fake_apt_boundary'] = dict(args, kind='probe')
            elif 'ansible.builtin.deb822_repository' in task:
                args = task.pop('ansible.builtin.deb822_repository')
                task['fake_apt_boundary'] = dict(args, kind='repo')
            elif 'ansible.builtin.apt' in task or 'apt' in task:
                args = task.pop('ansible.builtin.apt', None)
                if args is None:
                    args = task.pop('apt')
                task['fake_apt_boundary'] = dict(args, kind='apt')
            elif 'ansible.builtin.file' in task:
                args = task['ansible.builtin.file']
                assert args['state'] == 'absent' and args['path'] == '{{ item.1 }}'
                args['path'] = '{{ sandbox_root }}{{ item.1 }}'
            elif not any(key in task for key in ('ansible.builtin.assert', 'include_tasks',
                                                   'include_vars', 'set_fact')):
                raise AssertionError(f'unisolated task: {task}')
            if 'fake_apt_boundary' in task:
                task['fake_apt_boundary'].update(state_path=str(state_path), root=str(root))

    for tasks, filename in ((selected, 'canonical.yml'), (configure, 'configure.yml'),
                            (install, 'install.yml')):
        isolate(tasks)
        (root / filename).write_text(yaml.safe_dump(tasks, sort_keys=False))
    return [{'name': 'Repository migration integration', 'hosts': 'localhost',
             'connection': 'local', 'gather_facts': False, 'become': False,
             'vars': {'ansible_facts': {'hostname': '{{ test_hostname }}',
                                        'distribution_release': 'noble',
                                        'python': {'executable': '/usr/bin/python3'}},
                      'sandbox_root': str(root),
                      'ansible_python_interpreter': '/usr/bin/python3'},
             'tasks': [{'include_tasks': str(root / 'canonical.yml')}]}]


class RepositoryMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='repository-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state_path = self.root / 'state.json'
        self.library = self.root / 'library'
        self.library.mkdir()
        (self.library / 'fake_apt_boundary.py').write_text(FAKE_APT_MODULE)
        self.fixture = self.root / 'playbook.yml'
        self.fixture.write_text(yaml.safe_dump(fixture_tasks(self.root, self.state_path),
                                               sort_keys=False))

    def source(self, name, suffix='.list'):
        return self.root / 'etc/apt/sources.list.d' / (name + suffix)

    def create_source(self, name, suffix='.list', content='legacy source'):
        path = self.source(name, suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def execute(self, *, hostname='corp', legacy=(), fail_repo=None, probe_ok=True,
                check=False, extra_vars=None, reset=True):
        if reset:
            self.state_path.write_text(json.dumps({
                'events': [], 'legacy_paths': [f'/etc/apt/sources.list.d/{name}.list'
                                               for name in legacy],
                'probe_ok': probe_ok, 'fail_repo': fail_repo}))
        else:
            state = json.loads(self.state_path.read_text())
            state['events'] = []
            state['fail_repo'] = fail_repo
            self.state_path.write_text(json.dumps(state))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', ANSIBLE_INJECT_FACT_VARS='False',
                   ANSIBLE_LIBRARY=str(self.library), ANSIBLE_LOCAL_TEMP=str(self.root / 'tmp'),
                   ANSIBLE_NOCOLOR='1', ANSIBLE_HOST_KEY_CHECKING='False')
        variables = dict(test_hostname=hostname, **(extra_vars or {}))
        command = ['/usr/bin/ansible-playbook', '-i', 'localhost,', str(self.fixture),
                   '--extra-vars', json.dumps(variables)]
        if check:
            command.append('--check')
        result = subprocess.run(command, env=env, text=True, capture_output=True,
                                timeout=90, check=False)
        return result, json.loads(self.state_path.read_text())['events']

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_first_migration_removes_only_declared_sources_before_apt(self):
        old = self.create_source('mattermost-desktop')
        old_jeyboard = self.create_source('jeyboard')
        unrelated = self.create_source('unmanaged')
        keyring = self.root / 'etc/apt/keyrings/custom.gpg'
        keyring.parent.mkdir(parents=True)
        keyring.write_text('keep key')
        result, events = self.execute(hostname='corpo', legacy=('mattermost-desktop', 'jeyboard'))
        self.assert_success(result)
        self.assertFalse(old.exists())
        self.assertFalse(old_jeyboard.exists())
        self.assertTrue(unrelated.exists())
        self.assertEqual(keyring.read_text(), 'keep key')
        self.assertEqual(json.loads(self.source('mattermost-desktop', '.sources').read_text())['uris'],
                         'https://deb.packages.mattermost.com')
        self.assertEqual(json.loads(self.source('jeyboard', '.sources').read_text())['suites'],
                         'noble')
        self.assertLess(events.index(['repo', 'mattermost-desktop']), events.index(['refresh']))
        self.assertLess(events.index(['repo', 'jeyboard']), events.index(['refresh']))
        self.assertLess(events.index(['refresh']),
                        next(i for i, event in enumerate(events) if event[0] == 'packages'))
        self.assertIn(['packages', 'mattermost-desktop'], events)
        self.assertIn(['packages', 'gnome-shell-extension-jeyboard'], events)

    def test_second_run_does_not_refresh_unchanged_repositories(self):
        self.assert_success(self.execute()[0])
        result, events = self.execute(reset=False)
        self.assert_success(result)
        self.assertNotIn(['refresh'], events)
        self.assertIn(['repo', 'mattermost-desktop'], events)

    def test_failed_key_retrieval_preserves_legacy_and_never_runs_apt(self):
        old = self.create_source('mattermost-desktop')
        result, events = self.execute(legacy=('mattermost-desktop',), fail_repo='mattermost-desktop')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('repository key retrieval failed', result.stdout + result.stderr)
        self.assertEqual(old.read_text(), 'legacy source')
        self.assertFalse(self.source('mattermost-desktop', '.sources').exists())
        self.assertEqual([event[0] for event in events], ['probe', 'repo'])

    def test_later_key_failure_preserves_every_legacy_source(self):
        mattermost = self.create_source('mattermost-desktop')
        jeyboard = self.create_source('jeyboard')
        result, events = self.execute(hostname='corpo', legacy=('mattermost-desktop', 'jeyboard'),
                                      fail_repo='jeyboard')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('repository key retrieval failed for jeyboard', result.stdout + result.stderr)
        self.assertEqual(mattermost.read_text(), 'legacy source')
        self.assertEqual(jeyboard.read_text(), 'legacy source')
        self.assertTrue(self.source('mattermost-desktop', '.sources').exists())
        self.assertEqual([event[0] for event in events], ['probe', 'repo', 'repo'])

    def test_restarted_migration_repairs_coexisting_sources_before_apt(self):
        old = self.create_source('mattermost-desktop')
        self.create_source('mattermost-desktop', '.sources', '{}')
        result, events = self.execute(legacy=('mattermost-desktop',))
        self.assert_success(result)
        self.assertFalse(old.exists())
        self.assertEqual(json.loads(self.source('mattermost-desktop', '.sources').read_text())['suites'],
                         'stable')
        self.assertIn(['refresh'], events)
        self.assertIn(['packages', 'mattermost-desktop'], events)

    def test_corpo_only_uses_jeyboard_repository_and_binary_package(self):
        for host in ('corp', 'can', 'kiwi', 'unknown', 'corpo'):
            with self.subTest(host=host):
                result, events = self.execute(hostname=host)
                self.assert_success(result)
                self.assertEqual(['repo', 'jeyboard'] in events, host == 'corpo')
                self.assertEqual(['packages', 'gnome-shell-extension-jeyboard'] in events,
                                 host == 'corpo')
                self.assertIn(['repo', 'mattermost-desktop'], events)
                self.assertEqual(self.source('jeyboard', '.sources').exists(), host == 'corpo')
                if host == 'corpo':
                    self.assertEqual(json.loads(self.source('jeyboard', '.sources').read_text())['suites'],
                                     'noble')

    def test_direct_debs_are_installed_even_without_repositories(self):
        result, events = self.execute(extra_vars={
            'base_external_repos': [], 'base_external_debs': [],
            'extra_external_debs': [{'name': 'custom', 'deb_url': 'https://example.test/custom.deb'}]})
        self.assert_success(result)
        self.assertIn(['deb', 'https://example.test/custom.deb'], events)
        self.assertNotIn('repo', [event[0] for event in events])
        self.assertNotIn(['refresh'], events)

    def test_missing_deb822_library_installs_prerequisites_before_repository(self):
        result, events = self.execute(probe_ok=False)
        self.assert_success(result)
        self.assertLess(events.index(['packages', ['python3-debian', 'ca-certificates']]),
                        events.index(['repo', 'mattermost-desktop']))

    def test_missing_library_with_non_system_python_fails_before_apt(self):
        interpreter = '/tmp/venv/bin/python3'
        result, events = self.execute(probe_ok=False, extra_vars={
            'ansible_facts': {'hostname': 'corp', 'distribution_release': 'noble',
                              'python': {'executable': interpreter}}})
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Install the Python debian library into ' + interpreter,
                      result.stdout + result.stderr)
        self.assertEqual(events, [['probe', [interpreter, '-c', 'import debian.deb822']]])
        self.assertFalse(self.source('mattermost-desktop', '.sources').exists())

    def test_check_mode_leaves_existing_sources_untouched(self):
        old = self.create_source('mattermost-desktop')
        result, events = self.execute(legacy=('mattermost-desktop',), check=True)
        self.assert_success(result)
        self.assertEqual(old.read_text(), 'legacy source')
        self.assertFalse(self.source('mattermost-desktop', '.sources').exists())


if __name__ == '__main__':
    unittest.main()
