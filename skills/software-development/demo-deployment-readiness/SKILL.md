---
name: demo-deployment-readiness
description: Make a repo clone, install and demo without creds.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [deployment, demo, onboarding, dependencies, install, preview]
    related_skills: [repo-quality-audit, requesting-code-review, service-and-credential-provisioning]
---

# Demo / Deployment Readiness

## When to Use

- "довести до демо", "щоб можна було показати іншим", "make it deployable"
- A project that works on the author's machine must survive a stranger's clone
- Preparing a public preview when production credentials are absent or secret

**Not for:** judging or cleaning code quality (use `repo-quality-audit`), or
provisioning the real credentials themselves (use
`service-and-credential-provisioning`).

## Core rule: a clean clone is the only honest test

Demo-readiness is not "the gates pass" — it is "a stranger can get to a working
screen". Test in the order a stranger hits it: install, build, run, click.
A repo that typechecks perfectly and cannot be installed is worth zero.

## Step 1 — Prove it installs from scratch, before anything else

Run the lockfile-exact install, not the forgiving one. This is the single most
commonly broken step and it blocks every other person on the project.

```bash
npm ci --no-audit --no-fund; echo "exit=$?"
```

`npm ci` failing while the author's `node_modules` works is the signature of a
lockfile that was only ever produced by incremental local installs. Treat it as
a release blocker, not an environment quirk.

When it fails, read the FIRST `npm error` block, not the `npm warn` noise above
it — warnings about overridden peers are usually a different, tolerated
conflict, and chasing them wastes the pass.

```bash
npm install --no-audit --no-fund >/tmp/install.log 2>&1
grep -n "npm error" /tmp/install.log | head -20
```

## Step 2 — Resolve ERESOLVE by version, not by force

`--legacy-peer-deps` and `--force` hide the conflict and hand the next person a
tree npm never validated. Fix the versions instead.

For a DIRECT dependency pinned to an old peer major, find the release that
matches the major the project actually uses:

```bash
for v in $(npm view PKG versions --json | python3 -c "import json,sys;print(' '.join(json.load(sys.stdin)[-10:]))"); do
  echo "  $v -> peer $(npm view "PKG@$v" peerDependencies.THE_PEER 2>/dev/null)"
done
```

Pick the newest version whose peer range covers the installed major — not the
`latest` tag, which usually demands a newer major and cascades a rewrite.

For a TRANSITIVE dep that npm hoists at the wrong major (a deep package pulls
v5 to the top while a direct dep requires >=6), pin the shared leaf packages
with `overrides` in `package.json`. Then rebuild the tree from nothing —
`node_modules` and the lockfile both cache the bad resolution:

```bash
rm -rf node_modules package-lock.json
npm install --no-audit --no-fund; echo "exit=$?"
```

Commit the regenerated lockfile in this case: unlike incidental arch/marker
churn, it encodes the fix.

## Step 3 — Make missing credentials a visible state, not a hang

An SDK provider that is skipped when its key is absent usually leaves its hook
reporting "not ready" forever rather than throwing — so every gated page sits on
a spinner and the demo looks broken instead of unconfigured.

Export an explicit flag from the auth/config layer and branch on it:

```ts
export const AUTH_CONFIGURED = Boolean(process.env.NEXT_PUBLIC_PRIVY_APP_ID);
// ready: AUTH_CONFIGURED ? ready : true   → "ready, signed out", not "loading"
```

Then, everywhere the flag is false:
- replace "Loading…" with one sentence saying sign-in is not configured here;
- replace every login control, INCLUDING the one in the global header, with a
  link to the public demo route. A button whose handler cannot work is worse
  than no button, because the visitor blames the product.

Grep for the login label across the whole app rather than fixing the page you
happen to be on — the header control lives in its own component and is the one
reviewers click first.

## Step 4 — Find the credential-free happy path and lead to it

Look for an existing seeded/sample route (`/passport/demo`, `/demo`, fixtures)
before building one. Projects built for hackathons usually already have it, and
it is the strongest demo asset: real-looking records, zero setup.

Verify it renders as TEXT, not just as a 200 — a shell page with an empty client
component also returns 200:

```bash
curl -s --max-time 25 http://localhost:PORT/PATH | python3 -c "
import sys,re,html
t=re.sub(r'<script.*?</script>|<style.*?</style>','',sys.stdin.read(),flags=re.S)
print(re.sub(r'\\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)))[:400])"
```

## Step 5 — Integrate provided brand assets at the real UI entry point

When the user supplies a logo or other visual asset, first locate the actual project and the component that renders the relevant surface (usually the storefront header, footer, favicon, or metadata), rather than dropping the file into a guessed directory. For a Next.js storefront, put a public asset under `apps/storefront/public/images/`, reference it with a root-relative URL such as `/images/brand-logo.jpg`, and use `next/image` with explicit dimensions, meaningful `alt`, and `priority` only for an above-the-fold logo.

Before editing, inspect the target component and package manifest. Preserve unrelated working-tree changes: report the files changed by this task separately from pre-existing modifications, and never reset the repository wholesale. Verify the asset type and dimensions with `file` (and `identify` when available), then run the narrowest relevant build or typecheck from the app directory.

If dependencies are absent and the build cannot run, report the exact blocker (`next: not found`, for example) and do not claim the UI change is runtime-verified. The file placement and source diff can still be verified independently.

## Step 6 — Scope lint to the shipped app

Helper directories (pitch decks, build scripts, agent skill folders) are plain
Node or generated code and will fail the app's TypeScript rules. Add them to the
lint config's ignores with a comment saying why, instead of rewriting scripts
that are not shipped — and instead of leaving a red gate the user must remember
to ignore.

## Pitfalls

- **Verify the running process is serving the NEW build.** A stale server keeps
  the port and silently serves the old bundle, which reads exactly like "my fix
  did nothing". Confirm the new string is in the build output, then confirm who
  owns the port, then hard-kill that PID:
  ```bash
  grep -rl "new visible string" .next | head -3   # fix is in the build?
  ss -ltnp | grep :PORT                            # who actually listens
  kill -9 <pid>
  ```
  `pkill -f "next start"` kills the wrapper and leaves the `next-server` child
  holding the port; process age in `ps -eo pid,etimes,cmd` older than your
  rebuild is the tell.
- **A build that compiles but dies collecting page data is not a code defect.**
  Static generation calls the real API, so an unreachable backend gives
  `ECONNREFUSED` after a successful compile. Report the stage reached; never
  call it "passing", and never call it "broken code".
- **Never claim an optimization is confirmed when the verifying build could not
  finish.** State which specific claim is unverified and what is needed to
  verify it. Enabling image optimization or deferring a heavy script is
  plausible-but-unmeasured until a full build runs.
- **Check the sample/demo route before assuming credentials are mandatory.**
  Concluding "this needs keys to show anything" when a working public fixture
  route already exists sends the user to buy setup they do not need.

## Report style

While working, stay silent: no step-by-step commentary. At the end give the
findings and the result, short.

Lead with the blocker you removed ("the repo did not install at all, even with
its own lockfile"), because that is the fact that changes the user's plan. Then
the verified gates in one line each. Then, explicitly separated, what is still
NOT verified and what it needs. Finish with the single next decision for the
user — commit, push, or deploy — not a menu of possibilities.
