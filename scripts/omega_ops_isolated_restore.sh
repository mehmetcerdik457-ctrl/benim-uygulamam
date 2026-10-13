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
temporary_password="${OMEGA_DEV_DB_PASSWORD:-}"
if [[ ! "${OMEGA_TEST_DB_SENTINEL:-}" =~ ^[0-9a-f]{32}$ ||
      ${#temporary_password} -lt 24 ]]; then
  echo "OMEGA_OPS_ISOLATION=BLOCKED_MISSING_TEMP_CREDENTIALS"
  exit 21
fi
project="omega-ops-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT:-1}"
compose=(docker compose -p "$project" -f compose.omega.yml)
db_exec() { "${compose[@]}" exec -T db "$@"; }
# Never inherit an existing project, even if the numeric run ID is accidentally reused.
if [[ -n "$(docker ps -aq --filter "label=com.docker.compose.project=$project")" ||
      -n "$(docker volume ls -q --filter "label=com.docker.compose.project=$project")" ]]; then
  echo "OMEGA_OPS_ISOLATION=BLOCKED_PROJECT_ALREADY_EXISTS"
  exit 29
fi
# Parse rendered Compose privately; neither configuration nor credentials are printed.
"${compose[@]}" config --format json | python3 -c '
import json,sys
c=json.load(sys.stdin)
db=c["services"]["db"]
assert not db.get("ports") and not db.get("volumes"), "database must not publish/mount persistent volumes"
assert any(x.split(":")[0]=="/var/lib/postgresql/data" for x in db.get("tmpfs",[]))
assert db.get("image")=="postgres:16-alpine", "review changed database image before running"
services=c["services"]
assert set(services).issubset({"api","db","tests","ingress"}), "unreviewed service"
assert {"db","api","ingress"}.issubset(services), "required service missing"
networks=c["networks"]
assert networks["isolated_demo"].get("internal") is True, "database network must remain internal"
assert networks["loopback_ingress"].get("driver")=="bridge" and networks["loopback_ingress"].get("internal") is not True, "ingress bridge required"
for name, svc in services.items():
    for forbidden in ("privileged","network_mode","pid","devices","cap_add","extra_hosts"):
        assert not svc.get(forbidden), "unsafe service configuration"
    allowed_networks = {"isolated_demo","loopback_ingress"} if name=="ingress" else {"isolated_demo"}
    assert set(svc.get("networks",{})) == allowed_networks, "unreviewed network attachment"
    mounts=svc.get("volumes",[])
    ports=svc.get("ports",[])
    if name=="ingress":
        assert svc.get("read_only") is True and svc.get("cap_drop")==["ALL"], "ingress hardening required"
        assert "no-new-privileges:true" in svc.get("security_opt",[]), "ingress privileges denied"
        assert len(mounts)==1 and type(mounts[0]) is dict, "ingress may only mount its own configuration"
        m=mounts[0]
        assert m.get("type")=="bind" and m.get("read_only") is True, "ingress mount must be read-only"
        assert m.get("target")=="/etc/nginx/nginx.conf" and str(m.get("source","")).endswith("/omega_mvi/ingress/nginx.conf"), "unexpected ingress mount"
        assert len(ports)==1 and type(ports[0]) is dict, "one loopback port only"
        p=ports[0]
        assert p.get("host_ip")=="127.0.0.1" and str(p.get("published"))=="18080" and p.get("target")==8080 and p.get("protocol","tcp")=="tcp", "unsafe ingress publication"
    else:
        assert not mounts and not ports, "non-ingress service cannot publish or mount host files"
        if name in ("api","tests"):
            assert svc.get("read_only") is True and svc.get("cap_drop")==["ALL"], "app and tests must remain hardened"
            assert "no-new-privileges:true" in svc.get("security_opt",[]), "app privileges denied"

'
echo "OMEGA_OPS_COMPOSE_DISPOSABLE_GUARD=PASS"
cleanup() {
  # The unique project ID prevents targeting any preexisting OMEGA services.
  original_status=$?
  if ! "${compose[@]}" --profile integration down --volumes --remove-orphans >/dev/null 2>&1; then
    echo "OMEGA_OPS_ISOLATED_DISPOSAL=FAIL"
    exit 27
  fi
  container_left="$(docker ps -aq --filter "label=com.docker.compose.project=$project")"
  volume_left="$(docker volume ls -q --filter "label=com.docker.compose.project=$project")"
  if [[ -n "$container_left" || -n "$volume_left" ]]; then
    echo "OMEGA_OPS_ISOLATED_DISPOSAL=FAIL"
    exit 28
  fi
  echo "OMEGA_OPS_ISOLATED_DISPOSAL=PASS"
  exit "$original_status"
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
# A deliberately truncated copy MUST be rejected before any restore.
db_exec sh -c 'head -c 12 /tmp/omega_ops_fixture.dump > /tmp/omega_ops_invalid.dump'
if db_exec pg_restore -l /tmp/omega_ops_invalid.dump >/dev/null 2>&1; then
  echo "OMEGA_OPS_INVALID_ARCHIVE_REJECTION=FAIL"
  exit 30
fi
echo "OMEGA_OPS_INVALID_ARCHIVE_REJECTION=PASS"
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
