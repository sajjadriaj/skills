#!/usr/bin/env bash
# Install assistant-skills into Claude Code, Codex, pi and (per project) Cursor.
# Usage: ./install.sh [--uninstall] [--cursor <project-dir>] [--skip <host>]...
set -euo pipefail

ALWAYS_ON="clear-response prove-it"   # skills that load every session

REPO="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
UNINSTALL=0
CURSOR_DIR=""
SKIP=" "
while [ $# -gt 0 ]; do
  case "$1" in
    --uninstall) UNINSTALL=1 ;;
    --cursor) CURSOR_DIR="${2:?--cursor needs a project dir}"; shift ;;
    --skip) SKIP="$SKIP${2:?--skip needs a host} "; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

body() { awk '/^---$/ && n<2 {n++; next} n>=2' "$1"; }                  # SKILL.md without frontmatter
description() { sed -n 's/^description: *//p' "$1" | head -1; }
is_always_on() { case " $ALWAYS_ON " in *" $1 "*) return 0 ;; esac; return 1; }

# Rewrite in place via cat (keeps symlinks and permissions of the user's file).
rewrite() { local f="$1" tmp; tmp="$(mktemp)"; cat > "$tmp"; cat "$tmp" > "$f"; rm -f "$tmp"; }

remove_block() {  # file name; refuses (returns 1) if a start marker has no end marker
  [ -f "$1" ] || return 0
  local s="<!-- assistant-skills:$2:start -->" e="<!-- assistant-skills:$2:end -->"
  if grep -aqxF -- "$s" "$1" && ! awk -v s="$s" -v e="$e" '$0==s {o=1} $0==e && o {o=0} END {exit o}' "$1"; then
    echo "warn: $1 has an unterminated $2 block, left alone; fix markers by hand"
    return 1
  fi
  awk -v s="<!-- assistant-skills:$2:start -->" -v e="<!-- assistant-skills:$2:end -->" \
    '$0==s {skip=1; next} $0==e {skip=0; next} !skip' "$1" | rewrite "$1"
}

add_block() {  # file name skill_md
  remove_block "$1" "$2" || return 0
  [ -s "$1" ] && [ "$(tail -c1 "$1")" != "" ] && echo >> "$1"
  { echo "<!-- assistant-skills:$2:start -->"; body "$3"; echo "<!-- assistant-skills:$2:end -->"; } >> "$1"
}

remove_line() {  # file line
  [ -f "$1" ] || return 0
  { grep -avxF -- "$2" "$1" || true; } | rewrite "$1"
}

add_line() {  # file line
  touch "$1"
  grep -aqxF -- "$2" "$1" && return 0
  [ -s "$1" ] && [ "$(tail -c1 "$1")" != "" ] && echo >> "$1"
  echo "$2" >> "$1"
}

link_skill() {  # skills_dir name
  local target="$1/$2" src="$REPO/skills/$2"
  if [ "$UNINSTALL" = 1 ]; then
    [ -L "$target" ] && [ "$(readlink "$target")" = "$src" ] && rm "$target"
    return 0
  fi
  mkdir -p "$1"
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$src" ]; then return 0
  elif [ -e "$target" ] || [ -L "$target" ]; then echo "warn: $target exists and is not our symlink, left alone"
  else ln -s "$src" "$target"; fi
}

# host: label root skills_dir always_on_kind always_on_file
install_host() {
  local label="$1" root="$2" skills="$3" kind="$4" file="$5" dir name md
  case "$SKIP" in *" $label "*) echo "skip: $label (--skip)"; return ;; esac
  if [ ! -d "$root" ]; then echo "skip: $label (not installed)"; return; fi
  for dir in "$REPO"/skills/*/; do
    name="$(basename "$dir")"; md="$dir/SKILL.md"
    [ -f "$md" ] || continue
    link_skill "$skills" "$name"
    is_always_on "$name" || continue
    case "$kind:$UNINSTALL" in
      import:0) case "$REPO" in *[[:space:]]*) echo "warn: repo path has a space; @import can't load it, move the repo to enable always-on for $label"; continue ;; esac
                add_line "$file" "@$REPO/skills/$name/SKILL.md" ;;
      import:1) remove_line "$file" "@$REPO/skills/$name/SKILL.md" ;;
      block:0)  add_block "$file" "$name" "$md" ;;
      block:1)  remove_block "$file" "$name" || true ;;
    esac
  done
  echo "ok: $label"
}

install_host claude "$HOME/.claude"    "$HOME/.claude/skills"    import "$HOME/.claude/CLAUDE.md"
install_host codex  "$HOME/.codex"     "$HOME/.codex/skills"     block  "$HOME/.codex/AGENTS.md"
install_host pi     "$HOME/.pi/agent"  "$HOME/.pi/agent/skills"  block  "$HOME/.pi/agent/AGENTS.md"

if [ -n "$CURSOR_DIR" ]; then
  for md in "$REPO"/skills/*/SKILL.md; do  # always-on skills apply every chat; the rest load when their description matches
    dir="$(dirname "$md")"; name="$(basename "$dir")"; mdc="$CURSOR_DIR/.cursor/rules/$name.mdc"
    if [ "$UNINSTALL" = 1 ]; then rm -f "$mdc"; continue; fi
    always=false; is_always_on "$name" && always=true
    mkdir -p "$(dirname "$mdc")"
    { echo "---"; echo "description: $(description "$md")"; echo "alwaysApply: $always"; echo "---"
      body "$md" | sed "s|<skill-dir>|$dir|g; s|\`template.svg\` (same folder)|\`$dir/template.svg\`|"; } > "$mdc"
  done
  echo "ok: cursor ($CURSOR_DIR)"
fi
