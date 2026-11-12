# Source size per provider

Status 2026-11-12. Music Assistant `server`, branch `dev`, commit 052cfee6b.

The size model needs the size of the source before the response headers are sent. This page
lists which music providers supply one today (`StreamDetails.size`) and which do not.

Method: a scan of every `StreamDetails(...)` construction under `music_assistant/providers` for
a `size=` argument. 72 providers implement `get_stream_details`; `music247e` builds its details
elsewhere and was not scanned. "Lossless" is read from the content types and quality names in
each provider's code. Only Tidal was measured against the service.

## Supplies a source size today

| Provider | Where the size comes from | Lossless | Note |
|---|---|---|---|
| filesystem_local (local, SMB, NFS) | file size from stat | yes | includes tags and cover art |
| webdav, Google Drive, OneDrive, Yandex Disk | file size from the listing, through the shared file-system base | yes | inherited; not run |
| deezer | `FILESIZE_<format>` from the track API | yes (FLAC tier) | set on 2 of its 5 constructions |
| feiniu_music | `size` from the API | yes | |
| audible, storytel | size from the API | no (audiobooks) | lossy source |

## Lossless, no size today

| Provider | Stream | Way to a size |
|---|---|---|
| tidal | DASH manifest served by MA | manifest + 1 HEAD, or sum of segment sizes (measured, below) |
| qobuz | HTTP file URL | HEAD on the URL (not tested) |
| jellyfin, emby, opensubsonic | HTTP | HEAD, or the server's own size field (not checked) |
| plex (direct play) | HTTP | same; the Opus HLS transcode path has none |
| nugs, internet_archive, ibroadcast | HTTP | HEAD (not tested) |
| qqmusic, neteasecloudmusic, zvuk_music | HTTP | HEAD (not tested) |
| kion_music, yandex_music | HTTP or custom | HEAD where HTTP (not tested) |
| apple_music | encrypted HTTP | none known |
| spotify (lossless tier), spotify_connect | custom (librespot) | none known |

Not relevant: lossy-only catalogues, podcasts and audiobooks, radio and live streams, and the
plugin sources. A lossy or endless source has no size that helps a FLAC estimate.

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
