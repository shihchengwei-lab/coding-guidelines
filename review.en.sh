#!/usr/bin/env bash
payload=$(cat)
if echo "$payload" | grep -Eq '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
  exit 0
fi

cat >&2 <<'INNER'
[Simplicity] Would a senior engineer call this diff too complex?
- Any abstractions written for one-shot code?
- Any unrequested flexibility/configuration?
- Any handling of errors that can't actually happen?

[Scope] Can every changed line be traced back to the user's original request this turn?
- Any drive-by edits to nearby code / comments / formatting?
- Any refactor of things that weren't broken?
- Any deletion of pre-existing dead code (mention only, don't delete)?

If any apply, fix it before stopping.
INNER
exit 2
