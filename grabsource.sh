#!/bin/bash
find . -name "*.py" -type f -not -path "*/backups/*" -not -path "*/logs/*" -not -path "*/.emailagent/*" -not -path "*/.git/*"  -not -path "*/tests*" -not -path "*/tools" -not -path "*/utils*"  -not -path "*/email*" -exec sh -c 'echo "\n=== $1 ==="; cat "$1"' sh {} \; | pbcopy
