#!/usr/bin/env bash
# OMEGA-093: GitHub-hosted runner ONLY. Disposable DB and synthetic fixture ONLY.
set -Eeuo pipefail
if [[ "${GITHUB_ACTIONS:-}" != "true" || "${RUNNER_ENVIRONMENT:-}" != "github-hosted" ||
      "${GITHUB_REPOSITORY:-}" != "mehmetcerdik457-ctrl/benim-uygulamam" ||
      ! "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ ||
      ! "${GITHUB_RUN_ATTEMPT:-1}" =~ ^[0-9]+$ ]]; then
  echo "OMEGA_OPS_ISOLATION=BLOCKED_NON_EPHEMERAL_RUNNER"
  exit 20
fi
if [[ ! "${OMEGA_TEST_DB_SENTINEL:-}" =~ ^[0-9a-f]{32}$ ||
      ${#OMEGA_DEV_DB_PASSWORD} -lt 24 ]]; then
  echo "OMEGA_OPS_ISOLATION=BLOCKED_MISSING_TEMP_CREDENTIALS"
  exit 21
fi
project="omega-ops-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT:-1}"
compose=(docker compose -p "$project" -f compose.omega.yml)
db_exec() { "${compose[@]}" exec -T db "$@"; }
# Parse rendered Compose privately; neither configuration nor credentials are printed.
"${compose[@]}" config --format json | python3 -c '
import json,sys
c=json.load(sys.stdin)
db=c["services"]["db"]
assert not db.get("ports") and not db.get("volumes"), "database must not publish/mount persistent volumes"
assert any(x.split(":")[0]=="/var/lib/postgresql/data" for x in db.get("tmpfs",[]))
assert all(c["networks"][n].get("internal") is True for n in db.get("networks",{}))
assert db.get("image")=="postgres:16-alpine", "review changed database image before running"
'
echo "OMEGA_OPS_COMPOSE_DISPOSABLE_GUARD=PASS"
cleanup() {
  # The unique project ID prevents targeting any preexisting OMEGA services.
  "${compose[@]}" --profile integration down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT
"${compose[@]}" up -d --wait --wait-timeout 120 db >/dev/null
# Sentinel is independently inserted here; migrate.py cannot create it.
db_exec psql -X -q -v ON_ERROR_STOP=1 -U omega_demo -d omega_demo -c \
  "CREATE TABLE omega_test_sentinel(marker_id integer PRIMARY KEY CHECK(marker_id=1), marker text NOT NULL); INSERT INTO omega_test_sentinel VALUES (1, '${OMEGA_TEST_DB_SENTINEL}');" >/dev/null
found="$(db_exec psql -X -At -v ON_ERROR_STOP=1 -U omega_demo -d omega_demo -c \
  'SELECT marker FROM omega_test_sentinel WHERE marker_id=1')"
[[ "$found" == "$OMEGA_TEST_DB_SENTINEL" ]] || { echo "OMEGA_OPS_SENTINEL=FAIL"; exit 22; }
echo "OMEGA_OPS_SENTINEL=PASS"
# Prove wrong marker is refused; no traceback or token is copied into logs.
if "${compose[@]}" --profile integration run --build --rm \
  -e OMEGA_TEST_DB_SENTINEL=00000000000000000000000000000000 \
  tests python -m db.migrate up >/dev/null 2>&1; then
  echo "OMEGA_OPS_WRONG_MARKER_DENIAL=FAIL"
  exit 23
fi
echo "OMEGA_OPS_WRONG_MARKER_DENIAL=PASS"
"${compose[@]}" --profile integration run --rm tests python -m db.migrate up
versions="$(db_exec psql -X -At -U omega_demo -d omega_demo -c \
  'SELECT string_agg(version::text, CHR(44) ORDER BY version) FROM omega_schema_version')"
[[ "$versions" == "1,2,3,4" ]] || { echo "OMEGA_OPS_UP=FAIL"; exit 24; }
echo "OMEGA_OPS_UP=PASS"
# Create only a new synthetic table in the disposable demo database.
db_exec psql -X -q -v ON_ERROR_STOP=1 -U omega_demo -d omega_demo -c \
  "CREATE TABLE public.omega_ops_fixture (id integer PRIMARY KEY, label text NOT NULL); INSERT INTO public.omega_ops_fixture VALUES (1,'synthetic-a'),(2,'synthetic-b');" >/dev/null
# Custom-format dump is kept only INSIDE the temporary DB container. Never upload.
db_exec pg_dump -U omega_demo -d omega_demo -Fc --no-owner --no-acl \
  -t public.omega_ops_fixture -f /tmp/omega_ops_fixture.dump
db_exec createdb -U omega_demo omega_ops_restore
db_exec pg_restore -U omega_demo -d omega_ops_restore --no-owner --no-privileges \
  /tmp/omega_ops_fixture.dump
src="$(db_exec psql -X -At -U omega_demo -d omega_demo -c \
  'SELECT md5(string_agg(id::text || label, CHR(44) ORDER BY id)) FROM public.omega_ops_fixture')"
dst="$(db_exec psql -X -At -U omega_demo -d omega_ops_restore -c \
  'SELECT md5(string_agg(id::text || label, CHR(44) ORDER BY id)) FROM public.omega_ops_fixture')"
[[ -n "$src" && "$src" == "$dst" ]] || { echo "OMEGA_OPS_RESTORE=FAIL"; exit 25; }
echo "OMEGA_OPS_BACKUP_RESTORE_SYNTHETIC=PASS"
"${compose[@]}" --profile integration run --rm tests python -m db.migrate down
remaining="$(db_exec psql -X -At -U omega_demo -d omega_demo -c \
  "SELECT count(*) FROM omega_schema_version")"
gone="$(db_exec psql -X -At -U omega_demo -d omega_demo -c \
  "SELECT to_regclass('public.omega_tasks') IS NULL")"
[[ "$remaining" == 0 && "$gone" == "t" ]] || { echo "OMEGA_OPS_DOWN=FAIL"; exit 26; }
echo "OMEGA_OPS_MIGRATION_DOWN=PASS"
"${compose[@]}" --profile integration run --rm tests python -m db.migrate up
echo "OMEGA_OPS_REAPPLY=PASS"
echo "OMEGA_OPS_PRODUCTION_DATA=NOT_ACCESSED"
echo "OMEGA_OPS_IMAGE_SCAN=NOTRUN"
echo "OMEGA_OPS_OWNER_RESTORE=NOTRUN"
