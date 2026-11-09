# Probing model IDs across routing layers

## ID syntax is layer-specific

The same model is usually alive on both layers under two different spellings:

| Layer | Accepted syntax | Reaction to the other syntax |
|---|---|---|
| Router / gateway (routes between vendors) | vendor-prefixed (`codex/gpt-5.6-terra`) | bare ID may resolve or 400 |
| Upstream proxy (single vendor pool) | bare (`gpt-5.6-terra`) | `unknown provider for model <vendor>/<id>` |

## The wrong-layer probe

A prefixed ID probed against the bare-ID layer returns a provider error that is
indistinguishable from a retired model. Acting on it produces a false "the whole role map is
dead" alarm and a pointless rewrite of working configuration.

Rules:

- Read the caller's own `base_url` (runner script, config block) **before** probing, and probe that exact port with that layer's syntax.
- Treat an all-IDs-dead sweep as evidence of a wrong-layer probe or a bad key, not of a vendor catalogue change — a real retirement kills some IDs, not every one at once.
- Re-probe on the correct layer before reporting any breakage, and retract explicitly if an earlier claim came from the wrong port.
- A model list (`/v1/models`) is membership, not capability: confirm with a real completion.

## Aliases are not separate gateways

One gateway instance is commonly reachable under several addresses (`localhost:<port>`,
LAN IP, tailnet IP) and accepts the same API key on all of them. Differing addresses across
config entries are often the same service, so verify with an identical keyed request to each
address before "consolidating" or declaring one broken.

## Minimal probe

```bash
curl -s -m 60 -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"<id-in-this-layer-syntax>","max_tokens":20,
       "messages":[{"role":"user","content":"reply OK only"}]}' \
  http://<host>:<port>/v1/chat/completions
```

Check `choices[0].message.content` is non-empty and `finish_reason` is `stop`; an empty string with
`finish_reason: length` means a thinking budget ate the whole allowance, not a dead model.
