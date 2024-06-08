#!/bin/bash -e


cd "$(dirname "${BASH_SOURCE[0]}")/.."


function main {
    python -m venv venv --prompt=nooneissafe
    find . -name site-packages -exec bash -c 'echo "../../../../" > {}/self.pth' \;
    venv/bin/pip install -U pip
    venv/bin/pip install -r requirements.txt
}


main "$@"
