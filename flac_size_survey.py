#!/usr/bin/env python3
"""
FLAC stream size survey for Music Assistant's content-length estimate.

What it does, in one run:
  1. SCAN    every audio file under the music folder: reads the file header only (no decoding).
  2. SAMPLE  picks a spread of tracks across formats, bit depths, sample rates and compression
             ratios (rare kinds are over-sampled; a few tracks per artist).
  3. MEASURE encodes each sampled track the way Music Assistant streams it (same ffmpeg commands
             as MA upstream dev 21f7f90cb) under a handful of settings, and records the sizes.

It only reads your music. It writes these files to the output folder and nothing else:
  scan.jsonl.gz         one line per audio file: format, size, duration, compression ratio, year
  sample-SEED.jsonl     which tracks were picked and how many each one stands for
  results-SEED.jsonl    measured sizes per picked track, with its loudness and level figures
  meta-SEED.json        ffmpeg version, options, counts, the seed
Each run draws its sample with a new random seed. The seed is in the file names, so several runs
can share one output folder; an unfinished run is continued until it is done.
No file names, tags or audio leave your machine: tracks and artists appear as short hashes.

Needs: Python 3.8+, ffmpeg 9.0.1 (preferred) or 7.1 and its ffprobe, ffmpeg built with libsoxr. All of this is checked
at start, followed by a ten-second self-test on a generated tone; nothing is scanned if a check fails.

Usage:
  python3 flac_size_survey.py /path/to/music --out survey_out
Options:
  --sample N    tracks to measure (default 20000; 0 = scan only)
  --jobs N      tracks measured at once (default: CPU cores / 3; each uses about 3 cores)
  --hours H     stop cleanly after H hours; run the same command again to continue
  --new         start another run with a new seed (a different sample of the library)
  --seed N      use this seed: repeats or continues that run
  --dyn-every N measure the slow "dynamic loudness" setting on one track in N (default 5)
  --genre       also record the genre tag (off by default)
  --selftest    run only the start-up checks and exit
  --force       do not stop when a start-up check or the self-test fails: record what failed in
                the meta file and run anyway (missing ffmpeg, music folder or output folder still stop)
Safe to stop (Ctrl-C) and rerun: finished work is kept.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor
from concurrent.futures import wait as futures_wait
from pathlib import Path

VERSION = "5 (2026-11-12, MA upstream dev 21f7f90cb)"
SEED = 0  # set per run in main(): random, or --seed, or the unfinished run found in the output folder
AUDIO_EXT = {"flac", "m4a", "mp4", "wav", "aiff", "aif", "wv", "ape", "mp3", "aac", "ogg", "oga", "opus"}
RATES = (44100, 48000, 88200, 96000, 176400, 192000)
FFMPEG, FFPROBE = "ffmpeg", "ffprobe"  # replaced by --ffmpeg / --ffprobe
FF = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostats", "-ignore_unknown",
      "-protocol_whitelist", "file,hls,http,https,tcp,tls,crypto,pipe,data,fd,rtp,udp,concat",
      "-probesize", "8096", "-analyzeduration", "500000"]
# MA's filter chain for a 5-band parametric EQ with a -3 dB preamp, per sample rate
EQ5: dict[int, str] = {
    44100: "volume=-3.0dB,biquad=b0=2.5408717850000553:b1=-5.0353321937312785:b2=2.4948722101377223:a0=2.536103385046971:a1=-5.0354081798735795:a2=2.4995646239485065,biquad=b0=1.0132244679869078:b1=-1.998731423510194:b2=0.9867755320130921:a0=1.0166486188061767:a1=-1.998731423510194:a2=0.9833513811938231,biquad=b0=1.077400001722104:b1=-1.9797349455598832:b2=0.9225999982778961:a0=1.065123985412308:a1=-1.9797349455598832:a2=0.9348760145876921,biquad=b0=1.1035377207477672:b1=-1.756443146740457:b2=0.8964622792522328:a0=1.1380697696544888:a1=-1.756443146740457:a2=0.8619302303455111,biquad=b0=4.464919306971622:b1=-1.2050731669085932:b2=0.8023631242045317:a0=3.7019000203330834:a1=-0.25993379821580564:a2=0.6202430421502823",
    48000: "volume=-3.0dB,biquad=b0=2.5389998226419728:b1=-5.0353897904197895:b2=2.4967375705751693:a0=2.534621676583569:a1=-5.03545393054949:a2=2.5010515765038726,biquad=b0=1.01215038052491:b1=-1.9989291749527314:b2=0.9878496194750901:a0=1.015296422805778:a1=-1.9989291749527314:a2=0.984703577194222,biquad=b0=1.0711488153041904:b1=-1.9828897227476208:b2=0.9288511846958097:a0=1.059864267530757:a1=-1.9828897227476208:a2=0.940135732469243,biquad=b0=1.0957515565888267:b1=-1.7937454830653767:b2=0.9042484434111733:a0=1.1276867528741998:a1=-1.7937454830653767:a2=0.8723132471258002,biquad=b0=4.446934727367141:b1=-1.794467894527849:b2=0.871114030478909:a0=3.6440533418101184:a1=-0.7558476585459404:a2=0.6353751800540242",
    88200: "volume=-3.0dB,biquad=b0=2.529356197597043:b1=-5.035609283065351:b2=2.5063560366558675:a0=2.5269814574009333:a1=-5.035628279755174:a2=2.5087117801621543,biquad=b0=1.0066132827584915:b1=-1.9996828307284618:b2=0.9933867172415085:a0=1.0083256297200451:a1=-1.9996828307284618:a2=0.9916743702799549,biquad=b0=1.0387984071364496:b1=-1.994927303327087:b2=0.9612015928635503:a0=1.032644791268181:a1=-1.994927303327087:a2=0.967355208731819,biquad=b0=1.0534207757312415:b1=-1.938154572458156:b2=0.9465792242687586:a0=1.0712377493604008:a1=-1.938154572458156:a2=0.9287622506395992,biquad=b0=3.9804600198944193:b1=-4.385050376045607:b2=1.5607233374979637:a0=3.063819421250976:a1=-2.935551172526135:a2=1.0278647326219357",
    96000: "volume=-3.0dB,biquad=b0=2.528420999722829:b1=-5.035623682453089:b2=2.5072895840252087:a0=2.5262399143670127:a1=-5.035639717595417:a2=2.509454634238697,biquad=b0=1.0060760036089995:b1=-1.9997322758191236:b2=0.9939239963910005:a0=1.0076492353455226:a1=-1.9997322758191236:a2=0.9923507646544774,biquad=b0=1.0356507386200813:b1=-1.995717846477207:b2=0.9643492613799188:a0=1.029996358270999:a1=-1.995717846477207:a2=0.970003641729001,biquad=b0=1.0491599856174234:b1=-1.9477539585546673:b2=0.9508400143825767:a0=1.0655558944256747:a1=-1.9477539585546673:a2=0.9344441055743252,biquad=b0=3.905584775760927:b1=-4.575157817159419:b2=1.6519731028236386:a0=2.987042312029689:a1=-3.095506649869897:a2=1.0908643992653542",
    176400: "volume=-3.0dB,biquad=b0=2.523602210555363:b1=-5.035678556101966:b2=2.5121020833957393:a0=2.5224172102374074:a1=-5.035683305284063:a2=2.5132823345315987,biquad=b0=1.003306772482672:b1=-1.9999207061102353:b2=0.9966932275173279:a0=1.0041629799094576:a1=-1.9999207061102353:a2=0.9958370200905424,biquad=b0=1.0194115160646804:b1=-1.998731423510194:b2=0.9805884839353196:a0=1.0163327553087897:a1=-1.998731423510194:a2=0.9836672446912103,biquad=b0=1.0269193030147858:b1=-1.9844784132003441:b2=0.9730806969852142:a0=1.0358974675091157:a1=-1.9844784132003441:a2=0.9641025324908843,biquad=b0=3.4564603204901756:b1=-5.323627698088555:b2=2.1655655024061913:a0=2.5549081622350314:a1=-3.725265571351429:a2=1.468755533924209",
    192000: "volume=-3.0dB,biquad=b0=2.523134812690181:b1=-5.035682155962377:b2=2.512569068633158:a0=2.522046270678126:a1=-5.035686164754828:a2=2.5136536018527624,biquad=b0=1.0030381034779217:b1=-1.9999330678348022:b2=0.9969618965220783:a0=1.003824745672016:a1=-1.9999330678348022:a2=0.9961752543279841,biquad=b0=1.0178349183486826:b1=-1.9989291749527314:b2=0.9821650816513176:a0=1.0150062136502203:a1=-1.9989291749527314:a2=0.9849937863497799,biquad=b0=1.0247421085715978:b1=-1.9868955580388887:b2=0.9752578914284024:a0=1.0329941320571374:a1=-1.9868955580388887:a2=0.9670058679428626,biquad=b0=3.4081639057600674:b1=-5.374076490728433:b2=2.21820722218781:a0=2.5106156749629296:a1=-3.767712940380489:a2=1.5093919026370035",
}

# name: (float stage forced, normalization, player max bit depth, EQ on, player max rate)
VARIANTS = {
    "exact": (False, "none", 24, False, None),
    "pad24": (True, "none", 24, False, None),
    "dither16": (True, "none", 16, False, None),
    "meas24": (False, "meas", 24, False, None),
    "meas16": (False, "meas", 16, False, None),
    "fixed24": (False, "fixed", 24, False, None),
    "meas_eq24": (False, "meas", 24, True, None),
    "dyn24": (False, "dyn", 24, False, None),
    "meas48": (False, "meas", 24, False, 48000),  # only for sources above 48 kHz
}


def used_bits(text: str) -> int | None:
    """Bits really used, from ffmpeg astats ("Bit depth: 15/16/16/16" or the older "16/24")."""
    m = re.search(r"Bit depth: ([\d/]+)", text)
    if not m:
        return None
    nums = [int(x) for x in m.group(1).split("/") if x]
    return nums[1] if len(nums) >= 4 else nums[0]


TTY = sys.stdout.isatty()


def hms(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def status(text: str, end: bool = False) -> None:
    """Redraw the one-line progress display (terminal only)."""
    if not TTY:
        return
    width = shutil.get_terminal_size((80, 24)).columns - 1
    sys.stdout.write("\r" + text[:width].ljust(width) + ("\n" if end else ""))
    sys.stdout.flush()


def meter(done: int, total: int, session: int, t0: float, failed: int, end: bool = False) -> None:
    """Progress line: percent, bar, counts, speed, time left, time spent."""
    spent = time.time() - t0
    rate = session / spent if session and spent > 0 else 0
    left = hms((total - done) / rate) if rate else "--:--:--"
    frac = done / total if total else 1.0
    bar = ("#" * int(24 * frac)).ljust(24, ".")
    status(f"measure {100 * frac:3.0f}% [{bar}] {done:,}/{total:,}  {rate * 3600:,.0f}/h  "
           f"left {left}  spent {hms(spent)}" + (f"  failed {failed}" if failed else ""), end)


def sha(text: str, n: int) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:n]  # noqa: S324


# ---------------------------------------------------------------- scan

def scan_flac(path: str) -> dict | None:
    """Read a FLAC file's header blocks: stream info, tags, picture and padding sizes."""
    with open(path, "rb") as fh:
        head = fh.read(10)
        skipped = 0
        if head[:3] == b"ID3":  # ID3v2 tag in front of the FLAC stream
            skipped = 10 + ((head[6] & 127) << 21 | (head[7] & 127) << 14 | (head[8] & 127) << 7 | (head[9] & 127))
            fh.seek(skipped)
            head = fh.read(4)
        else:
            fh.seek(4)
        if head[:4] != b"fLaC":
            return None
        info: dict = {"art": 0, "pad": 0}
        meta = skipped + 4
        while True:
            hdr = fh.read(4)
            if len(hdr) < 4:
                return None
            last, kind = hdr[0] >> 7, hdr[0] & 127
            size = int.from_bytes(hdr[1:4], "big")
            meta += 4 + size
            if kind == 0:
                d = fh.read(size)
                x = int.from_bytes(d[10:18], "big")
                info.update(block=int.from_bytes(d[2:4], "big"), rate=x >> 44, ch=((x >> 41) & 7) + 1,
                            bps=((x >> 36) & 31) + 1, samples=x & ((1 << 36) - 1))
            elif kind == 4:
                d = fh.read(size)
                vlen = int.from_bytes(d[0:4], "little")
                info["vendor"] = d[4:4 + vlen].decode("utf-8", "replace")
                pos = 4 + vlen
                count = int.from_bytes(d[pos:pos + 4], "little")
                pos += 4
                tags = {}
                for _ in range(count):
                    clen = int.from_bytes(d[pos:pos + 4], "little")
                    key, _, val = d[pos + 4:pos + 4 + clen].decode("utf-8", "replace").partition("=")
                    tags.setdefault(key.upper(), val)
                    pos += 4 + clen
                info["tags"] = tags
            else:
                if kind == 6:
                    info["art"] += size
                elif kind == 1:
                    info["pad"] += size
                fh.seek(size, 1)
            if last:
                break
        info["meta"] = meta
        return info


def scan(root: Path, out: Path, want_genre: bool) -> list[dict]:
    """Walk the library once; cache the result so a rerun skips this step."""
    cache = out / "scan.jsonl.gz"
    if cache.exists():
        with gzip.open(cache, "rt") as fh:
            rows = [json.loads(line) for line in fh]
        print(f"scan: reusing {len(rows):,} files from {cache.name}")
        return rows
    rows, t0 = [], time.time()
    for folder, _dirs, files in os.walk(root):
        for name in files:
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext not in AUDIO_EXT or name.startswith("._"):
                continue
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, root)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size < 1024:
                continue
            row = {"id": sha(rel, 16), "ext": ext, "size": size, "_rel": rel}
            artist = rel.split(os.sep)[0]
            if ext == "flac":
                try:
                    info = scan_flac(path)
                except (OSError, IndexError, ValueError):
                    info = None
                if not info or not info.get("rate") or not info.get("samples"):
                    row["bad"] = True
                else:
                    dur = info["samples"] / info["rate"]
                    pcm = info["rate"] * info["bps"] / 8 * info["ch"] * dur
                    tags = info.get("tags", {})
                    artist = tags.get("ALBUMARTIST") or tags.get("ARTIST") or artist
                    row.update(bps=info["bps"], rate=info["rate"], ch=info["ch"], dur=round(dur, 3),
                               ratio=round(size / pcm, 4), audio_ratio=round((size - info["meta"]) / pcm, 4),
                               art=info["art"], pad=info["pad"], block=info["block"],
                               vendor=info.get("vendor", ""))
                    for key, field in (("DATE", "year"), ("YEAR", "year"), ("ORIGINALDATE", "orig_year"),
                                       ("ORIGINALYEAR", "orig_year")):
                        m = re.search(r"(?<!\d)(1[89]\d\d|20\d\d)(?!\d)", tags.get(key, ""))
                        if m and field not in row:
                            row[field] = int(m.group(1))
                    if want_genre and tags.get("GENRE"):
                        row["genre"] = tags["GENRE"]
            row["artist"] = sha(artist.strip().lower(), 12)
            rows.append(row)
            if TTY and len(rows) % 500 == 0:
                spent = time.time() - t0
                status(f"scan: {len(rows):,} files  {len(rows) / max(spent, 0.001):,.0f}/s  spent {hms(spent)}")
            elif not TTY and len(rows) % 20000 == 0:
                print(f"scan: {len(rows):,} files ({time.time() - t0:.0f} s)", flush=True)
    status("")
    if TTY:
        sys.stdout.write("\r")
    paths = out / "paths.local.json"  # stays on your machine: maps hashes back to files for step 3
    paths.write_text(json.dumps({r["id"]: r["_rel"] for r in rows}))
    with gzip.open(cache, "wt") as fh:
        for r in rows:
            fh.write(json.dumps({k: v for k, v in r.items() if k != "_rel"}) + "\n")
    print(f"scan: {len(rows):,} audio files in {time.time() - t0:.0f} s")
    return rows


# ---------------------------------------------------------------- sample

def stratum(r: dict) -> str:
    if r["ext"] != "flac" or r.get("bad"):
        return r["ext"]
    rate = r["rate"] if r["rate"] in RATES else "other"
    band = min(int(r["ratio"] / 0.05), 20)
    short = "s" if r["dur"] < 30 else ("l" if r["dur"] > 2400 else "")
    return f'flac/{r["bps"]}/{rate}/{r["ch"]}ch/r{band:02d}{short}'


def pick_sample(rows: list[dict], n: int, out: Path) -> list[dict]:
    """Square-root allocation over strata, at most 3 tracks per artist per stratum."""
    cache = out / f"sample-{SEED}.jsonl"
    if cache.exists():
        picked = [json.loads(line) for line in cache.open()]
        print(f"sample: reusing {len(picked):,} tracks from {cache.name}")
        return picked
    rng = random.Random(SEED)
    groups: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("bad") or r.get("ch", 2) > 2 or (r["ext"] == "flac" and r["dur"] < 5):
            continue
        groups.setdefault(stratum(r), []).append(r)
    weight = {k: math.sqrt(len(v)) for k, v in groups.items()}
    total = sum(weight.values()) or 1
    picked = []
    for key, members in sorted(groups.items()):
        quota = min(len(members), max(20, round(n * weight[key] / total)))
        rng.shuffle(members)
        per_artist: dict[str, int] = {}
        chosen, spare = [], []
        for r in members:
            if per_artist.get(r["artist"], 0) < 3:
                per_artist[r["artist"]] = per_artist.get(r["artist"], 0) + 1
                chosen.append(r)
            else:
                spare.append(r)
            if len(chosen) >= quota:
                break
        chosen += spare[: quota - len(chosen)]
        for r in chosen:
            picked.append({"id": r["id"], "artist": r["artist"], "stratum": key,
                           "stratum_size": len(members), "stratum_picked": len(chosen)})
    rng.shuffle(picked)  # so a run stopped early is still a spread
    with cache.open("w") as fh:
        for p in picked:
            fh.write(json.dumps(p) + "\n")
    print(f"sample: {len(picked):,} tracks from {len(groups)} kinds")
    return picked


def choose_seed(out: Path, wanted: int | None, new: bool) -> tuple[int, str]:
    """Return (seed, "new" | "continuing" | "finished"). Without options an unfinished run is continued."""
    def state_of(seed: int) -> str:
        try:
            meta = json.loads((out / f"meta-{seed}.json").read_text())
        except (OSError, ValueError):
            return "new"
        return "finished" if meta.get("remaining") == 0 else "continuing"
    if wanted is not None:
        return wanted, state_of(wanted)
    runs = sorted(out.glob("meta-*.json"), key=lambda f: f.stat().st_mtime)
    seeds = [int(f.stem[5:]) for f in runs if f.stem[5:].isdigit()]
    if seeds and not new:
        open_runs = [x for x in seeds if state_of(x) == "continuing"]
        return (open_runs[-1], "continuing") if open_runs else (seeds[-1], "finished")
    while True:
        seed = random.SystemRandom().randrange(100000000, 1000000000)
        if seed not in seeds:
            return seed, "new"


# ---------------------------------------------------------------- measure (MA's pipeline)

def pcm_name(depth: int) -> str:
    return {16: "s16le", 24: "s24le"}.get(depth, "s32le")


def fmt_args(ch: int, rate: int, codec: str) -> list[str]:
    return ["-ac", str(ch), "-channel_layout", "stereo" if ch == 2 else "mono", "-ar", str(rate),
            "-acodec", f"pcm_{codec}", "-f", codec]


def build(path: str, bps: int, rate: int, ch: int, variant: str, gain: float | None,
          want_format: bool = False):  # noqa: ANN201

    """Return MA's ffmpeg commands (decode, buffer read, encode) for one track and variant."""
    force_float, norm, max_depth, eq, max_rate = VARIANTS[variant]
    rates = [r for r in RATES if max_rate is None or r <= max_rate]
    buf_depth = bps if bps in (16, 24) else 32
    buf = pcm_name(buf_depth)
    is_float = force_float or norm != "none" or eq
    pcm_rate = max((r for r in rates if r <= rate), default=min(rates))
    pcm, pcm_depth = ("f32le", 32) if is_float else (buf, buf_depth)
    pcm_ch = 2 if force_float else ch
    out_depth = min(pcm_depth, max_depth)
    if eq and pcm_rate not in EQ5:
        return None

    cmds = [[*FF, "-i", path, *fmt_args(ch, rate, buf), "-"]]
    f2: list[str] = []
    if norm == "dyn":
        f2.append("loudnorm=I=-14.0:TP=-2.0:LRA=10.0:offset=0.0:print_format=json")
    elif norm == "fixed":
        f2.append("volume=-6.0dB")
    elif norm == "meas":
        f2.append(f"volume={gain if gain is not None else 0.0}dB")
    if f2 or (buf, rate, ch) != (pcm, pcm_rate, pcm_ch):
        if ch == 1 and pcm_ch == 2:
            f2.insert(0, "pan=stereo|c0=c0|c1=c0")
        if pcm_rate != rate:
            resampler = "swr" if norm == "dyn" else "soxr:precision=30"
            f2.append(f"aresample=resampler={resampler}:osr={pcm_rate}")
        af = ["-af", ",".join(f2)] if f2 else []
        cmds.append([*FF, *fmt_args(ch, rate, buf), "-i", "-", *af, *fmt_args(pcm_ch, pcm_rate, pcm), "-"])
    f3: list[str] = []
    if pcm_ch == 1:
        f3.append("pan=stereo|c0=c0|c1=c0")
    if eq:
        f3.append(EQ5[pcm_rate])
    if pcm_depth > 16 and out_depth == 16:
        f3.append("aresample=resampler=soxr:precision=30:osf=s16:dither_method=triangular_hp")
    af = ["-af", ",".join(f3)] if f3 else []
    cmds.append([*FF, *fmt_args(pcm_ch, pcm_rate, pcm), "-i", "-", *af, "-ac", "2", "-channel_layout",
                 "stereo", "-sample_fmt", "s32" if out_depth > 16 else "s16", "-ar", str(pcm_rate),
                 "-f", "flac", "-compression_level", "0", "-frame_size", "4096", "-"])
    if want_format:
        return cmds, {"rate": pcm_rate, "bps": 24 if out_depth > 16 else 16, "ch": 2}
    return cmds


def run_chain(cmds: list[list[str]], timeout: float = 3600) -> tuple[int, int | None, str]:
    """Run the commands piped together; return (bytes, bits really used in the output, error)."""
    procs, prev = [], None
    for cmd in cmds:
        p = subprocess.Popen(cmd, stdin=prev, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # noqa: S603
        if prev is not None:
            prev.close()
        prev = p.stdout
        procs.append(p)
    stats = subprocess.Popen(  # noqa: S603
        [FFMPEG, "-hide_banner", "-nostats", "-i", "-", "-af", "astats=measure_perchannel=none",
         "-f", "null", "-"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    timed_out = threading.Event()

    def kill() -> None:
        timed_out.set()
        for p in [*procs, stats]:
            try:
                p.kill()
            except OSError:
                pass

    timer = threading.Timer(timeout, kill)
    timer.start()
    size = 0
    try:
        while chunk := prev.read(1 << 20):
            size += len(chunk)
            stats.stdin.write(chunk)
    except (BrokenPipeError, OSError):
        pass
    finally:
        timer.cancel()
    err = "timed out " if timed_out.is_set() else ""
    for i, p in enumerate(procs):
        text = p.stderr.read().decode("utf-8", "replace")
        if p.wait() != 0:
            err += f"stage{i + 1}: {text[-200:]} "
    try:
        stats.stdin.close()
    except OSError:
        pass
    bits = used_bits(stats.stderr.read().decode("utf-8", "replace"))
    stats.wait()
    return size, bits, err


def probe(path: str) -> dict | None:
    out = subprocess.run(  # noqa: S603
        [FFPROBE, "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=codec_name,sample_rate,channels,bits_per_raw_sample,sample_fmt:format=duration",
         "-of", "json", path], capture_output=True, text=True, check=False, timeout=120)
    try:
        d = json.loads(out.stdout)
        st = d["streams"][0]
        raw = str(st.get("bits_per_raw_sample") or "")
        fmt = st.get("sample_fmt", "")
        # lossy codecs decode to float: MA treats those as 16-bit
        bps = int(raw) if raw.isdigit() and int(raw) > 0 else (32 if fmt.startswith("s32") else 16)
        return {"codec": st["codec_name"], "rate": int(st["sample_rate"]), "ch": int(st["channels"]),
                "bps": bps, "dur": float(d["format"]["duration"]), "sample_fmt": fmt}
    except (ValueError, KeyError, IndexError, TypeError):
        return None


def level(text: str, label: str) -> float | None:
    """Last "<label> dB: x" figure in ffmpeg astats output; silence (-inf) is reported as -200."""
    found = re.findall(label + r" dB: (-?[\d.]+|-?inf)", text)
    if not found:
        return None
    return -200.0 if "inf" in found[-1] else float(found[-1])


def analyse_extra(path: str, channels: int, timeout: float = 3600) -> dict:
    """Second decode pass, kept apart from the first so that one is unchanged: level above 8 kHz
    and, for stereo, level of the difference between the channels (both RMS, dB)."""
    stats = "astats=measure_perchannel=none"
    high = f"highpass=f=8000,highpass=f=8000,{stats}"
    if channels == 2:
        graph = f"[0:a:0]asplit=2[h][s];[h]{high}[oh];[s]pan=mono|c0=0.5*c0-0.5*c1,{stats}[os]"
        cmd = [FFMPEG, "-hide_banner", "-nostats", "-i", path, "-filter_complex", graph,
               "-map", "[oh]", "-f", "null", "-", "-map", "[os]", "-f", "null", "-"]
    else:
        cmd = [FFMPEG, "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0", "-af", high, "-f", "null", "-"]
    out = subprocess.run(cmd, capture_output=True, check=False, timeout=timeout)  # noqa: S603
    parts: dict[int, str] = {}
    for line in out.stderr.decode("utf-8", "replace").splitlines():
        m = re.match(r"\[Parsed_astats_(\d+) @", line)
        if m:
            parts[int(m.group(1))] = parts.get(int(m.group(1)), "") + line + "\n"
    order = [parts[k] for k in sorted(parts)]
    res = {"hf_rms_db": level(order[0], "RMS level") if order else None}
    if channels == 2:
        res["side_rms_db"] = level(order[1], "RMS level") if len(order) > 1 else None
    return res


def analyse(path: str, timeout: float = 3600) -> tuple[float | None, int | None, dict]:
    """One decode pass: integrated loudness (LUFS), the bits the source really uses, levels."""
    out = subprocess.run(  # noqa: S603
        [FFMPEG, "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0", "-af",
         "astats=measure_perchannel=none,ebur128=framelog=quiet", "-f", "null", "-"],
        capture_output=True, check=False, timeout=timeout)
    text = out.stderr.decode("utf-8", "replace")
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", text)
    lra = re.findall(r"LRA:\s+(-?[\d.]+) LU", text)
    levels = {"peak_db": level(text, "Peak level"), "rms_db": level(text, "RMS level"),
              "lra": float(lra[-1]) if lra else None}
    return (float(lufs[-1]) if lufs else None), used_bits(text), levels


DYN_EVERY = 5


def measure(item: dict, root: Path, rel: str) -> dict:
    path = str(root / rel)
    row: dict = {"id": item["id"], "artist": item["artist"], "stratum": item["stratum"]}
    try:
        info = probe(path)
        if not info or info["ch"] > 2 or info["dur"] <= 0:
            row["error"] = "unreadable or more than 2 channels"
            return row
        limit = max(900.0, info["dur"] * 4)  # a stuck ffmpeg is killed, the track is recorded as failed
        lufs, used, levels = analyse(path, limit)
        gain = round(-14.0 - lufs, 2) if lufs is not None else None
        row.update(info, size=os.path.getsize(path), lufs=lufs, used_bits=used, gain=gain, **levels, variants={})
        try:  # extra figures only: a failure here must not lose the track
            row.update(analyse_extra(path, info["ch"], limit))
        except (OSError, subprocess.SubprocessError) as err:
            row["extra_error"] = repr(err)[:200]
        for name in VARIANTS:
            if name == "meas48" and info["rate"] <= 48000:
                continue
            if VARIANTS[name][1] == "meas" and gain is None:
                continue
            if name == "dyn24" and DYN_EVERY > 1 and int(item["id"], 16) % DYN_EVERY:
                continue
            built = build(path, info["bps"], info["rate"], info["ch"], name, gain, want_format=True)
            if built is None:
                continue
            cmds, out_fmt = built
            size, bits, err = run_chain(cmds, limit)
            row["variants"][name] = {"size": size, "used_bits": bits, "out": out_fmt,
                                     **({"error": err} if err else {})}
    except Exception as err:  # noqa: BLE001 - one bad file must not stop the survey
        row["error"] = repr(err)[:300]
    return row


FORCE = False
PROBLEMS: list[str] = []


def problem(msg: str) -> None:
    """A failed start-up check: stop with the message, or with --force record it and carry on."""
    msg = " ".join(msg.split())[:300]
    if not FORCE:
        sys.exit(msg + "\n(run with --force to record this and continue anyway)")
    PROBLEMS.append(msg)
    print("FORCED past: " + msg, flush=True)


def selftest(out: Path) -> dict:
    """Generate a tone and push it through every setting; stop with a clear message if anything fails."""
    notes: dict = {}
    with tempfile.TemporaryDirectory(dir=str(out)) as tmp:
        files = {}
        for name, args in (("t16.flac", ["-sample_fmt", "s16"]), ("t24.flac", ["-sample_fmt", "s32"])):
            path = os.path.join(tmp, name)
            rate = "44100" if name == "t16.flac" else "96000"
            made = subprocess.run(  # noqa: S603
                [FFMPEG, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                 f"sine=frequency=440:sample_rate={rate}:duration=4,volume=0.3", "-f", "lavfi", "-i",
                 f"anoisesrc=sample_rate={rate}:duration=4:amplitude=0.05", "-filter_complex",
                 "[0:a][1:a]amix=inputs=2:normalize=0,pan=stereo|c0=c0|c1=0.9*c0", *args, "-c:a", "flac", path],
                capture_output=True, text=True, check=False)
            if made.returncode or not os.path.exists(path):
                problem(f"self-test: ffmpeg could not create a test file: {made.stderr[-300:]}")
                continue
            files[name] = path
        for name, path in files.items():
            info = probe(path)
            if not info:
                problem("self-test: ffprobe could not read the generated test file")
                continue
            lufs, used, levels = analyse(path)
            if lufs is None:
                problem("self-test: the ebur128 loudness filter gave no result with this ffmpeg")
            try:
                levels.update(analyse_extra(path, info["ch"], 300))
            except (OSError, subprocess.SubprocessError) as exc:
                levels["extra_error"] = repr(exc)[:200]
            notes[f"{name}:levels"] = levels
            if None in levels.values() or "extra_error" in levels:
                print(f"self-test: note - some level figures are missing with this ffmpeg ({levels}); sizes are unaffected")
            gain = round(-14.0 - lufs, 2) if lufs is not None else None
            for variant in VARIANTS:
                if variant == "meas48" and info["rate"] <= 48000:
                    continue
                if VARIANTS[variant][1] == "meas" and gain is None:
                    continue
                try:
                    cmds = build(path, info["bps"], info["rate"], info["ch"], variant, gain)
                    size, bits, err = run_chain(cmds, 300)
                except Exception as exc:  # noqa: BLE001
                    size, bits, err = 0, None, repr(exc)[:200]
                notes[f"{name}:{variant}"] = [size, bits]
                if err or size < 1000:
                    problem(f"self-test: setting '{variant}' failed on {name}: {err or 'no output'}")
        # bit-depth readout must tell a zero-padded stream from a filled one
        pad, filled = notes.get("t16.flac:pad24", [0, None])[1], notes.get("t16.flac:meas24", [0, None])[1]
        notes["bits_ok"] = pad == 16 and filled == 24
    if not notes["bits_ok"]:
        print("self-test: note - this ffmpeg's bit-depth readout is not usable; sizes are unaffected")
    print("self-test: " + ("passed" if not PROBLEMS else f"{len(PROBLEMS)} problem(s), continuing because of --force"))
    return notes


# ---------------------------------------------------------------- main

USAGE = """\
Measures how large Music Assistant's FLAC streams are for a sample of your library.
Read-only: it never changes, moves or uploads your music.

FLAC_SIZE_SURVEY music_folder [--out folder] [--sample N] [--jobs N] [--hours H]
                 [--new] [--seed N] [--dyn-every N] [--genre] [--selftest] [--force]
                 [--ffmpeg path] [--ffprobe path]

  music_folder    Top folder of your music library.
  --out folder    Where the result files go. Default: survey_out
  --sample N      How many tracks to measure. Default: 20000. 0 = scan only.
  --jobs N        Tracks measured at once. Default: CPU cores / 3.
  --hours H       Stop cleanly after H hours. Run the same command again to continue.
  --new           Start another run with a new random seed (a different sample).
  --seed N        Use this seed. Repeats that run, or continues it if unfinished.
  --dyn-every N   Measure the slow "dynamic loudness" setting on 1 track in N. Default: 5.
  --genre         Also record each track's genre tag. Off by default.
  --selftest      Only check ffmpeg and run the 10-second self-test, then exit.
  --force         Do not stop if a start-up check fails; record it and run anyway.
  --ffmpeg path   The ffmpeg program, or the folder holding ffmpeg and ffprobe.
                  Default: whatever "ffmpeg" is on PATH.
  --ffprobe path  The ffprobe program, if it is not next to ffmpeg.

Examples:
  python3 flac_size_survey.py /mnt/music
  python3 flac_size_survey.py /mnt/music --selftest
  python3 flac_size_survey.py /mnt/music --out /tmp/survey --hours 8
  /opt/python3.12/bin/python3 flac_size_survey.py /mnt/music --ffmpeg /opt/ffmpeg/bin

Needs Python 3.8+ and ffmpeg + ffprobe (built with libsoxr). Nothing else.
ffmpeg must be 9.0.1 (preferred) or 7.1: the versions Music Assistant ships.
To use a particular Python, start the script with it, as in the last example.
Safe to stop with Ctrl-C and run again: finished work is kept.

Each run picks its sample with a random seed. The seed is saved and is part of the
file names, so runs never overwrite each other.

When it finishes, send back these four files from the output folder (SEED is a number):
  scan.jsonl.gz  sample-SEED.jsonl  results-SEED.jsonl  meta-SEED.json
Do NOT send paths.local.json: it holds your file names.
"""


def main() -> None:
    if len(sys.argv) == 1 or any(a in ("/?", "-?", "-h", "--help", "/h", "/help") for a in sys.argv[1:]):
        print(USAGE)
        return
    try:  # progress shows up at once even when output is sent to a log file
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(add_help=False, usage="run with no arguments (or /?) for help")
    ap.add_argument("music")
    ap.add_argument("--out", default="survey_out")
    ap.add_argument("--sample", type=int, default=20000)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 3) // 3))
    ap.add_argument("--hours", type=float, default=0)
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--genre", action="store_true")
    ap.add_argument("--dyn-every", type=int, default=5)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--ffmpeg", default="")
    ap.add_argument("--ffprobe", default="")
    args = ap.parse_args()
    global DYN_EVERY, FORCE, FFMPEG, FFPROBE, SEED  # noqa: PLW0603
    DYN_EVERY = max(1, args.dyn_every)
    FORCE = args.force
    if args.ffmpeg:
        # either the program itself or the folder that holds ffmpeg and ffprobe
        if os.path.isdir(args.ffmpeg):
            exe = ".exe" if os.name == "nt" else ""
            FFMPEG = os.path.join(args.ffmpeg, "ffmpeg" + exe)
            FFPROBE = os.path.join(args.ffmpeg, "ffprobe" + exe)
        else:
            FFMPEG = args.ffmpeg
            sibling = os.path.join(os.path.dirname(args.ffmpeg), os.path.basename(args.ffmpeg).replace("ffmpeg", "ffprobe"))
            if os.path.exists(sibling):
                FFPROBE = sibling
    if args.ffprobe:
        FFPROBE = args.ffprobe
    FF[0] = FFMPEG
    if sys.version_info < (3, 8):
        problem("Python 3.8 or newer is needed")
    if not os.path.isdir(args.music):
        sys.exit(f"music folder not found: {args.music}")
    root, out = Path(args.music).resolve(), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        conf = subprocess.run([FFMPEG, "-hide_banner", "-buildconf"], capture_output=True, text=True, check=False).stdout
        ver = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True, check=False).stdout.split("\n")[0]
        filters = subprocess.run([FFMPEG, "-hide_banner", "-filters"], capture_output=True, text=True, check=False).stdout
        subprocess.run([FFPROBE, "-version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        sys.exit(f"cannot run ffmpeg ({FFMPEG}) or ffprobe ({FFPROBE}); put them on PATH or use --ffmpeg / --ffprobe")
    num = re.match(r"ffmpeg version n?(\d+)\.(\d+)(?:\.(\d+))?", ver)
    found = tuple(int(x) for x in num.groups(default="0")) if num else None
    if found is None or not (found == (9, 0, 1) or found[:2] == (7, 1)):
        problem(f"this is {ver.split(' Copyright')[0] or 'an unknown ffmpeg'}; the survey accepts only ffmpeg 9.0.1 "
                "(preferred) or 7.1, the versions Music Assistant ships. Point --ffmpeg at one of those")
    elif found[:2] == (7, 1):
        print("note: ffmpeg 7.1 is accepted; 9.0.1 is preferred if you have it")
    if "libsoxr" not in conf:
        problem("this ffmpeg is built without libsoxr; Music Assistant resamples with soxr, so results would differ")
    missing = [f for f in ("loudnorm", "ebur128", "astats", "aresample", "pan", "volume", "biquad", "highpass", "asplit")
               if not re.search(rf"\s{f}\s", filters)]
    if missing:
        problem(f"this ffmpeg lacks filters the survey needs: {', '.join(missing)}")
    try:
        probe_file = out / ".write_test"
        probe_file.write_text("ok")
        probe_file.unlink()
    except OSError as err:
        sys.exit(f"cannot write to the output folder {out}: {err}")
    if hasattr(os, "nice"):
        try:
            os.nice(19)
        except OSError:
            pass
    print(f"ffmpeg: {ver}")
    test_notes = selftest(out)
    if args.selftest:
        (out / "selftest.json").write_text(json.dumps({"ffmpeg": ver, "python": sys.version.split()[0],
                                                      "forced": FORCE, "startup_problems": PROBLEMS,
                                                      "selftest": test_notes}, indent=1))
        return

    SEED, state = choose_seed(out, args.seed, args.new)
    if state == "finished":
        sys.exit(f"the run with seed {SEED} in {out} is finished. Add --new to measure a different sample.")
    print(f"run: seed {SEED} ({state})")
    meta_file = out / f"meta-{SEED}.json"
    rows = scan(root, out, args.genre)
    meta = {"script": VERSION, "ffmpeg": ver, "python": sys.version.split()[0], "seed": SEED, "files": len(rows),
            "sample_target": args.sample, "dyn_every": DYN_EVERY, "variants": list(VARIANTS),
            "selftest": test_notes, "forced": FORCE, "startup_problems": PROBLEMS,
            "started": time.strftime("%Y-%m-%d %H:%M")}
    meta_file.write_text(json.dumps(meta, indent=1))
    if args.sample <= 0:
        return
    picked = pick_sample(rows, args.sample, out)
    paths = json.loads((out / "paths.local.json").read_text())
    res = out / f"results-{SEED}.jsonl"
    done = set()
    if res.exists():
        for line in res.open():
            try:
                done.add(json.loads(line)["id"])
            except (ValueError, KeyError):
                continue  # a line cut off by a hard stop; that track is simply measured again
    todo = [p for p in picked if p["id"] not in done]
    print(f"measure: {len(todo):,} to do, {len(done):,} already done, {args.jobs} at a time")
    t0, n = time.time(), 0
    deadline = t0 + args.hours * 3600 if args.hours else None
    timed_out, failed = False, 0
    meter(len(done), len(picked), 0, t0, 0)
    with res.open("a") as fh, ThreadPoolExecutor(args.jobs) as ex:
        # hand out tracks one at a time: a track is started only while time remains, and a stop
        # leaves at most --jobs tracks unfinished
        queue, running = iter(todo), set()
        try:
            while True:
                while len(running) < args.jobs and not timed_out:
                    if deadline and time.time() > deadline:
                        timed_out = True
                        break
                    p = next(queue, None)
                    if p is None:
                        break
                    running.add(ex.submit(measure, p, root, paths[p["id"]]))
                if not running:
                    break
                # on a terminal wake up every second so the clock in the progress line keeps moving
                finished, running = futures_wait(running, timeout=1 if TTY else None, return_when=FIRST_COMPLETED)
                for fut in finished:
                    row = fut.result()
                    fh.write(json.dumps(row) + "\n")
                    fh.flush()
                    n += 1
                    failed += "error" in row
                    if not TTY and n % 25 == 0:
                        rate = n / (time.time() - t0)
                        print(f"measure: {n:,}/{len(todo):,}  {rate * 3600:.0f} tracks/h  "
                              f"about {(len(todo) - n) / rate / 3600:.1f} h left", flush=True)
                meter(len(done) + n, len(picked), n, t0, failed)
            meter(len(done) + n, len(picked), n, t0, failed, end=True)
        except KeyboardInterrupt:
            print("\nstopping; run the same command again to continue")
            try:
                ex.shutdown(wait=False, cancel_futures=True)
            except TypeError:  # Python 3.8
                ex.shutdown(wait=False)
    left = len(todo) - n
    meta.update(measured=len(done) + n, remaining=left, finished=time.strftime("%Y-%m-%d %H:%M"))
    meta_file.write_text(json.dumps(meta, indent=1))
    if timed_out and left:
        print(f"time limit reached with {left:,} tracks left; run the same command again to continue")
    print(f"done: {len(done) + n:,} tracks measured. Send back: scan.jsonl.gz, sample-{SEED}.jsonl, "
          f"results-{SEED}.jsonl, meta-{SEED}.json (not paths.local.json, which holds your file names).")


if __name__ == "__main__":
    main()
