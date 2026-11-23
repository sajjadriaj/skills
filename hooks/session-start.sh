#!/usr/bin/env bash
# SessionStart: load always-on skills, and point at the project's handoff if one exists.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ALWAYS_ON="$(sed -n 's/^ALWAYS_ON="\(.*\)".*/\1/p' "$ROOT/install.sh")"
HANDOFF_ROOT="${ASSISTANT_SKILLS_HANDOFF_ROOT:-$HOME/workspace/handoff}"

for name in $ALWAYS_ON; do
  awk '/^---$/ && n<2 {n++; next} n>=2' "$ROOT/skills/$name/SKILL.md"
  echo
done

project="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"
doc="$HANDOFF_ROOT/$project/handoff.md"
if [ -f "$doc" ]; then
  echo "A session handoff exists for this project: $doc"
  echo "Before starting work, follow the handoff skill's Resume steps (read it, re-check stale facts with commands, summarize in <= 5 lines)."
fi
