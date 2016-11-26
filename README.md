# pgba
PostgreSQL backup/replication automation and management scripts

Only CentOS7 is supported at the moment

    pg-basebackup.py --help
    usage: pg-basebackup.py [-h] --pg-archivecleanup PG_ARCHIVECLEANUP
                            [--pgbase-path PGBASE_PATH]
                            [--pgarchive-path PGARCHIVE_PATH] [--keep KEEP]
                            [--user USER] [--verbose]

    Create and maintain PostgreSQL base backups

    optional arguments:
      -h, --help            show this help message and exit
      --pg-archivecleanup PG_ARCHIVECLEANUP
                            path to the pg_archivecleanup binary
      --pgbase-path PGBASE_PATH
                            target path to store the base backups
      --pgarchive-path PGARCHIVE_PATH
                            path to the WAL archive
      --keep KEEP           number of backups to keep
      --user USER           username to run backups as
      --verbose             enable verbose output


    pg-initslave.sh
    Usage: ./pg-initslave.sh [-c CONFIG] [-p PORT] BACKUP-DATA-PATH TARGET

# Examples

Run following to create new base backup and cleanup the old ones. Default is to keep the 5 latest backups and associated archives.

    pg-basebackup.py --pg-archivecleanup /usr/pgsql-9.5/bin/pg_archivecleanup --verbose
    NOTICE:  pg_stop_backup complete, all required WAL segments have been archived
    INFO:__main__:Cleaning up /var/backup/pgbase/20161126040126
    INFO:__main__:Cleaning up /var/backup/pgarchive/000000010000000000000085.00000028.backup
    INFO:__main__:Running /usr/pgsql-9.5/bin/pg_archivecleanup to clean the archives created before the /var/backup/pgarchive/000000010000000000000087.00000028.backup


Run following as root on the PostgreSQL master to deploy the base backup from the /var/backup/pgbase/20161126040126 and archives from the /var/backup/pgarchive to the pgslave.example.com and point it at the local fqdn to do the streaming replication.

    cat <<EOF >/root/pg-initslave.conf
    PG_SERVICE='postgresql-9.5'
    PG_DATA='/var/lib/pgsql/9.5/data'
    PG_ARCHIVE='/var/backup/pgarchive'
    PG_MASTER=$(hostname --fqdn)
    PG_MASTER_PORT=5432

    PG_REPLICATION_USER='replicator'
    PG_REPLICATION_PASSWORD='muchsecretveryrandom'
    EOF

    pg-initslave.sh -c /root/pg-initslave.conf /var/backup/pgbase/20161126040126 pgslave.example.com