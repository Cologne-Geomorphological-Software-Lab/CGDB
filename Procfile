# Headless everywhere — no Dagster UI, in dev or production. Maintenance
# jobs are triggered via the Django admin action ("Trigger selected
# maintenance job(s)"), which submits directly to the daemon's run queue
# via `dagster job launch`; nothing depends on the UI to function.
web: python manage.py runserver
daemon: export DAGSTER_HOME=$(pwd)/orchestration/dagster_home && dagster-daemon run
