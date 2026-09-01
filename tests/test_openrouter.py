"""OpenRouter unit tests. They are mocked and never make network requests.

Set RUN_OPENROUTER_SMOKE=1 plus OPENROUTER_API_KEY to run the one-request
integration smoke test in this module.
"""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from llm import timed_llm_call
from utils import initialize_clients


class OpenRouterTests(unittest.TestCase):
    def test_client_uses_openrouter_url_and_optional_headers(self):
        with patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "unit-test-key",
            "OPENROUTER_HTTP_REFERER": "https://example.test",
            "OPENROUTER_X_TITLE": "ACE unit test",
        }, clear=False), patch("utils.openai.OpenAI") as factory:
            initialize_clients("openrouter")

        self.assertEqual(factory.call_count, 3)
        kwargs = factory.call_args.kwargs
        self.assertEqual(kwargs["base_url"], "https://openrouter.ai/api/v1")
        self.assertEqual(kwargs["default_headers"]["HTTP-Referer"], "https://example.test")

    def test_missing_key_has_actionable_error(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False):
            with self.assertRaisesRegex(ValueError, "OPENROUTER_API_KEY is not set"):
                initialize_clients("openrouter")

    def test_completion_handles_missing_usage(self):
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"final_answer":"ok"}'))],
            usage=None,
        )
        text, info = timed_llm_call(
            client, "openrouter", "example/free-model", "Return JSON.", "generator", "unit_test"
        )
        self.assertEqual(text, '{"final_answer":"ok"}')
        self.assertIsNone(info["provider_prompt_tokens"])
        self.assertGreater(info["local_estimated_prompt_tokens"], 0)
        self.assertEqual(client.chat.completions.create.call_args.kwargs["max_tokens"], 4096)


@unittest.skipUnless(os.getenv("RUN_OPENROUTER_SMOKE") == "1", "set RUN_OPENROUTER_SMOKE=1 to call OpenRouter once")
class OpenRouterIntegrationSmokeTest(unittest.TestCase):
    def test_one_real_completion(self):
        clients = initialize_clients("openrouter")
        model = os.getenv("OPENROUTER_FREE_MODEL")
        if not model:
            self.fail("Set OPENROUTER_FREE_MODEL to a currently available model before this smoke test.")
        text, info = timed_llm_call(
            clients[0], "openrouter", model, "Reply with exactly: ACE_OK", "smoke", "smoke_openrouter",
            max_tokens=16,
        )
        self.assertTrue(text.strip())
        self.assertIn("provider_prompt_tokens", info)


if __name__ == "__main__":
    unittest.main()
