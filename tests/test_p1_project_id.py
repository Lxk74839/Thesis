"""P1 admission only: PUBLIC config, no real task, credentials, count or HTTP."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import p1_runtime as p1
from evidence_access import RootBudget

PRIVATE_ATTEMPTS = {'credentials': 0, 'network': 0}


def setUpModule():
    def boundary(event, args):
        if event.startswith('socket.'):
            PRIVATE_ATTEMPTS['network'] += 1
            raise OSError('P1_fix_network_forbidden')
        if event == 'open' and isinstance(args[0], (str, bytes)):
            path = Path(os.fsdecode(args[0])).resolve()
            if path.is_relative_to(p1.PROJECT / '.secrets') or '/private/' in path.as_posix():
                PRIVATE_ATTEMPTS['credentials'] += 1
                raise OSError('P1_fix_private_forbidden')
    sys.addaudithook(boundary)


def public_config():
    cfg = json.loads(p1.DEFAULT_CONFIG.read_text(encoding='utf-8'))
    cfg.update(execution_authorized=True, authorization_id='PUBLIC-PROJECT-ID-FIX', storage_limit_bytes=1024**2)
    cfg['authorized_task_keys'] = list(p1.TASK_KEYS.values())
    cfg['model_binding'].update(project_id='PUBLIC-PROJECT-ID-FIX',
        pricing={'input_microusd_per_million': 1, 'output_microusd_per_million': 1,
                 'cached_microusd_per_million': 1}, api_budget_microusd=2000,
        context_token_limit=100000, max_output_tokens=256, max_request_bytes=8192, usage_policy='require_native')
    cfg['limits'] = {m: dict.fromkeys(RootBudget.resources, 1000) for m in ('R', 'S', 'M')}
    cfg['final_reserve'] = {m: dict.fromkeys(RootBudget.resources, 0) for m in ('R', 'S', 'M')}
    for resource in ('model_calls', 'input_tokens', 'output_tokens', 'cost_microusd'):
        cfg['limits']['R'][resource] = 0
    return cfg


class P1ProjectIdAdmission(unittest.TestCase):
    def test_invalid_project_id_alone_refuses_before_assembly_credentials_count_and_send(self):
        parent = p1.PROJECT / '.tmp/recommendation-runtime/p1-project-id'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp, \
                patch('p1_runtime.assemble_task', side_effect=AssertionError('real_assembly_forbidden')) as assembly, \
                patch('fourrouter_probe.send_response', side_effect=AssertionError('HTTP_forbidden')) as send:
            counter = Mock()
            counter.count.side_effect = AssertionError('count_forbidden')
            guard = p1.P1StorageGuard(p1.OUTPUT, 1024**2)
            path = Path(tmp) / 'PUBLIC-config.json'
            for method in ('R', 'S', 'M'):
                cfg = public_config()
                path.write_text(json.dumps(cfg), encoding='utf-8')
                baseline = p1.prepare_p1(path, method, counter=counter, storage_guard=guard)
                self.assertEqual(baseline['terminal'], 'ready')
                self.assertEqual(baseline['missing'], [])
                for variant, value in (('missing', None), ('null', None), ('empty', ''),
                        ('whitespace', ' \t\r\n'), ('integer', 7), ('bool', False),
                        ('list', []), ('mapping', {})):
                    with self.subTest(method=method, project_id=variant):
                        invalid = copy.deepcopy(cfg)
                        if variant == 'missing':
                            del invalid['model_binding']['project_id']
                        else:
                            invalid['model_binding']['project_id'] = value
                        path.write_text(json.dumps(invalid), encoding='utf-8')
                        prepared = p1.prepare_p1(path, method, counter=counter, storage_guard=guard)
                        self.assertEqual(prepared['terminal'], 'not_started')
                        self.assertIs(prepared['started'], False)
                        self.assertEqual(prepared['missing'], ['project_id'])
                        self.assertEqual(prepared['provider_requests_sent'], 0)
                        self.assertEqual(p1.execute_p1(path, method, counter=counter, storage_guard=guard), prepared)
                        assembly.assert_not_called()
                        counter.count.assert_not_called()
                        send.assert_not_called()
                        self.assertEqual(PRIVATE_ATTEMPTS, {'credentials': 0, 'network': 0})

    def test_complete_configuration_keeps_ready_without_starting_execution(self):
        parent = p1.PROJECT / '.tmp/recommendation-runtime/p1-project-id'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            cfg = public_config()
            path = Path(tmp) / 'PUBLIC-config.json'
            path.write_text(json.dumps(cfg), encoding='utf-8')
            counter = Mock()
            guard = p1.P1StorageGuard(p1.OUTPUT, 1024**2)
            for method in ('R', 'S', 'M'):
                result = p1.prepare_p1(path, method, counter=counter, storage_guard=guard)
                self.assertEqual(result['terminal'], 'ready')
                self.assertIs(result['started'], False)
                self.assertEqual(result['missing'], [])
                self.assertEqual(result['provider_requests_sent'], 0)
                self.assertIsNone(result['input_tokens'])
                self.assertIsNone(result['usage'])
                self.assertEqual(result['pricing'], cfg['model_binding']['pricing'])
            counter.count.assert_not_called()


if __name__ == '__main__':
    unittest.main()
