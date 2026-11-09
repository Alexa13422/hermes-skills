#!/usr/bin/env python3
"""Report voice level, background level, their ratio and the mix peak.

Why this exists: `volumedetect` and `ebur128` sometimes return nothing through a
container/codec path, and subtracting a voice-only render from the mix does NOT
isolate the bed (the limiter reacts to the sum, so the difference carries its
gain changes too). Decode to WAV and measure the bed branch rendered alone.

Usage:
    measure_mix.py --voice voice_chain.wav --mix mix.wav [--bed bedbranch.wav]

  --voice  the speech rendered through the SAME chain, bed absent
  --mix    the final mix
  --bed    the background branch rendered ALONE through the same chain
           (strongly preferred; without it the bed is estimated by subtraction
           and the number is only an upper bound)

Stdlib only: wave + struct + math, so it runs anywhere ffmpeg does.
"""

import argparse
import math
import struct
import wave

SILENT_DB = -99.0


def read_mono(path):
    """Return (samples, sample_rate) as mono by averaging channels."""
    with wave.open(path, "rb") as handle:
        channels = handle.getnchannels()
        rate = handle.getframerate()
        frames = handle.getnframes()
        raw = handle.readframes(frames)

    samples = struct.unpack("<%dh" % (len(raw) // 2), raw)
    if channels == 2:
        samples = [(samples[i] + samples[i + 1]) / 2 for i in range(0, len(samples), 2)]
    return list(samples), rate


def rms_db(samples):
    """RMS in dBFS. Guards log10(0): a digitally silent slice is common."""
    if not samples:
        return SILENT_DB
    mean_square = sum(v * v for v in samples) / len(samples)
    value = math.sqrt(mean_square)
    if value < 1:
        return SILENT_DB
    return 20 * math.log10(value / 32768)


def peak_db(samples):
    if not samples:
        return SILENT_DB
    peak = max(abs(v) for v in samples) / 32768
    if peak <= 0:
        return SILENT_DB
    return 20 * math.log10(peak)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", required=True, help="speech through the chain, no bed")
    parser.add_argument("--mix", required=True, help="final mix")
    parser.add_argument("--bed", help="bed branch rendered alone (preferred)")
    parser.add_argument("--from-sec", type=float, default=0.0,
                        help="ignore everything before this point (skip a silent intro)")
    args = parser.parse_args()

    voice, rate = read_mono(args.voice)
    mix, _ = read_mono(args.mix)

    start = int(args.from_sec * rate)
    limit = min(len(voice), len(mix))

    if args.bed:
        bed, _ = read_mono(args.bed)
        limit = min(limit, len(bed))
        bed_window = bed[start:limit]
        bed_label = "bed (isolated)"
    else:
        bed_window = [mix[i] - voice[i] for i in range(start, limit)]
        bed_label = "bed (SUBTRACTED - upper bound only)"

    voice_window = voice[start:limit]
    voice_db = rms_db(voice_window)
    bed_db = rms_db(bed_window)

    print(f"voice          {voice_db:7.1f} dBFS")
    print(f"{bed_label:<14} {bed_db:7.1f} dBFS")
    print(f"ratio          {voice_db - bed_db:+7.1f} dB   (target +13..+16)")
    print(f"bed peak       {peak_db(bed_window):7.1f} dBFS")
    print(f"mix peak       {peak_db(mix):7.1f} dBFS   (clipping at 0.0)")

    # Per-second bed level proves an intended silent opening really is silent
    # and shows whether sparse transients survived the chain.
    print("\nper-second bed level:")
    for second in range((limit - start) // rate):
        chunk = bed_window[second * rate:(second + 1) * rate]
        marker = ""
        chunk_peak = peak_db(chunk)
        if chunk_peak <= -60:
            marker = "silent"
        elif chunk_peak > -30:
            marker = "<-- transient"
        print(f"  t={second + int(args.from_sec):3d}s  rms={rms_db(chunk):7.1f}  "
              f"peak={chunk_peak:7.1f}  {marker}")


if __name__ == "__main__":
    main()
