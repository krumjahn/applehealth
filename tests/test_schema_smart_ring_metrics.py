import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schema.json"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "smart_ring_schema_expectations.json"


class TestSmartRingSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_schema_json_is_valid_json(self):
        self.assertIsInstance(self.schema, dict)
        self.assertIn("dataInput", self.schema)
        self.assertIn("dataOutput", self.schema)

    def test_smart_ring_metric_identifiers_present(self):
        expected = set(self.fixture["requiredSmartRingMetricIdentifiers"])
        actual = set(self.schema["dataInput"]["smartRingMetricIdentifiers"])

        self.assertTrue(
            expected.issubset(actual),
            f"Missing smart ring identifiers: {sorted(expected - actual)}",
        )

    def test_smart_ring_category_identifier_present_in_examples(self):
        key_elements = self.schema["dataInput"]["keyElements"]
        category_examples = []
        for element in key_elements:
            category_examples.extend(element.get("examples", []))

        self.assertIn("HKCategoryTypeIdentifierSleepAnalysis", category_examples)

    def test_schema_mapping_contains_smart_ring_outputs(self):
        expected_outputs = set(self.fixture["requiredSchemaMappings"])
        schema_mapping = self.schema["dataOutput"]["schemaMapping"]
        actual_outputs = set(schema_mapping.keys())

        self.assertTrue(
            expected_outputs.issubset(actual_outputs),
            f"Missing smart ring schema mappings: {sorted(expected_outputs - actual_outputs)}",
        )


if __name__ == "__main__":
    unittest.main()
