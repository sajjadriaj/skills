#!/usr/bin/env bash
# Hooks must find the handoff by the main repo's name, also from inside a git worktree.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL: $*"; echo "$OUT"; exit 1; }
g() { git -c user.name=t -c user.email=t@t "$@"; }

g init -q -b main "$T/shop" && g -C "$T/shop" commit -q --allow-empty -m one
g -C "$T/shop" worktree add -q "$T/shop-wt" -b wt
mkdir -p "$T/h/shop" && echo "# shop" > "$T/h/shop/handoff.md"
touch -d 2000-01-01 "$T/h/shop/handoff.md"
export ASSISTANT_SKILLS_HANDOFF_ROOT="$T/h" TMPDIR="$T"

OUT="$(cd "$T/shop-wt" && bash "$REPO/hooks/session-start.sh")"
echo "$OUT" | grep -q "$T/h/shop/handoff.md" || fail "session-start missed handoff from worktree"

OUT="$(cd "$T/shop-wt" && echo '{"session_id":"s1"}' | bash "$REPO/hooks/stop.sh" 2>&1)"; RC=$?
[ $RC = 2 ] || fail "stop hook exit $RC from worktree, want 2"
echo PASS
