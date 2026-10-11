"""Source-pinned independent published corpus pilot and tamper controls."""
from __future__ import annotations
import unittest
from tools.run_issue1_external_official_typed_pilot_v15 import (
    run, gitblob, FILES, get,
)
class OfficialSourceTypedPilotTests(unittest.TestCase):
    def test_actual_original_upstream_cases_match(self):
        x=run()
        self.assertEqual(x["official_source_tests"],46)
        self.assertEqual(x["published_expected_labels_matched"],46)
        self.assertEqual(x["all_admissible_groups"],11)
        self.assertFalse(x["S3_arbitrary_natural_language_semantics_certified"])
        self.assertFalse(x["S4_real_world_task_complete_inventory_certified"])
        self.assertFalse(x["original_MVP18_pass_raised"])
    def test_external_source_tamper_rejected(self):
        def altered(name):return get(name)+b" "
        with self.assertRaisesRegex(ValueError,"EXTERNAL_PUBLISHED_UPSTREAM_BLOB_CHANGED"):
            run(altered)
    def test_external_source_expected_labels_nonspoofable(self):
        import json
        def fake(name):
            rows=json.loads(get(name))
            rows[0]["tests"][0]["valid"]=not rows[0]["tests"][0]["valid"]
            return json.dumps(rows).encode()
        with self.assertRaisesRegex(ValueError,"EXTERNAL_PUBLISHED_UPSTREAM_BLOB_CHANGED"):
            run(fake)
    def test_fixed_official_publisher_source_pins(self):
        for name,sha in FILES.items():
            self.assertEqual(gitblob(get(name)),sha)
if __name__=="__main__":unittest.main()
