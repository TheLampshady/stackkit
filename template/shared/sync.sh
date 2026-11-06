#!/usr/bin/env bash
# Copy shared/gcp_services/ into every *_service/ folder.
#
# Each service deploys from its own folder, so each keeps a copy of the shared
# Google clients. shared/gcp_services/ is the one to edit. The make targets
# that run, test, build or deploy a service run this first, so the copies are
# never out of date.
#
# A copy that differs is overwritten, unless it was edited by hand: newer than
# the shared file and, in a git repo, changed since the last commit. Then
# nothing is overwritten and this fails, naming the file, so the change can be
# moved to shared/gcp_services/. (git pull and checkout make files newer, so
# the date alone can't tell; a committed copy is safe to overwrite.)
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
src="$root/shared/gcp_services"
status=0

# Whether a copy is committed and unchanged since, so overwriting it loses nothing
committed() {
    git -C "$root" ls-files --error-unmatch -- "$1" >/dev/null 2>&1 \
        && git -C "$root" diff --quiet HEAD -- "$1" 2>/dev/null
}

for dir in "$root"/*_service; do
    [ -d "$dir" ] || continue
    name="$(basename "$dir")"
    dst="$dir/gcp_services"

    while IFS= read -r -d '' file; do
        rel="${file#"$src"/}"
        copy="$dst/$rel"
        if [ -f "$copy" ] && cmp -s "$file" "$copy"; then
            continue
        fi
        if [ -f "$copy" ] && [ "$copy" -nt "$file" ] && ! committed "$copy"; then
            echo "$name/gcp_services/$rel was edited directly." \
                "Make the change in shared/gcp_services/$rel instead, then run make sync." >&2
            status=1
            continue
        fi
        mkdir -p "$(dirname "$copy")"
        cp "$file" "$copy"
        echo "synced $name/gcp_services/$rel"
    done < <(find "$src" -name __pycache__ -prune -o -type f -print0)

    # Files deleted from shared/ go from the copies too
    [ -d "$dst" ] || continue
    while IFS= read -r -d '' copy; do
        rel="${copy#"$dst"/}"
        if [ ! -e "$src/$rel" ]; then
            rm "$copy"
            echo "removed $name/gcp_services/$rel"
        fi
    done < <(find "$dst" -name __pycache__ -prune -o -type f -print0)
done

exit "$status"
