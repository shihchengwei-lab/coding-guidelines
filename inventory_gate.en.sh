#!/usr/bin/env bash
# inventory_gate (English) - UserPromptSubmit: detect "build something new" phrasing,
# remind to inventory existing assets first (don't reinvent the wheel).
# advisory: prints reminder to stdout (injected as context) on match; always exit 0.
# Note: the shell version greps the whole payload (no jq); the Python version reads
# only .prompt, which is more precise.
payload=$(cat)
if printf '%s' "$payload" | grep -Eqi 'create a|build a|add a new|write a new|implement a'; then
  cat <<'INNER'
[Inventory] "Build something new" detected -- inventory before you build (most "I need a new X" is really "I didn't find the existing X"):

1. ls/glob the relevant dirs for something with the same name/function
2. grep the keywords to see if it is already implemented
3. Ask: can I extend what exists instead of building new?
   Can extend -> extend it (one less thing to maintain)
   Genuinely absent -> then build, and note why the existing one was not enough

"Inventory first, then decide whether to build" is the first gate of subtraction discipline.
INNER
fi
exit 0
