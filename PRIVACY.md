# TidyTools for Dify privacy policy

The plugin sends a selected website URL and tool parameters over HTTPS to one of three fixed RapidAPI gateway hosts. AI Web Extract also sends field names and optional instructions. RapidAPI forwards the call to the matching TidyTools backend, which fetches and processes the target page. Responses can contain public contact details or other personal data from that page; submit only pages you are entitled to process.

The RapidAPI key is held in Dify's provider credential and sent to the chosen fixed gateway in `X-RapidAPI-Key`. The plugin does not write the key to a file or log, include it in a tool parameter, or return it in a tool response. Redirects are blocked. The plugin does not independently store URLs, content, results, or Dify user identities.

For aggregate measurement it sends fixed `User-Agent: tidytools-dify/0.1.0` and `X-TidyTools-Source: dify` headers. If RapidAPI forwards the source header, TidyTools records only product, channel, subscription plan label, HTTP status, elapsed time, and the closed source label `dify` or `other` in Cloudflare Analytics Engine. That usage point contains no URL, content, key, IP address, raw header, or Dify user identifier. Dify, RapidAPI, Cloudflare, and the target website may process or retain information under their own policies.

Third-party policies: [RapidAPI](https://rapidapi.com/page/privacy), [Cloudflare](https://www.cloudflare.com/privacypolicy/). Privacy contact: tidytools@yukai.uk.
