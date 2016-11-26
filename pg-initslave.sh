#!/bin/bash

# PostgreSQL streaming replication slave initial seed tool
# Copyright (C) 2016 Sergej Alikov <sergej@alikov.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

set -eu
set -o pipefail

# Specify config file with the -c commandline argument to override the
# defaults
PG_SERVICE='postgresql'
PG_DATA='/var/lib/pgsql/9.2/data'
PG_ARCHIVE='/var/backup/pgarchive'
PG_MASTER=$(hostname --fqdn)
PG_MASTER_PORT=5432

PG_REPLICATION_USER='replicator'
PG_REPLICATION_PASSWORD=''

recovery_conf () {
    cat <<EOF
standby_mode = 'on'
primary_conninfo = 'host=${PG_MASTER} port=${PG_MASTER_PORT} user=${PG_REPLICATION_USER} password=${PG_REPLICATION_PASSWORD} sslmode=require'
trigger_file = '${PG_DATA}/failover.trigger'
EOF
}

usage () {
    cat <<EOF
Usage: ${BASH_SOURCE} [OPTIONS] BACKUP-DATA-PATH TARGET

OPTIONS
        -c, --config CONFIG      Specify configuration file
        -p, --port PORT          Specify non-standard SSH port
        -h, --help               Show help text and exit
EOF
}

abort () {
    >&2 echo "${1}"
    exit 1
}

quote () {
    printf '%q\n' "${1}"
}

main () {
    local arg port backup_path target sshargs

    while [[ "${#}" -gt 0 ]]; do
        case "${1}" in
            -c|--config)
                source "${2}"
                shift
                ;;
            -p|--port)
                port="${2}"
                shift
                ;;
            -h|--help)
                usage
                return 0
                ;;
            *)
                if [[ -z "${backup_path:-}" ]]; then
                    backup_path="${1}"
                elif [[ -z "${target:-}" ]]; then
                    target="${1}"
                fi
                ;;
        esac

        shift
    done

    if [[ -z "${backup_path:-}" ]]; then
        >&2 usage
        abort "Please specify the location of the base backup"
    fi

    if [[ -z "${target:-}" ]]; then
        >&2 usage
        abort "Please specify the target ([user@]host)"
    fi

    [[ -f "${backup_path}/backup_label" ]] || abort "${backup_path} does not contain a PostgreSQL base backup"

    sshargs=("${target}" ${port:+-p "${port}"})

    ssh "${sshargs[@]}" systemctl stop "${PG_SERVICE}"

    rsync -a -X -A --exclude postgresql.conf --exclude pg_hba.conf --delete "${backup_path}" "${target}${port:+:${port}}:${PG_DATA}"

    rsync -a -X -A --exclude "*.backup" "${PG_ARCHIVE}" "${target}${port:+:${port}}:${PG_DATA}/pg_xlog"

    recovery_conf | ssh "${sshargs[@]}" "umask 0077; cat >${PG_DATA}/recovery.conf"

    ssh "${sshargs[@]}" "chown postgres:postgres $(quote "${PG_DATA}/recovery.conf")"

    ssh "${sshargs[@]}" systemctl start "${PG_SERVICE}"
}


if [[ "${0}" = "${BASH_SOURCE}" ]]; then
    main "${@}"
fi
