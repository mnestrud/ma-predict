# Findings so far

Status 2026-11-12. Code references are Music Assistant `server`, branch `dev`, commit 21f7f90cb.

## The problem

`calculate_content_length` (`music_assistant/helpers/audio.py`) announces a FLAC stream as
`PCM size x 0.747`. For players that are sent a fixed `Content-Length`, a wrong figure means the
announced size and the real stream do not match.

## Who is affected

- Forced content length is the default for Bluesound, Google-made Chromecast audio devices
  (not groups) and Yandex Station.
- A source file size is available before the headers for local files, WebDAV, Deezer and
  feiniu_music.
- A stored loudness measurement is read only after the headers are sent, so with default settings
  a local file is on dynamic loudness normalization at header time even when a measurement exists.

## How wrong 0.747 is

- One live server's measured-size cache (633 streams): median error 8.8 %; 28 % of streams
  within 5 %.
- The library stores duration in whole seconds, rounded down: median 0.44 s lost per track. No
  ratio model can remove that; adding half a second removes the bias.
- Per setting on 330 tracks: median error 3 % to 73 %, depending on source depth and processing
  (see [comparison](comparison.md)).

## Measurement harness

- Built on Music Assistant's own functions for the ffmpeg arguments, resampling, DSP and
  normalization, running the same three ffmpeg stages.
- Byte-exact against a real server in 26 of 26 comparable cases (22 on a software renderer, 4 on
  a Sonos speaker, including crossfade enabled without a mix).
- ffmpeg 7.1 against 9.0.1: median size difference 0.016 %.
- WAV and MP3 output sizes do not depend on normalization or DSP (30 of 30 files). The model
  covers FLAC output only.
- A zero-gain volume filter and an enabled-but-empty DSP chain are bit-exact, so their 24-bit
  output is zero-padded 16-bit data.
- Music Assistant's FLAC level 0 does use stereo decorrelation: two identical channels cost the
  same as one.

## What decides the size

- The source file's own compression ratio predicts the output within about 1 to 2 % once the
  processing is accounted for.
- Processing sorts into five regimes (exact, zero-padded, filled, dithered, dynamic); see
  [model](model.md).
- Free coefficients do not beat the fixed form: fitted slopes on the source term are 0.99 to 1.01.
- One offset of about 0.57 bits per sample covers every regime except zero-padded 16 to 24 bit
  (0.77).
- Dynamic loudness normalization to 24-bit behaves like a filled stream with no gain: 0.747 is
  off by 3.0 % (16-bit sources) and 12.7 % (24-bit sources); V2 by 2.5 % and 3.2 %.

## DSP filters

Six filter types, two settings each, 30 tracks:

| Filter | Effect on size | Handling |
|---|---|---|
| Gain | exactly its level | add its dB to the gain |
| Balance (moderate) | half its attenuation | add to the gain |
| High-pass 80 Hz | none | nothing |
| Parametric EQ | within about 2 % | nothing; counting the preamp runs short when bands boost |
| Tone | 1.6 to 3.8 % | nothing |
| Low-pass 8 kHz | 7 % smaller, up to 16 % | nothing; depends on the track |
| Limiter, with gain | none | nothing |
| Limiter alone | between padded and filled | no usable rule |

Compressor, convolution, transpose, crossfeed and stereo width were not tested.

## Constructed files

- **Padded sources are the main hole.** 16- or 20-bit audio in a 24-bit file is announced 21 to
  95 % short by v1 once gain or dither touches it. The real depth is not in the file header. V2's
  guard covers the 16-bit case; 20-bit files partly escape it. None of the 330 library tracks is
  padded; how common such files are is an open question.
- **One-channel sources:** v1 4 to 18 % off, V2 1 to 3.6 %.
- **MP3 stored as FLAC:** both models within 1 to 3 %.
- **Upsampled files:** about 7 % long.

## Under-announcement tail

- On the development artists the only tracks more than 6 % short are three tracks of one 1964
  album: 14 to 16 % short.
- Cause: level 0 uses fixed predictors, while the source was encoded with linear prediction. One
  of those tracks is 19.0 MB as a source file and 25.4 MB re-encoded at level 0.
- That album has about 7.6 dB less energy above 8 kHz than a comparison track. Nothing in the
  file header marks such a recording.
- Kept as a known limit.

## Not modelled

- An applied crossfade changes the size (30 s track: +34 %).
- AAC output: under-announced by 3 to 10 % for encoder reasons, left alone.
- Source compression level: not readable before the headers; the swing between FLAC level 0 and
  8 is about 0.049 in ratio.

## Open

- Locked test artists not scored yet.
- A survey of a much larger library ([script](../flac_size_survey.py)) is planned, to set the
  provisional parameters and count padded, 20-bit and one-channel sources.
