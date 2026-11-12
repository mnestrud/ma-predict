# A Music Assistant server image with the patches applied.
#   docker build -t ma-patched --build-arg BASE=ghcr.io/music-assistant/server:nightly patches/
#   --build-arg PATCHES="perfect-flac"   to apply only some (default: both)
# BASE must be a build of branch dev at or after the commit in patches/BASE.
ARG BASE=ghcr.io/music-assistant/server:nightly

FROM ${BASE} AS locate
RUN cp -r "$(python -c 'import music_assistant, os; print(os.path.dirname(music_assistant.__file__))')" /ma

FROM alpine:3.22 AS patched
RUN apk add --no-cache git python3
ARG PATCHES="perfect-flac tidal-exact-size"
COPY --from=locate /ma /work/music_assistant
COPY . /patches
RUN cd /work && for name in $PATCHES; do \
      git apply --include='music_assistant/*' "/patches/$name.patch" && \
      python3 /patches/merge_translations.py music_assistant/translations/en.json "/patches/strings/$name.json" || exit 1; \
    done

FROM ${BASE}
COPY --from=patched /work/music_assistant /ma-patched
RUN cp -r /ma-patched/. "$(python -c 'import music_assistant, os; print(os.path.dirname(music_assistant.__file__))')"/ \
    && rm -rf /ma-patched
