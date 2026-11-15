# Protected files

Uploads (field photos, measurement files, rasters, analysis scripts) and maintenance results (database backups, exports) are stored under `PROTECTED_MEDIA_ROOT` (default: `protected_media/` in the project directory), not under `MEDIA_ROOT`. They reach a browser only through `/files/…`, which checks the user's role and project permission. Backups are for superusers only.

Keep `PROTECTED_MEDIA_ROOT` outside every directory the web server serves. `python manage.py check` reports an error if it lies inside `MEDIA_ROOT` or `STATIC_ROOT`, and `check --deploy` warns while protected files are still left under `MEDIA_ROOT`; `python manage.py move_protected_media` moves them.

## Letting the web server send the files

By default Django sends the files itself. To let the web server send them after Django's permission check, set `PROTECTED_MEDIA_SERVER` in `local_settings.py`.

Apache with [mod_xsendfile](https://tn123.org/mod_xsendfile/):

```apache
XSendFile On
XSendFilePath /srv/cgdb/protected_media
```

```python
PROTECTED_MEDIA_SERVER = "x-sendfile"
```

nginx:

```nginx
location /protected-media-internal/ {
    internal;
    alias /srv/cgdb/protected_media/;
}
```

```python
PROTECTED_MEDIA_SERVER = "x-accel-redirect"
PROTECTED_MEDIA_ACCEL_PREFIX = "/protected-media-internal/"
```
