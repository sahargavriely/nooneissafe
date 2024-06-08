#!/bin/bash -e


cd "$(dirname "${BASH_SOURCE[0]}")/.."


function main {
    venv/bin/python -m nooneissafe
}


main "$@"
