import json
import os
import unittest
from unittest import mock

os.environ.setdefault("GROQ_MODEL", "test-model")

import tone_analysis


class TestGroqToneAnalysis(unittest.TestCase):
    def test_analyze_text_tone_calls_groq_and_parses_scores(self):
        api_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"pro_male": 2, "pro_female": 1}'
                    }
                }
            ]
        }
        response = mock.MagicMock()
        response.read.return_value = json.dumps(api_response).encode("utf-8")

        context_manager = mock.MagicMock()
        context_manager.__enter__.return_value = response

        with mock.patch("tone_analysis.request.urlopen", return_value=context_manager) as mocked_urlopen:
            result = tone_analysis.analyze_text_tone("some text", api_key="secret", model="test-model", timeout=5)

        self.assertEqual(result, {"pro_male": 2, "pro_female": 1})
        request_obj = mocked_urlopen.call_args.args[0]
        headers = dict(request_obj.header_items())
        self.assertEqual(request_obj.full_url, "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(headers.get("Authorization"), "Bearer secret")

    def test_analyze_text_tone_returns_none_without_api_key(self):
        with mock.patch("tone_analysis.request.urlopen") as mocked_urlopen:
            result = tone_analysis.analyze_text_tone("some text", api_key="")

        self.assertIsNone(result)
        mocked_urlopen.assert_not_called()

    def test_apply_tone_style_wraps_content_with_opacity(self):
        html = "<p>Hello</p>"
        styled = tone_analysis.apply_tone_style(html, {"pro_male": 2, "pro_female": 0})
        self.assertIn('opacity:0.70', styled)
        self.assertIn("Tone score: M2/F0", styled)
        self.assertIn(html, styled)


if __name__ == "__main__":
    unittest.main()
