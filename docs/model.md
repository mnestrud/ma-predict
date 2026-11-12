# Model parameters explained

Both models predict the ratio `FLAC bytes / PCM bytes` of the stream Music Assistant is about to
send, from inputs that exist before the headers go out. The announced size is
`ratio x output PCM bytes per second x duration`.

Files: [`model_v1.json`](../models/model_v1.json), [`model_v2.json`](../models/model_v2.json).

## The idea

A FLAC source file already tells us how compressible the music is: its size divided by its
sample count is the number of bits each sample costs. Music Assistant re-encodes the same audio,
so the output costs about the same bits per sample, plus whatever the processing adds or removes.

## Inputs

| Input | Meaning |
|---|---|
| Source size | Size of the source file in bytes, including tags and cover art |
| Duration | Whole seconds, rounded down, as Music Assistant's library stores it |
| Source format | Bits per sample (container depth), sample rate, channels |
| Output format | Bits per sample, sample rate, channels |
| Regime | Which of five processing cases applies (below) |
| Gain | Sum of the level changes known before the headers, in dB |

## Regimes

| Regime | When | What happens to the samples |
|---|---|---|
| R0 exact | No float processing | Copied bit for bit |
| R1 padded | Float path is on, but no filter changes a sample; 24-bit output | A 16-bit source is zero-padded into 24 bits |
| R2 filled | A filter changes samples; 24-bit output | The low bits fill with real data |
| R3 dithered | Float path, 16-bit output | Requantized to 16 bits with dither |
| R4 unknown | Dynamic loudness normalization | Gain varies over the track and is not known in advance |

The float path is on when crossfade is enabled, when volume normalization is on, or when DSP is
enabled, whether or not any sample ends up changed.

## Terms shared by v1 and V2

| Term | Formula | Why |
|---|---|---|
| Duration correction | `d = duration + 0.5 s` | The stored duration is rounded down; on average half a second is lost |
| Source bits | `src_bits = size / (rate x bps/8 x channels x d) x bps` | Bits the source spends per sample |
| R0, R1 | `bits = src_bits` | Same samples, same cost |
| R2 fill | `+ max(bps_out - bps_src, 0)` | Bits added when a 16-bit source is turned into real 24-bit data |
| R3 depth cut | `- max(bps_src - 16, 0)` | Bits removed when a 24-bit source is cut to 16 |
| Gain | `+ gain_dB / 6.02` | 6.02 dB of level is one bit per sample |
| Resample | `+ c x log2(rate_src / rate_out)` when the rate goes down | Fewer samples, each less predictable |
| Channels | `x channels_src / channels_out` | A one-channel source sent as stereo costs half per output sample |
| Clamp | ratio kept within 0.02 to 1.01 | Guards against bad inputs |

## Parameters

### v1

| Parameter | Value | Basis |
|---|---|---|
| Offset, 16-bit output | 0.0371 (ratio) | Mean residual on the first 330-track study |
| Offset, 24-bit output | 0.0235 (ratio) | Same |
| Resample coefficient `c` | 2.6 | Provisional: 5 tracks, one artist |
| Fallback | 0.747 | Dynamic loudness, lossy or uncompressed sources, unknown size |

The offset is the cost of Music Assistant's fast FLAC setting (compression level 0) relative to
the encoder that made the source file.

### V2

| Parameter | Value | Status | Basis |
|---|---|---|---|
| `offset_bits` | 0.57 bits per sample | Fitted | Median residual on 50 development artists; 0.55 to 0.58 across the five folds |
| `offset_padded_bits` | 0.77 bits per sample | Fitted | Same data, 16-bit source zero-padded into 24 bits (R1); 0.76 to 0.78 across folds |
| `resample_c` | 2.6 | Provisional | 5 tracks, one artist |
| `mono_dither_bits` | 1.65 bits per sample | Provisional | One-channel source dithered to stereo (R3): the dither differs between the two output channels. Set from 24 constructed one-channel files |
| `padded_guard_bits` | 13 bits per sample | Provisional | See below |

What changed from v1:

- **Offset in bits, inside the channel factor.** v1 added a ratio offset after the channel factor,
  which over-announced one-channel sources by about 8 %.
- **Zero-padded streams get their own offset.**
- **Dynamic loudness normalization to 24-bit** is treated as R2 with gain 0. No new number.
- **Gain** now includes the DSP gain filter (its dB) and the balance filter (half its attenuation
  in dB). Parametric EQ, tone, high/low-pass and limiter are not counted.
- **Padded guard.** The model trusts the bit depth in the file header. A 24-bit file holding
  16-bit audio breaks that once gain or dither is applied (v1 was 41 to 72 % short). When a source
  deeper than 16 bits costs fewer than 13 bits per sample and its samples get changed, V2 uses
  0.747 instead. Real 24-bit tracks in the study cost at least 12.35 bits per sample; constructed
  16-in-24 files at most 12.99.

### Where V2 still uses 0.747

- Lossy or uncompressed sources (MP3, AAC, WAV, ...), or no known source size.
- Dynamic loudness normalization with 16-bit output (not measured).
- The padded guard.

## Known limits of V2

| Case | Error |
|---|---|
| 20-bit audio in a 24-bit file that costs more than 13 bits per sample | 21 to 45 % short |
| Limiter as the only filter that changes samples | 16 to 44 % long |
| Stereo file with identical channels, with gain | 44 to 50 % long; 18 % short with 16-bit output |
| Balance at 100 (one channel silent) | about twice too long |
| Low-pass at 8 kHz | 7 % long, up to 16 % |
| Old, band-limited recordings | up to 16 % short |
| A crossfade that is actually mixed into the stream | not modelled |
