#!/usr/bin/env bash
# Smoke test for a running demo (docker compose -f compose.demo.yml up -d).
# Logs in as demo_pi and checks the pages a first visitor will open.
# Used by .github/workflows/demo-image.yml; runs locally the same way.
set -euo pipefail

BASE="${CGDB_DEMO_URL:-http://127.0.0.1:8000}"
PASSWORD="${CGDB_DEMO_PASSWORD:-demo}"
JAR="$(mktemp)"
trap 'rm -f "$JAR"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

expect() {  # expect <path> <status> [content-type prefix]
    local result code type
    result=$(curl -s -b "$JAR" -o /dev/null -w "%{http_code} %{content_type}" "$BASE$1")
    code=${result%% *}
    type=${result#* }
    [ "$code" = "$2" ] || fail "$1 returned $code, expected $2"
    if [ -n "${3:-}" ] && [[ "$type" != "$3"* ]]; then
        fail "$1 returned $type, expected $3"
    fi
    echo "ok  $code $1"
}

token=$(curl -s -c "$JAR" -b "$JAR" "$BASE/login/" \
    | grep -o 'name="csrfmiddlewaretoken" value="[^"]*"' | head -1 | sed 's/.*value="//; s/"$//')
[ -n "$token" ] || fail "no CSRF token on the login page"

code=$(curl -s -c "$JAR" -b "$JAR" -o /dev/null -w "%{http_code}" \
    -H "Referer: $BASE/login/" \
    --data-urlencode "csrfmiddlewaretoken=$token" \
    --data-urlencode "username=demo_pi" \
    --data-urlencode "password=$PASSWORD" \
    --data-urlencode "next=/" \
    "$BASE/login/")
[ "$code" = "302" ] || fail "login returned $code, expected a redirect"
echo "ok  login as demo_pi"

expect / 200 text/html
expect /map/ 200 text/html
expect /field_data/sample/ 200 text/html
expect /analysis/grainsize/ 200 text/html
expect /api/v1/locations/map/ 200 application/json
expect /api/v1/landforms/tiles/2/2/1.mvt 200 application/x-protobuf
expect /api/v1/schema/swagger-ui/ 200 text/html

bundle=$(curl -s -b "$JAR" "$BASE/map/" | grep -o '/static/dist/[^"]*\.js' | head -1)
[ -n "$bundle" ] || fail "/map/ does not reference the built map bundle"
expect "$bundle" 200

locations=$(curl -s -b "$JAR" "$BASE/api/v1/locations/map/" | grep -o '"DEMO-[0-9][0-9]"' | sort -u | wc -l)
[ "$locations" -eq 8 ] || fail "expected 8 demo locations on the map, got $locations"
echo "ok  8 demo locations"

echo "Smoke test passed."
