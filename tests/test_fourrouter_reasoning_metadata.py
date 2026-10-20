"""PUBLIC shape from Responses docs, not a replay of the live A1 body."""
import unittest
import provider_fourrouter as provider
from tests.test_fourrouter_protocol_diagnostics import public_request, public_response, setUpModule


class ReasoningMetadata(unittest.TestCase):
    def test_empty_reasoning_metadata_is_validated_before_strict_role_JSON(self):
        response = public_response()
        response['body']['output'].insert(0, {'type': 'reasoning', 'id': 'rs_PUBLIC', 'summary': []})
        result = provider.normalize(response, public_request(), pricing=None, engineering=True)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['raw_response']['reasoning_items'], [{'output_index': 0, 'id': 'rs_PUBLIC', 'summary_count': 0}])
        response['body']['output'][0]['unknown'] = True
        with self.assertRaises(provider.ProtocolError):
            provider.normalize(response, public_request(), pricing=None, engineering=True)
        response['body']['output'][0] = {'type': 'PUBLIC_unknown'}
        with self.assertRaises(provider.ProtocolError):
            provider.normalize(response, public_request(), pricing=None, engineering=True)
        response['body']['output'].pop(0)
        response['body']['output'][0]['content'][0]['text'] = '{"kind":"final_submit","data":{"draft_id":"PUBLIC","extra":1}}'
        with self.assertRaises(provider.ProtocolError):
            provider.normalize(response, public_request(), pricing=None, engineering=True)
