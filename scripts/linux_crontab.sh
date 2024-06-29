#!/bin/bash -e


cd "$(dirname "${BASH_SOURCE[0]}")/.."


function main {
    (crontab -l 2>/dev/null; echo "@reboot ${PWD}/scripts/linux_reboot.sh") | crontab
}


main "$@"
