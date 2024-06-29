#!/bin/bash -e


cd "$(dirname "${BASH_SOURCE[0]}")/.."


function main {
    echo "
[Unit]
Description=No One is Safe.

[Service]
Type=simple
ExecStart=/bin/bash ${PWD}/scripts/linux_reboot.sh

[Install]
WantedBy=multi-user.target" | sudo tee /etc/systemd/system/nooneissafe.service > /dev/null
    sudo chmod 644 /etc/systemd/system/nooneissafe.service
    sudo systemctl enable nooneissafe
}


main "$@"
