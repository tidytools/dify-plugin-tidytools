# TidyTools for Dify

Three tools bring website contacts, structured AI extraction, and page-to-Markdown conversion to Dify Workflows, Chatflows, and Agents. The Marketplace plugin is free; each TidyTools API has its own RapidAPI subscription and quota.

## Setup and usage

1. Subscribe to BASIC separately for the tools you use: [Website Contact Extractor](https://rapidapi.com/tidytools/api/website-contact-extractor1), [AI Web Data Extractor](https://rapidapi.com/tidytools/api/ai-web-data-extractor-api-any-page-to-structured-json), [Web to Markdown for LLMs](https://rapidapi.com/tidytools/api/web-to-markdown-for-llms). Check the current Pricing and Endpoints tabs.
2. Install TidyTools in Dify and put your RapidAPI app key into the provider's **RapidAPI key** credential. Never put the key in a prompt or tool input.
3. Add a tool node to a Workflow or Chatflow, or enable a tool for an Agent. Supply the required URL and optional settings, then inspect the JSON result. Dify needs outbound HTTPS to the three fixed RapidAPI hosts.

**Installation:** the provider settings show one masked `RapidAPI key` field. After saving it, the tool picker lists Website Contacts, AI Web Extract, and Web to Markdown. Requires Dify 1.6.0 or later (AI Web Extract uses an array parameter).

**Example workflow:** Start → Web to Markdown (`url` = `https://example.com`) → End, or feed the tool's `json` output into an LLM node to summarize the page. The run trace shows `success`, `status`, and `data.content`.

| Tool | Parameter | Required | Description |
| --- | --- | --- | --- |
| Website Contacts | `url` | Yes | Public company URL or domain. |
| Website Contacts | `maxPages` | No | 1–8 pages; default 5. |
| Website Contacts | `render` | No | `auto` browser fallback or `never` HTTP only. |
| AI Web Extract | `url` | Yes | Public HTTP(S) page URL. |
| AI Web Extract | `fields` | Yes | Array of 1–50 field names, e.g. `["title","summary"]`. |
| AI Web Extract | `instructions` | No | Additional extraction instructions. |
| Web to Markdown | `url` | Yes | Page URL or domain. |
| Web to Markdown | `format` | No | `markdown` or `text`; default `markdown`. |
| Web to Markdown | `maxChars` | No | Maximum characters, 100–500000; default 12000. |

Each invocation emits one JSON message: `success`, HTTP `status` (0 before a response), and either original API object `data` plus `rows: [data]`, or `error: {code, message}` plus `rows: []`. Contact data can include `primaryEmail`, `primaryPhone`, `emails`, `phones`, `socialProfiles`, `contactPages`; AI extraction can include `data`, `title`, `finalUrl`; Markdown can include `content`, `title`, `nextStartIndex`, `truncated`. These fields are inside the original API object.

401 means check the key; 403 means the key is wrong or its RapidAPI app is not subscribed to that API; 422 means the target page failed; 429 means quota or rate limit. Hosts and paths are fixed in `main.py`; redirects are refused so the key cannot be forwarded. Each request carries `User-Agent: tidytools-dify/0.1.0` and `X-TidyTools-Source: dify` for aggregate measurement. See [PRIVACY.md](PRIVACY.md).

Source repository: https://github.com/tidytools/dify-plugin-tidytools. Support: tidytools@yukai.uk. Audio transcription and page classification are not included.

Tested on Dify Community Edition 1.18.0 (self-hosted Docker Compose): package installs, the credential is stored masked, and all three tools run in a Workflow and return the documented JSON envelope.
