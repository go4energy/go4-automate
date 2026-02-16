#!/bin/bash
# Post-Edit Quality Hook – Auto-Format nach Dateiänderungen
# Liest file_path aus stdin (JSON von Claude Code Hook)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

EXTENSION="${FILE_PATH##*.}"

case "$EXTENSION" in
  py)
    # Python: ruff check + format
    if command -v ruff &> /dev/null; then
      ruff check --fix "$FILE_PATH" 2>/dev/null || true
      ruff format "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
  vue|js|jsx)
    # Vue/JS: prettier + eslint
    if command -v npx &> /dev/null; then
      npx prettier --write "$FILE_PATH" 2>/dev/null || true
      npx eslint --fix "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
  json|yaml|yml)
    # JSON/YAML: prettier
    if command -v npx &> /dev/null; then
      npx prettier --write "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
esac

exit 0
