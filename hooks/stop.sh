#!/usr/bin/env bash
# Stop: once per session, if commits landed today but the project's handoff is older, ask to update it.
INPUT="$(cat)"
SESSION="$(printf '%s' "$INPUT" | sed -n 's/.*"session_id" *: *"\([^"]*\)".*/\1/p')"
printf '%s' "$INPUT" | grep -q '"stop_hook_active" *: *true' && exit 0
MARK="${TMPDIR:-/tmp}/assistant-skills-handoff-asked-${SESSION:-none}"
[ -e "$MARK" ] && exit 0

HANDOFF_ROOT="${ASSISTANT_SKILLS_HANDOFF_ROOT:-$HOME/workspace/handoff}"
top="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
common="$(git rev-parse --path-format=absolute --git-common-dir)"  # main repo, also from a worktree
doc="$HANDOFF_ROOT/$(basename "$(dirname "$common")")/handoff.md"
[ -f "$doc" ] || exit 0
today="$(date +%F)"
[ -n "$(git -C "$top" log --since="$today 00:00" --format=%h -1 2>/dev/null)" ] || exit 0
[ "$(date -r "$doc" +%F)" = "$today" ] && exit 0

touch "$MARK"
echo "Commits landed today but $doc was last updated $(date -r "$doc" +%F). Ask the user once whether to update the handoff now (handoff skill: Write/update, then Audit). Don't update it without a yes." >&2
exit 2
