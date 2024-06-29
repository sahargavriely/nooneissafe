#!/bin/bash -e


cd "$(dirname "${BASH_SOURCE[0]}")/.."


function main {
    touch stop
}


main "$@"
