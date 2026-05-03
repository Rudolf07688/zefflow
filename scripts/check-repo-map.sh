#!/usr/bin/env bash
# Tier-1 staleness detector for notes/repo-map/.
#
# Compares the cited-files list in notes/repo-map/.evidence.json against
# files changed since the recorded git_sha. Emits warnings only — never
# blocks the caller. Designed to be called from a pre-commit hook.
#
# Exit codes:
#   0 — fresh, or evidence missing (warns), or staleness only (warns)
#   never non-zero (we never block commits)

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
EVIDENCE="$REPO_ROOT/notes/repo-map/.evidence.json"

warn() { printf "\033[33m[repo-map]\033[0m %s\n" "$*" >&2; }
info() { printf "\033[36m[repo-map]\033[0m %s\n" "$*" >&2; }

if [ ! -f "$EVIDENCE" ]; then
  warn "no notes/repo-map/.evidence.json — repo-map has never been generated."
  warn "  run: make repo-map-rebuild"
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  warn "jq not installed; skipping staleness check."
  exit 0
fi

LAST_SHA="$(jq -r '.git_sha // empty' "$EVIDENCE")"
if [ -z "$LAST_SHA" ]; then
  warn ".evidence.json is missing 'git_sha'."
  exit 0
fi

# All currently-cited files, deduped. Trailing slashes (directory citations)
# are stripped so prefix-matching against 'git diff --name-only' works.
mapfile -t CITED < <(
  jq -r '.files_cited | to_entries[] | .value[]' "$EVIDENCE" \
    | sed 's:/*$::' \
    | sort -u
)

# Files changed since the recorded sha (committed) + currently staged + unstaged.
# We include all three so the detector fires *before* a commit lands.
# Changes to the output dir itself never count — we are checking the *inputs*
# to the repo-map, not its own pages.
mapfile -t CHANGED < <(
  {
    git diff --name-only "$LAST_SHA"..HEAD 2>/dev/null || true
    git diff --name-only --cached 2>/dev/null || true
    git diff --name-only 2>/dev/null || true
  } | sort -u | grep -Ev '^notes/repo-map/' || true
)

if [ ${#CHANGED[@]} -eq 0 ]; then
  exit 0
fi

# A cited entry hits if any changed path equals it OR is under it (dir prefix).
HIT_FILES=()
declare -A HIT_DOCS=()

for cited in "${CITED[@]}"; do
  [ -z "$cited" ] && continue
  for changed in "${CHANGED[@]}"; do
    if [ "$changed" = "$cited" ] || [[ "$changed" == "$cited"/* ]]; then
      HIT_FILES+=("$changed")
      # Find which docs cite this path and mark them stale.
      while IFS= read -r doc; do
        HIT_DOCS["$doc"]=1
      done < <(
        jq -r --arg p "$cited" '
          .files_cited
          | to_entries[]
          | select(.value | index($p))
          | .key
        ' "$EVIDENCE"
      )
      break
    fi
  done
done

if [ ${#HIT_FILES[@]} -eq 0 ]; then
  exit 0
fi

warn "repo-map is potentially STALE."
warn "  last verified at: $LAST_SHA"
warn "  changed cited paths:"
printf '    - %s\n' "${HIT_FILES[@]}" | sort -u >&2
warn "  affected docs:"
for d in "${!HIT_DOCS[@]}"; do
  warn "    - notes/repo-map/$d"
done
warn "  to refresh:  make repo-map-refresh"
warn "  to rebuild:  make repo-map-rebuild"

# Never block.
exit 0
