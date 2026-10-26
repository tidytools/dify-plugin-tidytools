"""Dify entrypoint, credential validation and fixed RapidAPI transport."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from dify_plugin import DifyPluginEnv, Plugin, ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


# Deliberately no user-supplied host or redirect destination for a credentialed call.
HOSTS = {
    "contact": "website-contact-extractor1.p.rapidapi.com",
    "ai_extract": "ai-web-data-extractor-api-any-page-to-structured-json.p.rapidapi.com",
    "markdown": "web-to-markdown-for-llms.p.rapidapi.com",
}
PATHS = {
    "contact": "/api/v1/contacts",
    "ai_extract": "/api/v1/ai-extract",
    "markdown": "/api/v1/markdown",
}
PLUGIN_VERSION = "0.1.0"
PLUGIN_USER_AGENT = f"tidytools-dify/{PLUGIN_VERSION}"

ALLOWED_PARAMS = {
    "contact": frozenset(("url", "maxPages", "render", "includeDetails")),
    "ai_extract": frozenset(("url", "fields", "schema", "instructions", "maxChars", "maxTokens", "timeoutMs")),
    "markdown": frozenset(("url", "format", "render", "removeBoilerplate", "cssSelector", "includeLinks", "maxChars", "startIndex", "timeoutMs")),
}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _open(request):
    # Never forward X-RapidAPI-Key to a Location chosen by another server.
    return build_opener(_NoRedirect()).open(request, timeout=60)


def _redact(value, secret):
    """Keep a returned page or gateway body from echoing the credential."""
    if isinstance(value, str):
        return value.replace(secret, "[redacted]") if secret else value
    if isinstance(value, list):
        return [_redact(item, secret) for item in value]
    if isinstance(value, dict):
        return {_redact(key, secret): _redact(item, secret) for key, item in value.items()}
    return value


def _failure(status, code, message):
    return {"success": False, "status": status, "error": {"code": code, "message": message}, "rows": []}


def call_api(tool, params, credentials):
    """Call one known API; return a stable JSON envelope and never expose the key."""
    if tool not in HOSTS:
        raise ValueError("Unknown TidyTools tool")
    key = credentials.get("rapidapi_key") if isinstance(credentials, dict) else None
    if not isinstance(key, str) or not key.strip():
        return _failure(0, "missing_credential", "Add your RapidAPI key in the Dify TidyTools credential.")
    if not isinstance(params, dict):
        return _failure(0, "invalid_input", "Tool parameters must be an object.")
    body = {name: value for name, value in params.items() if name in ALLOWED_PARAMS[tool] and value is not None and value != ""}
    if not isinstance(body.get("url"), str) or not body["url"].strip():
        return _failure(0, "invalid_input", "A website URL or domain is required.")
    host = HOSTS[tool]
    request = Request(
        f"https://{host}{PATHS[tool]}",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"X-RapidAPI-Key": key, "X-RapidAPI-Host": host, "Content-Type": "application/json",
                 "User-Agent": PLUGIN_USER_AGENT, "X-TidyTools-Source": "dify"},
        method="POST",
    )
    try:
        with _open(request) as response:
            status = response.status
            payload = json.load(response)
    except HTTPError as error:
        status = error.code
        error.close()
        payload = None
    except (URLError, TimeoutError, OSError):
        return _failure(0, "network_error", "RapidAPI could not be reached; retry later.")
    except (ValueError, UnicodeError):
        return _failure(0, "invalid_response", "RapidAPI returned an unreadable response.")

    if status == 401:
        return _failure(status, "invalid_credential", "Check the RapidAPI key in the Dify credential.")
    if status == 403:
        return _failure(status, "subscription_required", "Check the RapidAPI key. Subscribe the key's RapidAPI app to this API's BASIC plan if it is not subscribed yet.")
    if status == 429:
        return _failure(status, "quota_exceeded", "RapidAPI plan quota or rate limit reached; retry later or upgrade.")
    if status == 422:
        return _failure(status, "target_failed", "The target website could not be read or was blocked.")
    if not 200 <= status < 300:
        return _failure(status, "api_error", f"RapidAPI returned HTTP {status}.")
    if not isinstance(payload, dict) or payload.get("success") is False:
        return _failure(status, "api_error", "The API did not return a successful result.")
    data = _redact(payload, key)
    return {"success": True, "status": status, "data": data, "rows": [data]}


class TidyToolsProvider(ToolProvider):
    def _validate_credentials(self, credentials):
        key = credentials.get("rapidapi_key") if isinstance(credentials, dict) else None
        if not isinstance(key, str) or not key.strip():
            raise ToolProviderCredentialValidationError("Enter a RapidAPI key.")
        # Credential checks are local: subscriptions belong to three separate APIs.


if __name__ == "__main__":
    Plugin(DifyPluginEnv()).run()
