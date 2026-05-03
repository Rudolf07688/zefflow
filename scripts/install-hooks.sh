#!/usr/bin/env bash
# Install repo-local git hooks. Idempotent.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_DIR="$REPO_ROOT/.git/hooks"
HOOK="$HOOK_DIR/pre-commit"
LINE='bash "$(git rev-parse --show-toplevel)/scripts/check-repo-map.sh" || true'

mkdir -p "$HOOK_DIR"

if [ ! -f "$HOOK" ]; then
  cat >"$HOOK" <<'EOF'
#!/usr/bin/env bash
# Repo hooks. Add commands below; each MUST be tolerant (`|| true`).
EOF
fi

if ! grep -Fq "$LINE" "$HOOK"; then
  printf '\n# repo-map staleness detector (non-blocking)\n%s\n' "$LINE" >>"$HOOK"
fi

chmod +x "$HOOK" "$REPO_ROOT/scripts/check-repo-map.sh"
echo "[hooks] installed pre-commit -> scripts/check-repo-map.sh"
