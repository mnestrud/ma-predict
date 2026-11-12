# Source size per provider

Status 2026-11-12. Music Assistant `server`, branch `dev`, commit 052cfee6b.

The size model needs the size of the source before the response headers are sent. This page
lists which music providers supply one today (`StreamDetails.size`) and which do not.

Method: a scan of every `StreamDetails(...)` construction under `music_assistant/providers` for
a `size=` argument. 72 providers implement `get_stream_details`; `music247e` builds its details
elsewhere and was not scanned. "Lossless" is read from the content types and quality names in
each provider's code. Only Tidal was measured against the service.

## Checklist

- **Available now**: the provider already sets `StreamDetails.size`.
- **Available with provider update**: the service can give a size, the provider does not
  pass it on yet. `yes` = measured against the service; `expected` = follows from how the
  provider streams (a plain HTTP file URL), not tested, needs an account.
- **Unavailable**: no known way to a size before the stream starts.

| Provider | Lossless | Available now | Available with provider update | Unavailable | How / note |
|---|---|---|---|---|---|
| filesystem_local (local, SMB, NFS) | yes | yes | | | file size from stat; includes tags and cover art |
| webdav | yes | yes | | | size from the listing, through the shared file-system base; not run |
| Google Drive, OneDrive, Yandex Disk | yes | yes | | | same shared base; not run |
| deezer | yes (FLAC tier) | yes | | | `FILESIZE_<format>` from the track API; set on 2 of its 5 constructions |
| feiniu_music | yes | yes | | | `size` from the API |
| audible, storytel | no (audiobooks) | yes | | | size from the API; lossy source |
| tidal | yes | | yes | | manifest + 1 HEAD, or sum of segment sizes; measured on 100 tracks (below) |
| internet_archive | sometimes | | yes | | the metadata API the provider already calls has `size` per file; HEAD gives the same number (19 of 19 FLAC files, no login) |
| phishin | no (MP3) | | yes | | HEAD on the MP3 URL returns `Content-Length` (4 of 4, no login); lossy source |
| qobuz | yes | | expected | | HTTP file URL: HEAD |
| jellyfin, emby, opensubsonic | yes | | expected | | HTTP: HEAD, or the server's own size field (not checked) |
| plex, direct play | yes | | expected | | HTTP: HEAD |
| nugs, ibroadcast | sometimes | | expected | | HTTP: HEAD |
| qqmusic, neteasecloudmusic, zvuk_music | FLAC tiers | | expected | | HTTP: HEAD |
| kion_music, yandex_music | FLAC tiers | | expected | | HEAD where the stream is HTTP; their custom streams unknown |
| plex, transcode | no (Opus HLS) | | | yes | transcoded on the fly |
| apple_music | yes (ALAC) | | | yes | encrypted HTTP |
| spotify, spotify_connect | lossless tier | | | yes | audio comes through librespot, no file URL |

Not listed: lossy-only catalogues (ytmusic, soundcloud, bandcamp, pandora, musicme, nicovideo),
podcasts, radio and live streams, and the plugin sources. A lossy or endless source has no size
that helps a FLAC estimate.

Probes without a login, 2026-11-12: Internet Archive, 19 FLAC files from 12 items (HEAD 200 after
one redirect, `Content-Length` equal to the metadata `size`, ranged GET answered 206 with the
same total); phish.in, 4 tracks.

## Tidal

No Tidal API field carries a stream size. The stream is a DASH manifest (FLAC in fMP4, segments
of about 4 s), at 16-bit as well as hi-res. Two ways to a size, both using the manifest Music
Assistant already fetches and HEAD requests to the segment URLs:

| | A. Manifest + last segment | B. Segment sum |
|---|---|---|
| Requests | 1 HEAD (last segment) | 1 HEAD per segment + init (25-208) |
| Time | one round trip | median 0.42 s, max 1.69 s at 16 parallel |
| Result vs B | -118 to -4 bytes, median -34 | exact |

The manifest's `bandwidth` is the mean of the per-segment bitrates (init segment excluded,
truncated to an integer), so the short last segment weighs as much as a full one and
`bandwidth x duration` is off by up to 3.35 %. With n segments, full segment duration d and
last segment duration d_last from `SegmentTimeline`:

    full = d * (n * bandwidth / 8 - last_bytes / d_last)
    size = init_bytes + full + last_bytes

`init_bytes` was 623 (16-bit) or 619 (24-bit) in every stream.

Sample: 100 tracks from one account, 63 artists, 64-828 s, each at `LOSSLESS` and
`HI_RES_LOSSLESS`; 196 of 200 measured (4 rate-limited), 40 of them 24-bit.

Limits: B was not checked against a full download. A assumes equal-length segments plus one
short last segment. The residual of A exceeds integer truncation on 86 of 196 streams; the
cause is not established. The size is that of Tidal's source container, not of Music
Assistant's output stream.
