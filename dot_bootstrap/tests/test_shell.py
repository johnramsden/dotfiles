#!/usr/bin/python3
"""Exercise setup.yml's shell block with isolated account-provider boundaries."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


SETUP = Path(__file__).resolve().parents[1] / "setup.yml"
USERNAME = "first.last@example.com"
ZSH = "/usr/bin/zsh"
BASH = "/bin/bash"

# The fixture module has no system account operations. All changes are confined to
# the per-test JSON state file; the original block's conditions/assertions still run.
FAKE_ACCOUNT_MODULE = '''#!/usr/bin/python3
import json
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule

module = AnsibleModule(argument_spec=dict(
    kind=dict(type='str', required=True, choices=['getent', 'user', 'command']),
    state_path=dict(type='path', required=True),
    database=dict(type='str'), key=dict(type='str'), service=dict(type='str'),
    fail_key=dict(type='bool'), name=dict(type='str'), shell=dict(type='str'),
    argv=dict(type='list', elements='str'),
), supports_check_mode=True)
p = module.params
path = Path(p['state_path'])
state = json.loads(path.read_text())
events = state['events']

if p['kind'] == 'getent':
    service = p['service']
    events.append(['getent', service, p['key']])
    path.write_text(json.dumps(state))
    if service == 'authd' and not state['authd_available']:
        module.fail_json(msg='authd service unavailable')
    module.exit_json(changed=False, ansible_facts={
        'getent_passwd': {p['key']: state['accounts'][service].get(p['key'])}
    })

if p['kind'] == 'user':
    name = p['name']
    events.append(['user', name, p['shell']])
    if name not in state['accounts']['files']:
        path.write_text(json.dumps(state))
        module.fail_json(msg='refusing to create a local user')
    record = state['accounts']['files'][name]
    changed = record[5] != p['shell']
    if changed and not module.check_mode:
        record[5] = p['shell']
    path.write_text(json.dumps(state))
    module.exit_json(changed=changed)

argv = p['argv']
events.append(['authctl', argv])
path.write_text(json.dumps(state))
if module.check_mode:
    module.exit_json(skipped=True, changed=False, msg='command skipped in check mode')
if state['authctl_fail']:
    module.fail_json(msg='authctl rejected shell update')
if len(argv) != 5 or argv[:3] != ['authctl', 'user', 'set-shell']:
    module.fail_json(msg='unexpected authctl invocation')
if argv[3] not in state['accounts']['authd']:
    module.fail_json(msg='authd account missing')
record = state['accounts']['authd'][argv[3]]
changed = record[5] != argv[4]
record[5] = argv[4]
path.write_text(json.dumps(state))
module.exit_json(changed=changed)
'''


def account(shell):
    # getent_passwd entries omit the username; the sixth field is the shell.
    return ["x", "1001", "1001", "Test User", "/home/test", shell]


def shell_tasks(state_path):
    play = yaml.safe_load(SETUP.read_text())[0]
    (shell_block,) = [task for task in play['tasks'] if task.get('name') == 'Configure default shell']
    block = json.loads(json.dumps(shell_block))
    actions = {'ansible.builtin.getent': 'getent',
               'ansible.builtin.user': 'user',
               'ansible.builtin.command': 'command'}

    def isolate(tasks):
        for task in tasks:
            task.pop('become', None)
            if 'block' in task:
                isolate(task['block'])
            else:
                found = [action for action in actions if action in task]
                if found:
                    (action,) = found
                    task['fake_account'] = dict(task.pop(action), kind=actions[action],
                                                state_path=str(state_path))
                elif 'ansible.builtin.assert' not in task:
                    raise AssertionError(f'unisolated task: {task}')

    isolate(block['block'])
    return [{'name': 'Shell account provider integration', 'hosts': 'localhost',
             'connection': 'local', 'gather_facts': False, 'become': False,
             'vars': {'ansible_facts': {'user_id': USERNAME},
                      'ansible_python_interpreter': '/usr/bin/python3'},
             'tasks': [block]}]


class ShellProviderTests(unittest.TestCase):
    def run_shell(self, *, local=None, authd=None, available=True, authctl_fail=False,
                  check=False):
        with tempfile.TemporaryDirectory(prefix='shell-provider-test-') as directory:
            root = Path(directory)
            state_path = root / 'accounts.json'
            state_path.write_text(json.dumps({
                'accounts': {'files': {USERNAME: account(local)} if local else {},
                             'authd': {USERNAME: account(authd)} if authd else {}},
                'authd_available': available, 'authctl_fail': authctl_fail,
                'events': [],
            }))
            library = root / 'library'
            library.mkdir()
            (library / 'fake_account.py').write_text(FAKE_ACCOUNT_MODULE)
            fixture = root / 'playbook.yml'
            fixture.write_text(yaml.safe_dump(shell_tasks(state_path), sort_keys=False))
            env = dict(os.environ, ANSIBLE_INJECT_FACT_VARS='False',
                       ANSIBLE_LIBRARY=str(library), ANSIBLE_LOCAL_TEMP=str(root / 'tmp'),
                       ANSIBLE_NOCOLOR='1', ANSIBLE_HOST_KEY_CHECKING='False')
            command = ['/usr/bin/ansible-playbook', '-i', 'localhost,', str(fixture)]
            if check:
                command.append('--check')
            result = subprocess.run(command, env=env, text=True, capture_output=True,
                                    timeout=60, check=False)
            return result, json.loads(state_path.read_text())

    def test_local_account_takes_precedence_over_authd(self):
        result, state = self.run_shell(local=BASH, authd=BASH)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(state['accounts']['files'][USERNAME][5], ZSH)
        self.assertEqual(state['accounts']['authd'][USERNAME][5], BASH)
        self.assertEqual(state['events'], [['getent', 'files', USERNAME],
                                           ['user', USERNAME, ZSH]])

    def test_authd_shell_is_updated_with_the_full_username(self):
        result, state = self.run_shell(authd=BASH)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(state['accounts']['authd'][USERNAME][5], ZSH)
        self.assertEqual(state['accounts']['files'], {})
        self.assertEqual(state['events'], [['getent', 'files', USERNAME],
                                           ['getent', 'authd', USERNAME],
                                           ['authctl', ['authctl', 'user', 'set-shell', USERNAME, ZSH]]])

    def test_authd_shell_already_zsh_is_not_changed(self):
        result, state = self.run_shell(authd=ZSH)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(state['accounts']['authd'][USERNAME][5], ZSH)
        self.assertEqual(state['events'], [['getent', 'files', USERNAME],
                                           ['getent', 'authd', USERNAME]])

    def test_unresolved_provider_fails_without_creating_local_user(self):
        for available, error in ((True, 'could not be resolved through authd'),
                                 (False, 'authd service unavailable')):
            with self.subTest(authd_available=available):
                result, state = self.run_shell(available=available)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(error, result.stdout + result.stderr)
                self.assertEqual(state['accounts']['files'], {})
                self.assertEqual(state['events'], [['getent', 'files', USERNAME],
                                                   ['getent', 'authd', USERNAME]])

    def test_authctl_failure_is_surfaced_without_account_mutation(self):
        result, state = self.run_shell(authd=BASH, authctl_fail=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('authctl rejected shell update', result.stdout + result.stderr)
        self.assertEqual(state['accounts']['authd'][USERNAME][5], BASH)
        self.assertEqual(state['accounts']['files'], {})
        self.assertEqual(state['events'][-1],
                         ['authctl', ['authctl', 'user', 'set-shell', USERNAME, ZSH]])

    def test_check_mode_does_not_mutate_either_provider(self):
        for provider in ('local', 'authd'):
            with self.subTest(provider=provider):
                result, state = self.run_shell(**{provider: BASH}, check=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                service = 'files' if provider == 'local' else 'authd'
                self.assertEqual(state['accounts'][service][USERNAME][5], BASH)
                self.assertEqual(set(state['accounts']['files']),
                                 {USERNAME} if provider == 'local' else set())


if __name__ == '__main__':
    unittest.main()
