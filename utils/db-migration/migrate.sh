#!/bin/bash

function dump_sqlite_data()
{
    file_name=$1

    
# Three different ways to do this, the last one seems the safest

#    sqlite3 $file_name '.dump' |
#        grep '^INSERT INTO' |
#        sed -E 's/^INSERT INTO "([^"]+)"/INSERT INTO \1/'

#    sqlite3 $file_name '.dump' |
#        grep -v '^CREATE TABLE' |
#        grep -v '^BEGIN TRANSACTION;$' |
#        grep -v '^COMMIT;$' |
#        sed -E 's/^INSERT INTO "([^"]+)"/INSERT INTO \1/'

    tables="cluster_pool host_pool image_pool network_pool vm_pool history host_shares leases user_pool"

    echo '' > data.sql

    for table in $tables; do
        echo -e ".mode insert $table\nselect * from $table;" |
            sqlite3 $file_name >> data.sql
    done
    
}

function populate_tables()
{
    host=$1
    port=$2
    user=$3
    database=$4

    cat mysql_base.sql data.sql | 
        mysql -h $host -P $port -u $user -p $database < data.sql
}

# The useful parameters

HOST=127.0.0.1
PORT=8889
USER=oneadmin
DATABASE=opennebula

dump_sqlite_data one.db > data.sql
populate_tables $HOST $PORT $USER $DATABASE



