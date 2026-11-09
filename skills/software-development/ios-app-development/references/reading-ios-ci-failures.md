# Reading an iOS CI failure without drowning in the log

An iOS archive or simulator build emits tens of thousands of lines, most of them
successful compiler invocations whose command lines are each several kilobytes.
Fetching the whole job log into context is the wrong first move: the output is
truncated head+tail, and the one line that matters sits in the omitted middle.

## Order of operations

1. **Get each job's conclusion first, never the log.**

   ```bash
   gh run view <id> --json status,conclusion,jobs \
     -q '.status+" / "+(.conclusion//"-"), (.jobs[]|.name+" => "+(.conclusion//"running"))'
   ```

   `gh run view --log` refuses while a run is in progress ("logs will be
   available when it is complete"), so during a run this JSON query is the only
   way to watch progress.

2. **Separate `cancelled` from `failure` before debugging anything.** With
   `concurrency: cancel-in-progress: true`, a new push cancels the previous run's
   jobs mid-build. A cancelled job's tail is full of "Terminate orphan process
   (clang++)" lines that read exactly like a crashed toolchain. Nothing is wrong
   with it; re-run or ignore.

3. **Grep the log for the real error markers, with a column cut.**

   ```bash
   gh run view --job <job-id> --log 2>/dev/null \
     | grep -aE 'error:|BUILD FAILED|build commands failed|Could not resolve package' \
     | cut -c1-300 | sort -u
   ```

   `cut` is what keeps this usable — an unclipped compiler line is longer than
   the whole useful part of the output. `grep -a` because the log carries bytes
   grep may treat as binary. Then re-grep with `-A 12` around the single marker
   you found to read its detail.

4. `--log-failed` can come back empty for a job that failed inside `xcodebuild`
   rather than at a step boundary. Fall back to `--job <id> --log` on the
   specific failed job rather than concluding there is no error to find.

## Exit code 65 is not a code failure

`xcodebuild` reports almost everything as exit 65, and the surrounding thousands
of lines of successful compilation make it look like a broken pod picked at
random. Read the actual message before touching any source. The common causes
that no source change can fix:

- **`package '<name>' is using Swift tools version 6.2.0 but the installed
  version is 6.1.0`** — a dependency (typically an Expo or RN package) declares a
  newer SwiftPM tools version than the runner image's Xcode provides. Fix by
  moving the job to a runner image whose Xcode is new enough, not by pinning the
  dependency down. Check what each image ships before choosing:
  `images/macos/macos-<ver>-arm64-Readme.md` in `actions/runner-images` lists the
  installed Xcode versions. Leave a comment on the `runs-on:` line saying which
  dependency forced the bump, or a future session will "simplify" it back.
- A missing Info.plist key or entitlement assertion in a gating step — that one
  *is* yours.

## Polling, not watching

`gh run watch` blocks until the run ends and will hit a tool timeout on a 20+
minute iOS build, losing the whole call. Poll with short per-call timeouts
instead, and accept that several polling calls are normal:

```bash
for i in $(seq 1 18); do
  s=$(timeout 40 gh run view <id> --json status -q .status 2>/dev/null)
  [ "$s" = "completed" ] && break
  sleep 20
done
```
