# Perfect FLAC and Tidal exact size: two experimental patches

Status 2026-11-12. Both patches are made against Music Assistant `server`, branch `dev`,
commit `e44670403`. They are experiments for trying out, not upstream pull requests. Both are
off until switched on.

| Patch | Setting | What it does |
|---|---|---|
| [`perfect-flac.patch`](../patches/perfect-flac.patch) | Settings → System → Streams → Advanced: **Perfect FLAC (experimental)** | Announces the size of a FLAC stream from the V2 estimate, then makes the stream end on exactly that byte |
| [`tidal-exact-size.patch`](../patches/tidal-exact-size.patch) | Tidal provider settings → Advanced: **Look up the exact stream size** | Gives Music Assistant the exact size of a Tidal stream, so V2 has a source size to work from |

The two are independent. With both on, Tidal tracks get Perfect FLAC too.

## Try it

On a checkout of `music-assistant/server` (branch `dev`):

    patches/apply.sh /path/to/server                  # both patches
    patches/apply.sh /path/to/server perfect-flac     # one of them

As a Docker image built on an official build:

    docker build -t ma-patched --build-arg BASE=ghcr.io/music-assistant/server:nightly patches/

The base image must be a `dev` build at or after the commit in [`patches/BASE`](../patches/BASE).
The [Patches workflow](../.github/workflows/patches.yml) applies both patches to the newest
upstream `dev` every day and runs their tests; a red run means a patch needs a refresh.

## Perfect FLAC

Players that need a `Content-Length` (player setting "HTTP profile: forced content length")
get an estimate today, and the real stream is longer or shorter than announced. With the
option on:

1. **Announce.** The size is the [V2 estimate](model.md) plus 15 %. When the same track was
   played to the end before, the measured size plus 2 % and 64 kB is used instead.
2. **Pass through.** FLAC frames go to the player unchanged while the stream cannot yet be
   known to fit.
3. **Fill.** Towards the end of the track, frames are stored again with wider sample fields
   than needed, which makes them larger without changing a sample. The last seconds are held
   back so the final frames can be sized to land on the announced byte.

No audio is added, removed or changed: the stream decodes to the same samples.

It applies only to a single track sent as FLAC (16 or 24 bit, one or two channels), without
crossfade, from a source V2 can estimate: a FLAC file or stream whose size the provider reports.
Everything else keeps its usual content length; in particular there is no Perfect FLAC on the
0.747 fallback.

### Why bytes are only added late

A frame is enlarged only by what would still be left over if every remaining frame of the track
came out as large as uncompressed audio (no FLAC frame is larger than that), counting on the
track running 5 s longer than its stated duration. So adding bytes cannot make a stream too
large that would otherwise have fitted. The price is that the added bytes sit in the last part
of the track, in frames of about the uncompressed size.

### The margin

How much must be added to V2 so that the real stream is not the larger one:

| Data | Rows | Covers 95 % | Covers 99 % | Covers every row |
|---|---|---|---|---|
| Test corpus, development artists, Music Assistant's own pipeline | 1,399 | 5.3 % | 13.9 % | 21.3 % |
| One household server, local files | 97 | 3.3 % | 8.2 % | 8.2 % |
| Same server, Tidal | 311 | 5.4 % | 8.6 % | 10.4 % |

15 % covers 99.1 % of the corpus rows. On a first play the stream is therefore about 15 % larger
than it would be; on later plays about 2 %.

### What was tested

- **Unit tests** (`tests/core/test_perfect_flac.py`, 23): 16 and 24 bit, gaps of 0 to 40 %,
  exact size and identical decoded audio (frame checksums on).
- **Offline, two real streams** (16/44.1 and 24/48), gaps of 2 to 30 % with the stated
  duration right, and 15 % with it 4 s too short or too long: exact in every case but one
  (24/48, track 4 s shorter than stated, see Limits); identical audio on ffmpeg 7.1 and 9.0.1
  in every case.
- **Real dev server, software DLNA renderer** (gmrender), stream fetched and compared:

| Case | First play: announced = sent | Later play | Audio |
|---|---|---|---|
| Local 16/44.1 → 16/44.1 (two tracks) | yes, +15.3 % and +16.8 % over the plain stream | yes, +3.7 % and +2.4 % | identical |
| Local 24/48 → 24/48 | yes, +15.7 % | yes, +2.3 % | identical |
| Local 16/44.1 → 24 bit, gain −6 dB | yes, +17.1 % | yes, +4.1 % | identical |
| Local 16/44.1 → 24 bit, parametric EQ | yes, +16.5 % | yes, +3.0 % | identical |
| Tidal 16/44.1 (with the Tidal patch) | yes, +15.1 % | yes, +2.8 % | identical |
| Tidal 24/48 (with the Tidal patch) | yes, +14.2 % | yes, +2.4 % | identical |
| Tidal 24/96 → 24/48 | not applied: V2 gives no estimate for this track, stock length used | stock | identical |

- **One Sonos speaker** (Play:3, muted) played hand-made files of this kind to the end, in an
  earlier prototype; the patch itself has not been played on a real speaker.

### Limits

- A track that runs more than 5 s longer than its stated duration can come out larger than
  announced, as it can today.
- A track that ends earlier than stated, or a 24-bit stream announced far too large, can end
  short of the announced size; the connection is then closed. Measured offline: 4 s early on a
  24/48 stream ended 154 kB short.
- A gap smaller than about 3 kB cannot be filled (a frame cannot grow by less).
- V2 is made for music. On synthetic test tones it put the size at about half the real one,
  and the stream was larger than announced.
- The enlarged frames use uncompressed residual partitions with up to 31 bits per sample, so a
  frame can be up to about twice (16 bit) or 1.3 times (24 bit) its uncompressed size. Only
  ffmpeg's decoder, GStreamer (gmrender) and one Sonos model have decoded them.
- The stream is decoded a second time inside the server to get the samples of the frames that
  are stored again.

## Tidal exact size

Tidal's API has no size field. The stream is a DASH manifest of about one small file per 4 s.
With the option on, the provider asks Tidal's file servers for the size of each part (HTTP
`HEAD`, 8 at a time) and reports the sum as the size of the source. The result is remembered
for 30 days per track, quality and format. If any part does not answer, the size stays unknown.

Measured earlier on 100 tracks: the sum took a median of 0.42 s (at 16 requests at a time), with
no failed request in about 15,000 ([details](providers.md#tidal)). In the dev-server test above,
V2 fed with this size was within 0.1 % (16 bit) and 0.7 % (24/48) of the real stream.

Tests: `tests/providers/tidal/test_streaming.py` (parsing the manifest, the sum, the cache, a
failed part, option off).

## End-to-end test lab

The [Lab workflow](../.github/workflows/lab.yml) runs
[music-assistant/end-to-end-test-lab](https://github.com/music-assistant/end-to-end-test-lab)
on GitHub's runners against upstream `dev` with both patches applied: first the lab's own
stream checks with the options off, then [one scenario](../ci/lab/test_perfect_flac.py) that
plays an album on the lab's DLNA renderer with Perfect FLAC on.

Run of 2026-11-12 (x86-64 runner, 16 min): the lab's stream checks passed on the patched build
(3 of 3, squeezelite and Sendspin players); in the scenario all three tracks were heard in order
to the end, and the server reported all three streams as ending exactly on the announced size.
The scenario measures the sizes on a first pass and runs Perfect FLAC on the second, because
the lab's tracks are synthetic tones (see Limits).
