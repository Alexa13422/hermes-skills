---
name: ios-app-development
description: Use when building iPhone apps without a local Mac.
---

# iOS app development from a non-macOS host

## Procedure

1. Separate the build into a platform-independent Swift package (domain logic and fixture tests) and an iOS target (SwiftUI, PhotoKit, MapKit). Keep demo UI honest: simulated pairing, scanning, and consent must be visibly labeled until wired to real APIs.
2. Write behavioral tests for the pure package before app integration. For photo-derived encounters, model incomplete metadata and day-boundary/timezone cases; same-city/same-day evidence is a *possible overlap*, never proof of meeting. Do not infer a city from raw coordinates without an explicit resolver and test data.
3. Generate an iOS project reproducibly (for example, XcodeGen `project.yml`) and add macOS CI that runs `swift test`, generates the project, then runs `xcodebuild build` for an iOS Simulator with `CODE_SIGNING_ALLOWED=NO`. A package test passing is not an app build passing. Declare `platforms:` explicitly in `Package.swift` (for example `.iOS(.v17), .macOS(.v13)`) as soon as the package uses `Task`, `CancellationError`, or other concurrency types: with no declaration, SwiftPM assumes an ancient macOS deployment target, so the package compiles on Linux and fails only on the macOS runner with "only available in macOS 10.15 or newer".
4. Commit and push the workflow, wait for the actual run, then read **every** job's conclusion — not just the fast test job. A green test job next to two silently broken device-build jobs is the normal failure shape, and it means the install route the user actually cares about has been dead for some time. Inspect failures following `references/reading-ios-ci-failures.md` (job conclusions before logs, `cancelled` is not `failure`, exit 65 is usually a runner-image version mismatch), fix the cause, and rerun until every job passes. Confirm test count and `BUILD SUCCEEDED` from the run log. When creating or changing `.github/workflows/*`, check `gh auth status` for the `workflow` scope *before* push; GitHub can reject the entire push otherwise. For headless `gh auth refresh -s workflow`, set `GH_BROWSER=true` so the device flow does not launch a terminal browser; complete the code on the user's device and verify the scope again.
5. Check capability entitlements against the account tier before promising any install route. A free Apple ID is a "Personal Team" and has no right to the iCloud or Push Notifications capabilities, so an app whose core flow needs CloudKit cannot be proven by sideloading at all — it installs and then fails at the first pair. Sideloading also expires in 7 days, caps at 3 apps per device and 10 App IDs per 7 days. Say which gate each route actually proves instead of offering the free route as equivalent.
6. When a paid-tier capability blocks the whole product, re-derive the requirement before accepting the blocker: the user's goal is usually a *capability* (two devices exchanging state) rather than the service you picked for it. Device-to-device transport over the local network (Network framework / Bonjour) needs no paid entitlement — only `NSLocalNetworkUsageDescription` and `NSBonjourServices` in Info.plist plus the user's one-time local-network prompt. Do not confuse this with `com.apple.developer.networking.multicast`, which *is* a paid entitlement under separate Apple approval but is required only for multicast, not for ordinary Bonjour peer discovery. State the functional cost honestly (both devices on one Wi-Fi at the same time, so no "act now, partner sees it tomorrow") alongside what improves — a local link gives genuine real-time state where a cloud sync's push latency cannot.
7. Distinguish gates: simulator compilation does not establish that PhotoKit permissions, iCloud sync, two-device pairing, revocation, signing, or TestFlight work. Exercise those separately on real devices and report each as pending until observed.

## Local toolchain on a Linux host

Install a Linux Swift toolchain on the working host instead of treating macOS CI as the only way to run tests; a per-push CI round trip is minutes of latency for what is a few seconds locally, and iterating through CI hides which failure is real logic versus platform availability.

```bash
# pick the archive matching the host distro + arch from download.swift.org
curl -L -o swift.tar.gz --retry 3 \
  https://download.swift.org/swift-6.1.2-release/debian12-aarch64/swift-6.1.2-RELEASE/swift-6.1.2-RELEASE-debian12-aarch64.tar.gz
mkdir -p swift && tar xzf swift.tar.gz -C swift --strip-components=1
export PATH="$PWD/swift/usr/bin:$PATH"
swift --version && swift test
```

Export `PATH` in every command that needs it — an unpacked toolchain is not on the login path, so a later call silently falls back to a missing `swift`. The archive is ~800 MB and extraction is slow on small boards; give the download and the `tar` generous timeouts rather than re-running them.

The scratch directory is pruned after ~24h idle, so a toolchain from a previous session is often
gone. Treat `swift: command not found` as "re-download", not as a broken environment, and run the
fetch and extract as background jobs with notify so the wait does not block other work.

A green local `swift test` proves the pure package only. Platform availability, SwiftUI/PhotoKit/MapKit code in the app target, and the simulator build are still only provable on the macOS runner, so keep pushing and reading the run.

## Install routes from a Windows host with no Mac

A simulator build is not an installable product: `CODE_SIGNING_ALLOWED=NO` simulator output cannot go on a device. Device install needs a separate archive job (`-destination 'generic/platform=iOS'`) for an unsigned `.ipa`, or a signing job (App Store Connect API key plus `fastlane match` or `-allowProvisioningUpdates`) for TestFlight. TestFlight internal testers (up to 100) skip App Review, so a two-person test needs no review wait — but the two people must use two different Apple IDs. Promote the CloudKit schema from Development to Production before a TestFlight build, because TestFlight reads Production.

Without a paid account, a desktop sideloader on the user's own Windows machine signs an `.ipa` with their free Apple ID over USB, with the CI macOS runner producing the archive. This is a real route only for an app that needs no paid-tier capability (see step 6); the 7-day re-signing clock applies, and auto-refresh needs that PC powered on with the phone reachable. Keeping the transport free of paid entitlements is what makes this route viable, so decide the transport before promising an install path.

### Building the unsigned .ipa in CI

`xcodebuild -exportArchive` is unusable here — export always demands a signing identity. An `.ipa` is
just a zip with the `.app` inside `Payload/`, so assemble it directly:

```bash
xcodebuild archive -project X.xcodeproj -scheme X -configuration Release \
  -destination 'generic/platform=iOS' -archivePath build/X.xcarchive \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY="" \
  CODE_SIGN_ENTITLEMENTS="" AD_HOC_CODE_SIGNING_ALLOWED=YES
app="$(find build/X.xcarchive/Products/Applications -maxdepth 1 -name '*.app' -print -quit)"
mkdir -p build/Payload && cp -R "$app" build/Payload/
(cd build && zip -qry X-unsigned.ipa Payload)
```

Gate the job on the two faults that are silent at install time, so CI fails instead of the user:
assert each required Info.plist key with `PlistBuddy -c 'Print :<key>'`, and fail if
`codesign -d --entitlements :- <app>` still mentions a paid capability. Also guard against an empty
archive (`-z "$app"`), which would otherwise upload a valid-looking empty `.ipa`.

Download and open the artifact yourself before telling the user it is ready — a green job is not
evidence of a correct bundle. Read `Info.plist` with `plistlib`, confirm the capability keys are
present, confirm no `icloud`/`ubiquity` keys survive, and check `file` reports `Mach-O 64-bit arm64`
with no `embedded.mobileprovision` (correct for unsigned). Note `gh run download -n <name>` can fail
with "would result in path traversal"; fall back to
`gh api repos/{owner}/{repo}/actions/runs/<id>/artifacts -q '.artifacts[0].archive_download_url'`
piped through `gh api > art.zip`.

### Sideloader failures: read the device count before the error text

A sideloader screenshot has two independent signals. A device count of 0 means the phone is not
visible at all, so no login fix can help — the usual cause is the Microsoft Store build of iTunes
shadowing the desktop build, which must be replaced by the vendor's web installer. A login error like
`-80046 / "cannot be completed at this time"` is a refusal from the vendor's auth server for that
account at that moment: repackaging the `.ipa` cannot change it, and the fixes are checking the Apple
ID page for pending agreements or account locks, waiting out throttling after repeated attempts, or
trying a different Apple ID to separate an account problem from a tool problem. Do not suggest an
app-specific password for a desktop sideloader — it wants the real password and prompts for the 2FA
code in its own window; an app-specific password produces a different failure. Never accept the
password in chat.

## Keep the transport replaceable

Before committing to a cloud service, keep every reference to it out of the pure core — protocols and DTOs only, with the SDK confined to app-target files. Then an account-tier blocker or a change of transport costs nothing in the tested core: verify by grepping the core for the SDK name and expecting no hits, and report how many tests the swap would leave untouched. A core that imports the transport SDK turns a billing decision into a rewrite.

Keep the core's DTO names transport-neutral from the start. Names like `PairCloudChange` survive a
move off the cloud fine, but renaming them during the swap would churn every test for no behavioural
gain — leave them and note the mismatch in a comment.

### Replacing a cloud transport with a local-network one

Carry over the security property instead of dropping it. A cloud service authenticated the peer for
you; on a LAN anyone can see the advertised service, so a short pairing code becomes the only
boundary. Bind that code to the TLS handshake as a pre-shared key
(`sec_protocol_options_add_pre_shared_key` + a PSK ciphersuite, with HKDF stretching and a
service-specific salt) so a wrong code fails inside TLS and never reaches application code — one
guess per handshake against a listener that only runs while pairing, rather than offline guessing.
Make the host refuse a second connection when it already has a peer: a pair is two people, and a
third participant silently widens who sees shared material.

Put the parts that *can* be tested without a device in the Swift package, not the app target — their
failure modes are invisible on a phone:

- Pairing-code parsing: a code handled as an integer loses a leading zero (`000123` → `123`); reject
  non-ASCII digits, which satisfy `Character.isNumber` but never match what the peer sends; compare
  in constant time, since `==` on String leaks the prefix by timing.
- Length-prefixed framing: without it two messages sent back to back decode as one malformed object,
  and a message split across two reads is dropped. Bound the declared length from the header *before*
  allocating, or a hostile peer on the Wi-Fi chooses your allocation size. Test the half-frame case
  explicitly — it must yield nothing yet and keep the remainder.

Leave only genuinely platform-only code (CryptoKit derivation, `SecRandomCopyBytes`) in the app
target as an extension on the core type. Duplicating the type in both places duplicates *rules*: two
size caps and two parsers drift, and the device-only copy is the one no test can reach. The compiler
catches this as `invalid redeclaration` / `ambiguous for type lookup`, but only on the macOS runner.
After such a consolidation, delete the error cases nothing throws any more and the guards the core
already enforces — an unreachable `guard` and an unthrown case read like handled conditions while
handling nothing.

Stop implementing delegate hooks the old transport needed (for example a share-acceptance callback),
but keep an app-lifecycle hook to tear the transport down on backgrounding: an advertised service
plus an open listener keeps the pair discoverable long after the two people stopped using the app.

State the functional cost in the product doc as an open question, not a solved one: same-Wi-Fi
simultaneity, guest networks with client isolation blocking discovery entirely, and no cross-session
offline queue. Two phones were never exercised if you have no phones — say so.

### XcodeGen Info.plist trap

`GENERATE_INFOPLIST_FILE: YES` together with an explicit `info:` block makes the `INFOPLIST_KEY_*`
build settings win, so keys declared only in `info.properties` never reach the bundle. For Bonjour
that fails as two phones that simply never find each other, with no error anywhere. Set
`GENERATE_INFOPLIST_FILE: NO` plus `INFOPLIST_FILE`, declare every key in `info.properties`, and set
`CODE_SIGN_ENTITLEMENTS: ""` so no entitlements file blocks free-Apple-ID signing.

## Name the transport before answering "is the connection done right?"

A question about "the Bluetooth connection" in an app that never used Bluetooth is a wrong premise,
not a request for reassurance: correct it first, with the grep that settles it
(`grep -rinE 'bluetooth|CoreBluetooth|CBCentral|MultipeerConnectivity' --include=*.swift`), then say
what the code actually does. Agreeing with the premise teaches the user a wrong model of their own
product. Answer "is it final?" by splitting proven from unproven in one breath — core logic with a
test count and a read artifact is proven; anything needing two physical devices is not, however
complete the code looks.

## No simulator exists off macOS — answer the "surely there's an emulator?" question directly

The iOS Simulator is not an emulator: it runs the app natively against Apple's own
UIKit/SwiftUI/PhotoKit frameworks, which ship only inside Xcode and are licensed to Apple hardware.
So there is no Docker image, no VS Code or JetBrains plugin, and no Linux/Windows path — the gap is
licensing plus missing frameworks, not tooling immaturity. Say this plainly instead of hedging; the
contrast that lands is Android, whose emulator works anywhere because AOSP is open.

Two follow-up proposals deserve a straight refusal:

- **Rent a cloud Mac.** EC2 `mac2.metal` is a physical Mac mini on a Dedicated Host with a
  **24-hour minimum** billing period (Apple licensing), so the cheapest "quick look" is a full day
  (~$0.65/h, ~$16). Worth it only for interactive VNC debugging of a finished UI, never for a build
  check a free macOS runner already does.
- **Build on Android first, port later.** Cross-platform frameworks (Flutter, React Native, KMP)
  still require macOS + Xcode to produce an iOS binary, so they save code, not the Mac. Porting also
  rewrites exactly the hard parts — PhotoKit→MediaStore, Bonjour/`NWListener`→`NsdManager`,
  SwiftUI→Compose — while the portable domain logic was already testable on Linux. If the users own
  iPhones, an Android build tests nothing they can run.

## Screenshot the app in CI so the UI is reviewable without a Mac

A green simulator build proves compilation and nothing about what the screen looks like, and nobody
is watching the runner. Add a job that boots a simulator, installs, launches and photographs it,
uploading the images as an artifact — the only zero-cost way to *see* the app without a phone.
Three failure modes make the naive version worthless:

- `simctl launch` returns once the process exists, **before** SwiftUI has drawn. Screenshotting
  immediately yields a blank white rectangle that reads as a broken layout rather than a race; wait
  before capturing.
- A crash on launch still leaves a bootable simulator and a plausible-looking screenshot. Ask the
  device whether the process survived (`simctl spawn <dev> launchctl list | grep <bundle-id>`) and
  dump `simctl spawn <dev> log show --predicate 'process == "<Name>"'` when it did not.
- A hardcoded device name (`iPhone 16`) disappears with runner image updates and fails as an opaque
  simctl error. Resolve a UDID from `simctl list devices available -j`, newest runtime first.

Download the PNG and actually look at it before reporting the UI is fine — a present artifact of the
right byte size is not evidence the screen rendered. Read its PNG header for the dimensions (a
simulator shot is device-resolution, e.g. 1206x2622) and inspect the image itself for real labels and
controls; a blank or placeholder screen passes every mechanical check.

Use `if: always()` on the upload so a failed launch still yields the evidence. Keep multi-line
Python out of the workflow YAML — inline `python3 -c '...'` inside a `run:` block breaks YAML parsing
(`could not find expected ':'`); put it in `scripts/` and call it.

### Reading a failing run

See `references/reading-ios-ci-failures.md` for the triage order (conclusions
before logs, `cancelled` vs `failure`, grepping a multi-megabyte xcodebuild log,
and the runner-image Swift tools mismatch behind most exit-65 failures).

### macOS CI minutes bill at 10x — quote the real cost before adding a job

On a private repo, every macOS-runner minute consumes **ten** minutes of the Actions allowance, so a
three-minute wall-clock run costs ~30 minutes of quota and a 2000-minute monthly plan is ~70 pushes,
not 600. A screenshot job roughly triples the per-push cost because booting a simulator dominates
build time. Measure before claiming a number:

```bash
gh run view <id> --json jobs \
  -q '.jobs[] | "\(.name): \((((.completedAt|fromdateiso8601) - (.startedAt|fromdateiso8601))/60*10|floor)/10) min"'
```

When the cost matters, move the expensive job off every-push triggers (`workflow_dispatch` or tags)
rather than deleting it. `gh api user/settings/billing/actions` returns 404 without the `read:user`
scope — report per-job minutes you measured and point at the billing page instead of guessing a
remaining balance.

LAN pairing still cannot be proven here: two simulators on one runner talk over loopback, which does
not reproduce a real Wi-Fi with client isolation. Keep it listed as a two-device open question.

## Delivery shape this user expects

Commit each change on its own and do NOT push immediately: the user wants local commits per change plus a plain-language explanation of what changed, then pushes batched deliberately. Push when a slice is complete and the user is told what is going out, not reflexively after every commit — macOS CI bills at 10x, so a push per commit burns quota for no added signal.

After a push, verify the resulting run end to end before reporting the push as done, and say which jobs were green on a real run. If that verification uncovers a build that was already broken before this change, fix it as its own commit and tell the user plainly that the route was broken and went unnoticed — a push reported as "done" on the strength of the test job alone is how it stayed unnoticed.

Ship multi-slice work as one commit per slice in sequence, each independently green, rather than one mixed commit; the user asks for this explicitly and it keeps a CI failure attributable to a single slice. A follow-up fix for a failure CI found is its own commit. Report what real runs returned — local test count plus the remote run's test count and `BUILD SUCCEEDED` — and name the first failed run rather than quietly hiding it. Close by stating which gates remain unproven (on-device permissions, two-device pairing, signing, TestFlight) and offer the next slice as a choice.

## Privacy gate for couple-photo apps

Obtain each person's explicit agreement *before* any supporting photos become visible to the partner. Enumerate only assets permitted by PhotoKit for the selected period; Limited Photos access is incomplete coverage, not a full-library scan. Start with metadata on-device and avoid bulk photo upload; transfer only the photos that support a match under the agreed sharing scope. Treat the reveal animation as presentation, not retroactive consent. Provide deletion and unpair behavior before calling the product ready.

<!-- Merged in from the shared skills repo. Review placement. -->
4. Commit and push the workflow, wait for the actual run, inspect failures with `gh run view <id> --log-failed`, fix the source, and rerun until both test and simulator-build steps pass. Confirm test count and `BUILD SUCCEEDED` from the run log. When creating or changing `.github/workflows/*`, check `gh auth status` for the `workflow` scope *before* push; GitHub can reject the entire push otherwise. For headless `gh auth refresh -s workflow`, set `GH_BROWSER=true` so the device flow does not launch a terminal browser; complete the code on the user's device and verify the scope again.
