#!/bin/sh
# Entrypoint of the CGDB demo image (compose.demo.yml).
#   web     wait for the database, migrate, load the demo data, serve on :8000
#   daemon  run the Dagster daemon, which updates maintenance run status
#   other   run the given command, e.g. "python manage.py shell"
set -eu

mkdir -p /data/media /data/protected_media "$DAGSTER_HOME"
if [ ! -s /data/secret_key ]; then
    python -c "import secrets; print(secrets.token_urlsafe(50))" > /data/secret_key
fi
cp orchestration/dagster_home/dagster.yaml "$DAGSTER_HOME/dagster.yaml"

case "${1:-web}" in
    web)
        until pg_isready -q -h "${CGDB_DB_HOST:-db}" -p "${CGDB_DB_PORT:-5432}" -U "${CGDB_DB_USER:-cgdb}"; do
            echo "Waiting for the database..."
            sleep 1
        done
        python manage.py migrate --noinput
        python manage.py move_protected_media
        python manage.py load_demo_data
        exec python manage.py runserver 0.0.0.0:8000 --noreload
        ;;
    daemon)
        exec dagster-daemon run
        ;;
    *)
        exec "$@"
        ;;
esac
