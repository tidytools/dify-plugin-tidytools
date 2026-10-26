"""Offline contract tests; no SDK installation, credentials or network needed."""

import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Keep this suite runnable with the standard library before Integrator installs Dify.
sdk = types.ModuleType("dify_plugin")
sdk.Plugin = type("Plugin", (), {})
sdk.DifyPluginEnv = type("DifyPluginEnv", (), {})


class FakeTool:
    def create_json_message(self, value):
        return value


sdk.Tool = FakeTool
sdk.ToolProvider = type("ToolProvider", (), {})
entities = types.ModuleType("dify_plugin.entities")
tool_entity = types.ModuleType("dify_plugin.entities.tool")
tool_entity.ToolInvokeMessage = dict
errors = types.ModuleType("dify_plugin.errors")
tool_error = types.ModuleType("dify_plugin.errors.tool")
tool_error.ToolProviderCredentialValidationError = ValueError
sys.modules.update({
    "dify_plugin": sdk,
    "dify_plugin.entities": entities,
    "dify_plugin.entities.tool": tool_entity,
    "dify_plugin.errors": errors,
    "dify_plugin.errors.tool": tool_error,
})

import main  # noqa: E402
from tools.ai_extract import AiExtractTool  # noqa: E402
from tools.contact import ContactTool  # noqa: E402
from tools.markdown import MarkdownTool  # noqa: E402


KEY = "fake-secret-rapidapi-key"


class Response(io.BytesIO):
    def __init__(self, status, payload):
        super().__init__(json.dumps(payload).encode("utf-8"))
        self.status = status


class ToolsTest(unittest.TestCase):
    def invoke(self, cls, params, status=200, payload=None):
        tool = cls()
        tool.runtime = types.SimpleNamespace(credentials={"rapidapi_key": KEY})
        if payload is None:
            payload = {"success": True, "url": "https://example.com"}
        with patch.object(main, "_open", return_value=Response(status, payload)) as opener:
            result = list(tool._invoke(params))[0]
        return result, opener.call_args.args[0]

    def test_contact_request_and_fields(self):
        data = {"success": True, "primaryEmail": "hello@example.com", "phones": ["+12025550100"]}
        result, request = self.invoke(ContactTool, {"url": "example.com", "maxPages": 2,
                                                    "render": "never", "irrelevant": "ignored"}, payload=data)
        self.assertEqual(request.full_url, "https://website-contact-extractor1.p.rapidapi.com/api/v1/contacts")
        self.assertEqual(json.loads(request.data), {"url": "example.com", "maxPages": 2, "render": "never"})
        self.assertEqual(request.get_header("X-rapidapi-key"), KEY)
        self.assertEqual(result["rows"][0]["primaryEmail"], "hello@example.com")

    def test_ai_extract_request_shape(self):
        result, request = self.invoke(AiExtractTool, {"url": "https://example.com", "fields": ["title"],
                                                     "instructions": "Short", "maxPages": 8})
        self.assertTrue(result["success"])
        self.assertEqual(request.full_url, "https://ai-web-data-extractor-api-any-page-to-structured-json.p.rapidapi.com/api/v1/ai-extract")
        self.assertEqual(json.loads(request.data), {"url": "https://example.com", "fields": ["title"], "instructions": "Short"})

    def test_markdown_request_shape(self):
        _, request = self.invoke(MarkdownTool, {"url": "example.com", "format": "markdown",
                                                        "maxChars": 1200, "fields": ["ignored"]})
        self.assertEqual(request.full_url, "https://web-to-markdown-for-llms.p.rapidapi.com/api/v1/markdown")
        self.assertEqual(json.loads(request.data), {"url": "example.com", "format": "markdown", "maxChars": 1200})

    def test_hosts_fixed_and_no_redirect(self):
        for cls in (ContactTool, AiExtractTool, MarkdownTool):
            _, request = self.invoke(cls, {"url": "example.com", "host": "attacker.example"})
            self.assertIn(request.host, set(main.HOSTS.values()))
            self.assertNotIn("attacker", request.full_url)
            self.assertEqual(request.get_header("X-rapidapi-host"), request.host)
        self.assertIsNone(main._NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://attacker.example"))

    def test_manifest_submission_fields(self):
        manifest = (ROOT / "manifest.yaml").read_text(encoding="utf-8")
        for field in (f"version: {main.PLUGIN_VERSION}", "type: plugin", "author: tidytools",
                      "name: tidytools", "privacy: PRIVACY.md", "icon: icon.svg",
                      "entrypoint: main"):
            self.assertIn(field, manifest)
        self.assertTrue((ROOT / "_assets" / "icon.svg").is_file())
        self.assertTrue((ROOT / "PRIVACY.md").is_file())

    def test_marketplace_precheck_fields(self):
        # langgenius/dify-marketplace-toolkit blocks a PR without repo/contact, with
        # dify_plugin < 0.9.0, or with a README lacking a source link or containing CJK.
        manifest = (ROOT / "manifest.yaml").read_text(encoding="utf-8")
        for field in ("repo: https://github.com/tidytools/", "contact: tidytools@yukai.uk",
                      "minimum_dify_version: 1.6.0"):
            self.assertIn(field, manifest)
        self.assertEqual((ROOT / "requirements.txt").read_text(encoding="utf-8").strip(), "dify_plugin>=0.9.0,<1")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("https://github.com/tidytools/dify-plugin-tidytools", readme)
        self.assertFalse(any("㐀" <= ch <= "鿿" for ch in readme))

    def test_every_tool_has_fixed_source_marker(self):
        for cls in (ContactTool, AiExtractTool, MarkdownTool):
            _, request = self.invoke(cls, {"url": "example.com", "source": "attacker"})
            self.assertEqual(request.get_header("User-agent"), "tidytools-dify/0.1.0")
            self.assertEqual(request.get_header("X-tidytools-source"), "dify")
            self.assertNotIn("source", json.loads(request.data))

    def http_error(self, status, body=None):
        if body is None:
            body = {"message": KEY}
        error = HTTPError("https://example.invalid", status, "failure", {}, io.BytesIO(json.dumps(body).encode()))
        with patch.object(main, "_open", side_effect=error):
            return main.call_api("contact", {"url": "example.com"}, {"rapidapi_key": KEY})

    def test_422_target_failure(self):
        result = self.http_error(422)
        self.assertEqual(result["error"]["code"], "target_failed")
        self.assertEqual(result["rows"], [])

    def test_401_credential(self):
        result = self.http_error(401)
        self.assertEqual(result["error"]["code"], "invalid_credential")
        self.assertEqual(result["rows"], [])

    def test_403_subscription_has_no_success_rows(self):
        result = self.http_error(403)
        self.assertEqual(result["error"]["code"], "subscription_required")
        self.assertIn("Subscribe", result["error"]["message"])
        self.assertEqual(result["rows"], [])

    def test_429_quota(self):
        result = self.http_error(429)
        self.assertEqual(result["error"]["code"], "quota_exceeded")
        self.assertEqual(result["rows"], [])

    def test_key_never_in_success_or_error(self):
        payload = {"success": True, "message": "echo " + KEY, "nested": [KEY]}
        result, _ = self.invoke(ContactTool, {"url": "example.com"}, payload=payload)
        self.assertNotIn(KEY, json.dumps(result))
        for status in (401, 403, 422, 429, 500):
            self.assertNotIn(KEY, json.dumps(self.http_error(status)))

    def test_missing_key_does_not_open_network(self):
        with patch.object(main, "_open") as opener:
            result = main.call_api("contact", {"url": "example.com"}, {})
        opener.assert_not_called()
        self.assertEqual(result["error"]["code"], "missing_credential")


if __name__ == "__main__":
    unittest.main()
