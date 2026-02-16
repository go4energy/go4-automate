#!/bin/bash
# Pre-Bash Firewall – blockiert gefährliche Befehle
# Liest den Command aus stdin (JSON von Claude Code Hook)

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

# Gefährliche Patterns prüfen
check_blocked() {
  local pattern="$1"
  local message="$2"
  if echo "$COMMAND" | grep -qiE "$pattern"; then
    echo "{\"decision\": \"block\", \"reason\": \"$message\"}"
    exit 2
  fi
}

check_blocked "rm\s+-rf\s+/" "rm -rf auf Root-Verzeichnisse ist verboten."
check_blocked "rm\s+-rf\s+\." "rm -rf auf das aktuelle Verzeichnis ist verboten."
check_blocked "git\s+reset\s+--hard" "git reset --hard ist verboten. Nutze git stash oder erstelle einen neuen Commit."
check_blocked "git\s+push\s+--force\s+(origin\s+)?main" "Force-Push auf main ist verboten."
check_blocked "git\s+push\s+-f\s+(origin\s+)?main" "Force-Push auf main ist verboten."
check_blocked "DROP\s+(DATABASE|TABLE)" "DROP DATABASE/TABLE ist verboten. Nutze Alembic Migrationen."
check_blocked "chmod\s+777" "chmod 777 ist verboten. Nutze minimale Berechtigungen (755/644)."
# pip install ohne -r blockieren (aber pip install -r erlauben)
if echo "$COMMAND" | grep -qiE "pip\s+install" && ! echo "$COMMAND" | grep -qiE "pip\s+install\s+-[rq]*r"; then
  echo '{"decision": "block", "reason": "Direkte pip install ist verboten. Füge das Package in requirements.txt hinzu und nutze pip install -r requirements.txt."}'
  exit 2
fi

# Alles OK
exit 0
