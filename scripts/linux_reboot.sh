#!/bin/bash -e


cd "$(dirname "${BASH_SOURCE[0]}")/.."


function main {
    git pull --prune
    ./scripts/linux_install.sh
    ./scripts/linux_run.sh
}


main "$@"
