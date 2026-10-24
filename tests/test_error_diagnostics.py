import io
import logging
import os
import unittest
from unittest.mock import patch

import agent


class ErrorDiagnosticsTests(unittest.TestCase):
    def test_safe_error_uses_http_status_even_when_exception_text_is_generic(self):
        class ProviderError(Exception):
            status_code = 401

        self.assertIn("模型鉴权失败", agent.safe_error(ProviderError("request rejected")))

    def test_missing_key_startup_is_logged_and_reported_as_auth_failure(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("agent")
        logger.addHandler(handler)
        previous_level = logger.level
        logger.setLevel(logging.WARNING)
        try:
            with patch.dict(os.environ, {"DASHSCOPE_API_KEY": ""}):
                with self.assertRaises(ValueError) as raised:
                    agent.build_model()
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)

        self.assertIn("模型鉴权失败", agent.safe_error(raised.exception))
        self.assertIn("Model initialization failed", stream.getvalue())
        self.assertIn("DASHSCOPE_API_KEY", stream.getvalue())

    def test_model_initialization_logs_only_redacted_provider_details(self):
        class ProviderError(Exception):
            status_code = 401
            body = {
                "error": {
                    "code": "invalid_api_key",
                    "message": "Invalid api-key=sk-testcredential123 Authorization: Bearer test-secret-value",
                }
            }

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("agent")
        logger.addHandler(handler)
        previous_level = logger.level
        logger.setLevel(logging.WARNING)
        try:
            with patch.dict(os.environ, {
                "DASHSCOPE_API_KEY": "test-key-never-log",
                "LLM_TEMPERATURE": "0.3",
            }), patch.object(agent, "ChatOpenAI", side_effect=ProviderError()):
                with self.assertRaises(ProviderError):
                    agent.build_model()
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)

        output = stream.getvalue()
        self.assertIn("Model initialization failed (HTTP status=401", output)
        self.assertIn("invalid_api_key", output)
        self.assertNotIn("sk-testcredential123", output)
        self.assertNotIn("test-secret-value", output)
        self.assertNotIn("test-key-never-log", output)
        self.assertNotIn("Authorization:", output)


if __name__ == "__main__":
    unittest.main()
