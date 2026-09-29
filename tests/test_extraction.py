import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
import extract_paper_metadata as app


class ExtractionTests(unittest.TestCase):
    def test_single_entrypoint(self):
        tree = ast.parse(Path(app.__file__).read_text(encoding="utf-8-sig"))
        entries = [n for n in tree.body if isinstance(n, ast.If)
                   and "__name__" in ast.unparse(n.test)]
        self.assertEqual(len(entries), 1)

    @patch.object(app.requests, "post")
    def test_custom_endpoint_without_json_mode(self, post):
        post.return_value.json.return_value = {
            "choices": [{"message": {"content": '{"title":"Test paper"}'}}]}
        result = app.call_llm("test-key", "test-model", "text", 10,
                              base_url="https://example.test/v1/", json_mode=False)
        self.assertEqual(result["title"], "Test paper")
        self.assertEqual(post.call_args.args[0], "https://example.test/v1/chat/completions")
        self.assertNotIn("response_format", post.call_args.kwargs["json"])

    @patch.object(app.requests, "post")
    def test_auth_error_not_retried(self, post):
        response = Mock(status_code=401)
        post.return_value.raise_for_status.side_effect = requests.HTTPError(response=response)
        with self.assertRaises(RuntimeError):
            app.call_llm("invalid", "model", "text", 10)
        self.assertEqual(post.call_count, 1)

    @patch.object(app.time, "sleep")
    @patch.object(app.requests, "post")
    def test_transient_failure_retries(self, post, sleep):
        ok = Mock()
        ok.json.return_value = {"choices": [{"message": {"content": '{"title":"Recovered"}'}}]}
        post.side_effect = [requests.Timeout(), ok]
        self.assertEqual(app.call_llm("key", "model", "text", 10)["title"], "Recovered")
        self.assertEqual(post.call_count, 2)

    def test_empty_result_rejected(self):
        with self.assertRaises(ValueError):
            app.normalize_result({})

    def test_resume_only_skips_success(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "papers.jsonl"
            app.write_jsonl(output, [{"file": "a.pdf", "status": "ok"},
                                     {"file": "b.pdf", "status": "error"}], False)
            self.assertEqual(app.load_done_files(output), {"a.pdf"})


if __name__ == "__main__":
    unittest.main()
