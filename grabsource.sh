find . -name "*.py" -type f -not -path "*/backups/*" -not -path "*/logs/*" -not -path "*/.emailagent/*" -not -path "*/.git/*" -exec sh -c 'echo "\n=== $1 ==="; cat "$1"' sh {} \; | pbcopy
