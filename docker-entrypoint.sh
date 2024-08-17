#!/bin/bash

if [ "$1" = "web" ]; then
    exec gunicorn -w 4 -b 0.0.0.0:5000 app:app
elif [ "$1" = "migrate" ]; then
    exec flask db upgrade
elif [ "$1" = "init-script" ]; then
    while ! pg_isready -h db -U postgres; do
        sleep 1;
    done;
    sleep 10;
    exec psql -h db -U postgres -d postgres -f /app/init.sql
else
    exec "$@"
fi
