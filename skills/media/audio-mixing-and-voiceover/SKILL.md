---
name: audio-mixing-and-voiceover
description: Use when mixing voice with background audio.
version: 1.0.0
author: curator
license: MIT
metadata:
  hermes:
    tags: [Audio, ffmpeg, Voiceover, Mixing, Telegram]
    related_skills: [songsee]
---

# Mixing voice with background audio

For layering a background bed under speech (voice messages, voiceover, podcast beds) with ffmpeg,
and for verifying the result numerically instead of guessing. Visual spectrograms are a different
job — see the `songsee` skill.

## When to Use

Use when asked to put music or a sound effect behind a voice recording, join voice notes, change how
loud a background sits, or deliver an edited voice message. Also use when a mix "sounds wrong" and
the level needs measuring rather than guessing. `scripts/measure_mix.py` prints the level report.

## Procedure

1. **Probe every input before mixing.** Get duration, codec, channels and sample rate; the background
   almost never matches the voice length. Then measure the background's per-second level — see
   "Inspect the bed" below, because its first seconds are often silent.
2. **Fetch a source track** into a venv when `yt-dlp` is needed; Debian's `pip` refuses system installs
   (PEP 668), so `python3 -m venv ytenv && ./ytenv/bin/pip install -q yt-dlp` rather than
   `--break-system-packages`. `-x --audio-format mp3 --audio-quality 0` gives a mixable file.
3. **Build the graph** with the voice as the length reference and the bed looped under it:
   `-i voice.ogg -stream_loop -1 -i bg.mp3` plus `amix=inputs=2:duration=first:normalize=0`.
   `normalize=0` is mandatory — the default halves both inputs and the voice goes quiet.
4. **Render candidate levels**, not one guess: loop over two or three `volume=` values and print the
   measured ratio for each (script below), then pick from the numbers.
5. **Verify by isolating the bed** (see "Measure the bed, not the mix") and confirm the voice did not
   get squashed. Then check the peak is below 0 dBFS.
6. **Deliver as a voice bubble** when the user sent a voice message: encode `-c:a libopus -b:a 64k
   -ar 48000` to `.ogg` and attach with `[[audio_as_voice]]` on its own line.

## Measure the bed, not the mix

Subtracting a voice-only render from the mix seems like it isolates the background, but the limiter
and any normalizer react to the *sum*, so the difference signal also contains their gain changes.
This reads as "the background is already audible at t=0" when the bed is still digital silence.

Render the background branch **alone through the identical filter chain** and measure that:

```bash
ffmpeg -y -ss <offset> -stream_loop -1 -i bg.mp3 -t <voice_dur> \
  -filter_complex "[0:a]aformat=...,volume=<V>,adelay=<ms>|<ms>,afade=t=in:st=<s>:d=0.6[bg]" \
  -map "[bg]" bgbranch.wav
```

Silence shows as `-99`/`-inf` dBFS, which is the only proof an intended quiet opening is really quiet.
`scripts/measure_mix.py` does the voice/bed/ratio/peak report.

## Target a voice-to-background ratio, not a volume number

A `volume=` value means nothing across tracks. Aim for the measured RMS ratio between voice and bed:
**+13..+16 dB** keeps speech clearly in front with the bed plainly audible; +20 dB and the bed is
nearly inaudible on a phone speaker; below +8 dB the bed competes with the words. Render three values
and report the ratio, peak and transient peak for each so the choice is visible.

Confirm the voice itself was not squashed: compare its level in a region where the bed is absent
against the same region in the mix. A delta within ~0.1 dB means the limiter is not pulling speech
down; a full-mix rise of a few tenths is the added bed, not compression of the speech.

## Inspect the bed before trusting its name

Short "effect" tracks frequently open with seconds of silence — a 15 s knock clip whose first knock
lands at t=4s. Mixing it unshifted leaves the opening of the voice with no background at all. Print
per-second RMS **and peak** (RMS alone hides sparse transients), then `-ss` past the dead air.

For a delayed entry use `adelay=<ms>|<ms>` with one value per channel plus a short
`afade=t=in:d=0.6`; an abrupt start sounds like a splice.

## Do not sidechain a transient bed

Ducking (`sidechaincompress`) is the reflex for keeping a bed under speech, and it is wrong for
percussive material: knocks, claps and ticks *are* short transients, so the compressor removes
exactly the content that makes the bed audible. The symptom is diagnostic — tripling `volume=`
changes the measured bed level by well under 1 dB. Use a fixed level with a final
`alimiter=limit=0.95` instead. Ducking remains correct for sustained material (music, room tone).

## ffmpeg filtergraph traps

- **Never label a stream `[v]`** — ffmpeg resolves it as a video stream and fails with
  `Stream specifier 'v' ... matches no streams`. Use `[vmain]`, `[bgduck]`, `[aout]`.
- **Split before reuse**: feeding one input to two filters needs `asplit=2[a][b]`; referencing a
  label twice is an error.
- `volumedetect` and `ebur128` can return nothing through some container/codec paths. Decode to WAV
  and measure with `scripts/measure_mix.py` rather than concluding the file is broken.
- Guard `20*log10(x)` against an all-zero window: a digitally silent slice raises
  `ValueError: math domain error` mid-report.

## Confirm two attachments are two recordings

A voice message redelivered as a reply, or an "untranscribable" note resent as a file, arrives as two
paths with identical bytes. `md5sum` both before assuming a request to "join these" has two sources;
splicing a file to itself silently produces a doubled message. When the hashes match, mix the single
voice and say plainly that only one recording arrived, so the user can resend the other.

## Reporting

Lead with the delivered file, then the measured numbers (ratio, peak, where the bed enters) in a few
lines. State a correction to your own earlier measurement when one happened — a wrong number quietly
replaced is worse than a wrong number named. Offer the adjacent levels you already rendered
("±3 dB ready") so an iteration costs one message.
