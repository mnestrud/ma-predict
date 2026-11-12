# Predictive Encoding for Music Assistant Stream Size Estimation

Work in progress: a better estimate of the FLAC stream size that
[Music Assistant](https://github.com/music-assistant/server) announces in the HTTP
`Content-Length` header, to replace the fixed factor 0.747.

- [Findings so far](docs/findings.md)
- [Comparison: 0.747 vs v1 vs V2](docs/comparison.md)
- [Model parameters explained](docs/model.md)
- [Source size per provider, and V2 against a live server's measured sizes](docs/providers.md)
- Model files: [v1](models/model_v1.json), [V2](models/model_v2.json)
- Survey script: [flac_size_survey.py](flac_size_survey.py)

## Survey script usage

```
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

```

## Scope

The estimate matters only for players that Music Assistant sends a fixed `Content-Length`.
As of Music Assistant `server` branch `dev`, commit 21f7f90cb:

| Player | Fixed length |
|---|---|
| Bluesound | always (setting hidden) |
| Chromecast, Google-made, not a group | by default |
| Yandex Station | always (required) |
| Any other player | only when the user sets its HTTP profile to forced content length |

Not in scope: Chromecast groups and non-Google Cast devices, Squeezelite, Home Assistant players
and Raumfeld, which are never sent a fixed length by default.

The work covers FLAC output only, and applies when the source file size is known before the
headers are sent (local files, WebDAV, Deezer, feiniu_music; see
[Source size per provider](docs/providers.md)).

## References

Two papers on predicting encoder output size, used for the study design:

- Telili, Hamidouche, Amirpour, Fezza, Morin, Timmerer (2023).
  *Convex Hull Prediction Methods for Bitrate Ladder Construction: Design, Evaluation, and Comparison.*
  https://arxiv.org/abs/2310.15163
- Premkumar, Rajendran, Menon, Herglotz (2026).
  *Content-Driven Frame-Level Bit Prediction for Rate Control in Versatile Video Coding.*
  https://arxiv.org/abs/2602.06242

Papers citing the first one, read for modelling practice (grouped and repeated cross-validation,
checking a closed-form model on a mixed population, limiting the cost of a wrong prediction):

- Xiong, Chen, Wei, Wu, Sethuraman (2026). *Dynamic resolution switching for live streaming.*
  https://arxiv.org/abs/2605.15490
- Reznik (2026). *A Quantization Problem Posed by Adaptive Streaming.*
  https://arxiv.org/abs/2609.03745
- Soltanayev, Zisimopoulos, Anam, Kung, Katsenou, Andreopoulos (2025).
  *Content Adaptive Encoding For Interactive Game Streaming.*
  https://arxiv.org/abs/2511.22327
