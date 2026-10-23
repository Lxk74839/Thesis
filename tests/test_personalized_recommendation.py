"""Public handwritten recommendation cases; no private labels or provider access."""
import unittest


class PersonalizedRun(unittest.TestCase):
    def test_unknown_profile_falls_back_and_unreferenced_preference_is_rejected(self):
        from personalized_recommendation import run_task
        catalog = [{'parent_asin': 'A', 'crop': 'rice', 'title': 'Rice'}]
        arguments = dict(catalog=catalog, history=[], scene={'A': {'eligible': True}})
        task = {'C': ['A'], 'base_scores': [.3], 'K': 1}
        self.assertEqual(run_task(task, profile={'selections': []}, **arguments)['candidates'][0]['score'], .3)
        with self.assertRaisesRegex(ValueError, 'unsupported_preference'):
            run_task(task, profile={'selections': [{'option_id': 'future:target', 'weight': 1}]}, **arguments)

    def test_model_input_has_no_unapproved_history_fields(self):
        from personalized_recommendation import run_task
        requests = []
        def provider(request):
            requests.append(request)
            return {'selections': [], 'issues': []}
        run_task({'C': ['A'], 'base_scores': [.5], 'K': 1, 'method': 'S'},
            catalog=[{'parent_asin': 'A', 'crop': 'rice', 'title': 'Rice'}],
            history=[{'parent_asin': 'A', 'text': 'Good.', 'rating': 5, 'target_marker': 'MUST_NOT_LEAK'}],
            scene={'A': {'eligible': True}}, profile=None, invoke=provider)
        self.assertNotIn('MUST_NOT_LEAK', str(requests))

    def test_verification_feedback_recomputes_the_recommendation(self):
        from personalized_recommendation import run_task
        catalog = [{'parent_asin': 'A', 'crop': 'rice', 'title': 'Whole Rice Grain'},
                   {'parent_asin': 'B', 'crop': 'rice', 'title': 'Brown Rice Flour'}]
        def provider(request):
            identifier = 'h0:form' if request['role'] == '推荐依据核验' else 'h0:crop'
            return {'selections': [{'option_id': identifier, 'weight': 1}],
                    'issues': ['The review explicitly prefers flour.'] if identifier == 'h0:form' else []}
        result = run_task({'C': ['A', 'B'], 'base_scores': [.6, .4], 'K': 1, 'method': 'M'},
            catalog=catalog, history=[{'parent_asin': 'B', 'text': 'I prefer flour.', 'rating': 5}],
            profile=None, invoke=provider, scene={'A': {'eligible': True}, 'B': {'eligible': True}})
        self.assertEqual(result['before_feedback']['topK'], ['A'])
        self.assertEqual(result['topK'], ['B'])

    def test_history_title_term_can_distinguish_rice_varieties(self):
        from personalized_recommendation import run_task
        catalog = [{'parent_asin': 'A', 'crop': 'rice', 'title': 'Jasmine Rice'},
                   {'parent_asin': 'B', 'crop': 'rice', 'title': 'Basmati Rice'}]
        result = run_task({'C': ['A', 'B'], 'base_scores': [.6, .4], 'K': 1},
            catalog=catalog, history=[{'parent_asin': 'B', 'text': 'Good rice.', 'rating': 5}],
            profile={'selections': [{'option_id': 'h0:term:basmati', 'weight': 1}]},
            scene={'A': {'eligible': True}, 'B': {'eligible': True}})
        self.assertEqual(result['topK'], ['B'])

    def test_grounded_preference_can_reverse_base_order(self):
        from personalized_recommendation import run_task
        catalog = [{'parent_asin': 'A', 'crop': 'oats', 'title': 'Rolled Oats'},
                   {'parent_asin': 'B', 'crop': 'rice', 'title': 'Basmati Rice'}]
        history = [{'parent_asin': 'B', 'text': 'I like this rice.', 'rating': 5}]
        result = run_task({'C': ['A', 'B'], 'base_scores': [.6, .4], 'K': 1},
            catalog=catalog, history=history,
            profile={'selections': [{'option_id': 'h0:crop', 'weight': 1}]},
            scene={'A': {'eligible': True}, 'B': {'eligible': True}})
        self.assertEqual(result['topK'], ['B'])
        self.assertEqual(result['candidates'][1]['score'], .7)

    def test_quality_changes_stock_order_without_relaxing_qualification(self):
        from personalized_recommendation import run_task
        catalog = [{'parent_asin': p, 'crop': 'rice', 'title': 'Rice'} for p in ['A', 'B', 'C']]
        task = {'C': ['A', 'B', 'C'], 'base_scores': [.5, .5, 1], 'K': 2, 'prefer_stock': True}
        scene = {'A': {'eligible': True, 'stock': {'supported': True, 'value': 100, 'quality': .2}},
                 'B': {'eligible': True, 'stock': {'supported': True, 'value': 50, 'quality': 1}},
                 'C': {'eligible': False, 'stock': {'supported': True, 'value': 100, 'quality': 1}}}
        full = run_task(task, catalog=catalog, history=[], profile={'selections': []}, scene=scene)
        without = run_task(task, catalog=catalog, history=[], profile={'selections': []}, scene=scene, mode='no_quality')
        self.assertEqual(full['topK'], ['B', 'A'])
        self.assertEqual(without['topK'], ['A', 'B'])

    def test_product_form_from_history_distinguishes_same_crop(self):
        from personalized_recommendation import run_task
        catalog = [{'parent_asin': 'A', 'crop': 'rice', 'title': 'Whole Rice Grain'},
                   {'parent_asin': 'B', 'crop': 'rice', 'title': 'Brown Rice Flour'}]
        result = run_task({'C': ['A', 'B'], 'base_scores': [.6, .4], 'K': 1},
            catalog=catalog, history=[{'parent_asin': 'B', 'text': 'Good flour', 'rating': 5}],
            profile={'selections': [{'option_id': 'h0:form', 'weight': 1}]},
            scene={'A': {'eligible': True}, 'B': {'eligible': True}})
        self.assertEqual(result['topK'], ['B'])


if __name__ == '__main__':
    unittest.main()
