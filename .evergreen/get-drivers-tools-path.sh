#!/usr/bin/env bash
#
# This script prints the absolute path to drivers-evergreen-tools.
#
# Usage:
#   DRIVERS_TOOLS=$(path/to/get-drivers-tools-path.sh)

set -o errexit

if [ ! -z "${DRIVERS_TOOLS:-}" ]; then
    # Do not overwrite a previously set `DRIVERS_TOOLS`.
    # Some drivers overwrite `DRIVERS_TOOLS` to non-default directories.
    echo "$DRIVERS_TOOLS"
    exit 0
fi

DIR=$(dirname "${BASH_SOURCE[0]}")
if command -v realpath &> /dev/null; then
    DIR=$(realpath "$DIR")
else 
    DIR="$( cd -- "$DIR" &> /dev/null && pwd )"
fi

if [ "Windows_NT" = "${OS:-}" ]; then # Magic variable in cygwin
    DIR=$(cygpath -m "$DIR")
fi

# Find path to drivers-evergreen-tools by walking up the folder tree until there
# is a .evergreen folder in the same directory.
OUTDIR=$(dirname "$DIR")
while true; do
    if [ -d "$OUTDIR/.evergreen" ]; then 
        break
    fi

    OUTDIR=$(dirname $OUTDIR)
done

echo "$OUTDIR"
