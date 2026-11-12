#!/usr/bin/env bash
# Apply the patches to a Music Assistant server checkout (branch dev).
#   apply.sh <server checkout> [perfect-flac] [tidal-exact-size]     (no names = both)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dir="${1:?usage: apply.sh <server checkout> [perfect-flac] [tidal-exact-size]}"
shift
names=("$@")
[ ${#names[@]} -eq 0 ] && names=(perfect-flac tidal-exact-size)
for name in "${names[@]}"; do
  patch="$here/$name.patch"
  [ -f "$patch" ] || { echo "no such patch: $name" >&2; exit 2; }
  if git -C "$dir" apply --check "$patch" 2>/dev/null; then
    git -C "$dir" apply "$patch"
  else
    # the checkout moved on since the patch was made: let git merge it
    git -C "$dir" apply --3way "$patch"
  fi
  python3 "$here/merge_translations.py" "$dir/music_assistant/translations/en.json" "$here/strings/$name.json"
  echo "applied $name"
done
