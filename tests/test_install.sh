#!/usr/bin/env bash
# Sandbox test for install.sh. Never touches the real $HOME.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
H="$ROOT/home with space"
fail() { echo "FAIL: $*"; exit 1; }

seed() {
  rm -rf "$H"; mkdir -p "$H/.claude" "$H/.codex/skills/clear-response-other"
  printf '# mine\nkeep this line\n' > "$H/.claude/CLAUDE.md"
  printf '# mine\nkeep this line\n' > "$H/.codex/AGENTS.md"
  cp "$H/.claude/CLAUDE.md" "$ROOT/claude.orig"
  cp "$H/.codex/AGENTS.md" "$ROOT/agents.orig"
}

seed
HOME="$H" "$REPO/install.sh" >/dev/null || fail "first install exited non-zero"
OUT="$(HOME="$H" "$REPO/install.sh")" || fail "second install exited non-zero"

[ -L "$H/.claude/skills/clear-response" ] || fail "claude skill not a symlink"
[ "$(readlink "$H/.claude/skills/clear-response")" = "$REPO/skills/clear-response" ] || fail "claude symlink target wrong"
[ -L "$H/.codex/skills/clear-response" ] || fail "codex skill not a symlink"
[ "$(grep -c '^@.*clear-response/SKILL.md$' "$H/.claude/CLAUDE.md")" = 1 ] || fail "claude import line count != 1"
[ "$(grep -c 'assistant-skills:clear-response:start' "$H/.codex/AGENTS.md")" = 1 ] || fail "codex block count != 1"
grep -q 'Severity' "$H/.codex/AGENTS.md" || fail "codex block missing skill body"
grep -q '^name: clear-response' "$H/.codex/AGENTS.md" && fail "codex block contains frontmatter"
grep -q 'keep this line' "$H/.claude/CLAUDE.md" || fail "claude user content lost"
grep -q 'keep this line' "$H/.codex/AGENTS.md" || fail "codex user content lost"
[ -d "$H/.codex/skills/clear-response-other" ] || fail "unrelated dir removed"
[ -e "$H/.pi" ] && fail "pi dir created though pi absent"
echo "$OUT" | grep -q 'skip: pi' || fail "no 'skip: pi' message"

HOME="$H" "$REPO/install.sh" --cursor "$ROOT/proj" >/dev/null || fail "cursor install exited non-zero"
grep -q '^alwaysApply: true$' "$ROOT/proj/.cursor/rules/clear-response.mdc" || fail "cursor mdc missing alwaysApply"

HOME="$H" "$REPO/install.sh" --uninstall --cursor "$ROOT/proj" >/dev/null || fail "uninstall exited non-zero"
cmp -s "$H/.claude/CLAUDE.md" "$ROOT/claude.orig" || fail "CLAUDE.md not restored byte-identical"
cmp -s "$H/.codex/AGENTS.md" "$ROOT/agents.orig" || fail "AGENTS.md not restored byte-identical"
[ -e "$H/.claude/skills/clear-response" ] && fail "claude symlink not removed"
[ -e "$H/.codex/skills/clear-response" ] && fail "codex symlink not removed"
[ -e "$ROOT/proj/.cursor/rules/clear-response.mdc" ] && fail "cursor mdc not removed"

# pre-existing real dir at target: warn, leave untouched
seed
mkdir -p "$H/.claude/skills/clear-response"; touch "$H/.claude/skills/clear-response/mine"
OUT="$(HOME="$H" "$REPO/install.sh")" || fail "install with real dir exited non-zero"
echo "$OUT" | grep -q 'warn:' || fail "no warn for existing real dir"
[ -f "$H/.claude/skills/clear-response/mine" ] && [ ! -L "$H/.claude/skills/clear-response" ] || fail "real dir touched"
HOME="$H" "$REPO/install.sh" --uninstall >/dev/null
[ -f "$H/.claude/skills/clear-response/mine" ] || fail "uninstall removed user's real dir"

# binary/odd bytes in CLAUDE.md must survive uninstall
seed
printf 'line1\nbad\0nul\ncaf\xe9 latin1\nline4\n' > "$H/.claude/CLAUDE.md"; cp "$H/.claude/CLAUDE.md" "$ROOT/claude.orig"
HOME="$H" "$REPO/install.sh" >/dev/null && HOME="$H" "$REPO/install.sh" --uninstall >/dev/null
cmp -s "$H/.claude/CLAUDE.md" "$ROOT/claude.orig" || fail "CLAUDE.md with NUL/latin1 not restored"

# start marker without end marker: warn, never delete user content
seed
printf '<!-- assistant-skills:clear-response:start -->\nuser later note\n' >> "$H/.codex/AGENTS.md"; cp "$H/.codex/AGENTS.md" "$ROOT/agents.orig"
OUT="$(HOME="$H" "$REPO/install.sh")"
echo "$OUT" | grep -q 'warn:.*AGENTS.md' || fail "no warn for unterminated block"
grep -q 'user later note' "$H/.codex/AGENTS.md" || fail "unterminated block: user content lost on install"
[ "$(grep -c 'assistant-skills:clear-response:start' "$H/.codex/AGENTS.md")" = 1 ] || fail "unterminated block: second clear-response block added"
head -c "$(wc -c < "$ROOT/agents.orig")" "$H/.codex/AGENTS.md" | cmp -s - "$ROOT/agents.orig" || fail "unterminated block: original content altered"
HOME="$H" "$REPO/install.sh" --uninstall >/dev/null || fail "uninstall aborted on unterminated block"
grep -q 'user later note' "$H/.codex/AGENTS.md" || fail "unterminated block: user content lost on uninstall"
[ "$(grep -c 'assistant-skills:clear-response:start' "$H/.codex/AGENTS.md")" = 1 ] || fail "unterminated block (uninstall): second clear-response block added"
head -c "$(wc -c < "$ROOT/agents.orig")" "$H/.codex/AGENTS.md" | cmp -s - "$ROOT/agents.orig" || fail "unterminated block: original content altered"

# user's own symlink at target: warn, keep it through install and uninstall
seed
mkdir -p "$H/.claude/skills" "$ROOT/elsewhere"; ln -s "$ROOT/elsewhere" "$H/.claude/skills/clear-response"
OUT="$(HOME="$H" "$REPO/install.sh")"
echo "$OUT" | grep -q 'warn:' || fail "no warn for foreign symlink"
[ "$(readlink "$H/.claude/skills/clear-response")" = "$ROOT/elsewhere" ] || fail "foreign symlink replaced"
HOME="$H" "$REPO/install.sh" --uninstall >/dev/null
[ -L "$H/.claude/skills/clear-response" ] || fail "uninstall removed foreign symlink"

# dangling foreign symlink at target: warn, don't crash
seed
mkdir -p "$H/.claude/skills"; ln -s "$ROOT/gone" "$H/.claude/skills/clear-response"
HOME="$H" "$REPO/install.sh" | grep -q 'warn:' || fail "dangling symlink: no warn or crash"

# repo path with a space: claude @import can't hold it -> warn, no import line
seed
SP="$ROOT/my repo"; mkdir -p "$SP"; cp -r "$REPO/install.sh" "$REPO/skills" "$SP/"
OUT="$(HOME="$H" "$SP/install.sh")"
echo "$OUT" | grep -q 'warn:.*space' || fail "no warn for repo path with space"
grep -q '^@' "$H/.claude/CLAUDE.md" && fail "import line written for path with space"

# --skip claude leaves Claude untouched
seed
HOME="$H" "$REPO/install.sh" --skip claude | grep -q 'skip: claude (--skip)' || fail "--skip claude not honored"
[ -e "$H/.claude/skills/clear-response" ] && fail "--skip claude still linked skills"
cmp -s "$H/.claude/CLAUDE.md" "$ROOT/claude.orig" || fail "--skip claude touched CLAUDE.md"

echo PASS
