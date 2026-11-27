"""16 NEW real PostgreSQL tests of disposable mock subscription ledger.
NOT the 16 skipped V30 tests and NOT a commercial acceptance certificate.
"""
import os
import unittest
import uuid
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from sandbox.orba_mock_ledger import MockEvent, apply_mock_event, mock_entitlement_state, MockBillingError, MockReplayConflict, require_disposable_postgres

SCHEMA = (Path(__file__).resolve().parents[1] / "sandbox/orba_mock_schema.sql").read_text(encoding="utf-8")

class TestOrbaMockPostgres(unittest.TestCase):
    def setUp(self):
        self.dsn = os.environ.get("OMEGA_ORBA_MOCK_PG_DSN")
        if not self.dsn:
            raise RuntimeError("Must configure disposable PostgreSQL: OMEGA_ORBA_MOCK_PG_DSN; SKIP forbidden")
        # Deny unexpected destinations BEFORE attempting a database connection.
        # conninfo parsing understands PostgreSQL URLs and key-value DSNs.
        cfg = conninfo_to_dict(self.dsn)
        if (cfg.get("dbname") != "omega_mock"
                or cfg.get("user") != "omega_mock"
                or cfg.get("host") != "127.0.0.1"
                or cfg.get("hostaddr") not in (None, "127.0.0.1")
                or cfg.get("service") is not None):
            raise RuntimeError("unsafe database DSN; only local CI omega_mock is allowed")
        self.namespace = "omega_mock_" + uuid.uuid4().hex
        self.conn = psycopg.connect(self.dsn,autocommit=True)
        # Guard the actual authenticated database identity before DDL.
        identity = self.conn.execute("SELECT current_database(), current_user").fetchone()
        if identity != ("omega_mock", "omega_mock"):
            self.conn.close()
            raise RuntimeError("unexpected authenticated CI database identity")
        self.conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.namespace)))
        self.conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.namespace)))
        self.conn.execute(SCHEMA)

    def tearDown(self):
        if hasattr(self,"conn"):
            self.conn.close()
            with psycopg.connect(self.dsn,autocommit=True) as c:
                c.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.namespace)))

    def event(self, event_id="ev1", owner="ownerA", user="userA", product="subA", kind="MOCK_PURCHASED"):
        return MockEvent(event_id,owner,user,product,kind)

    def apply(self, event=None, owner="ownerA", **kwargs):
        return apply_mock_event(self.conn,event or self.event(),actor_owner=owner,**kwargs)

    def state(self, owner="ownerA",user="userA",product="subA"):
        return mock_entitlement_state(self.conn,owner,user,product)

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM sandbox_billing_events").fetchone()[0]

    def test_01_schema_exists(self):
        self.assertEqual(self.count(),0)
        self.assertIsNone(self.state())

    def test_02_mock_purchase_active(self):
        self.assertEqual(self.apply(),"MOCK_ACTIVE")
        self.assertEqual(self.state(),"ACTIVE")

    def test_03_pending_no_grant(self):
        self.assertEqual(self.apply(self.event(kind="MOCK_PENDING")),"PENDING_NO_GRANT")
        self.assertIsNone(self.state())

    def test_04_identical_event_idempotent(self):
        self.apply()
        self.assertEqual(self.apply(),"IDEMPOTENT_REPLAY")
        self.assertEqual(self.count(),1)

    def test_05_conflicting_same_event_denied(self):
        self.apply()
        with self.assertRaises(MockReplayConflict):
            self.apply(self.event(product="subB"))
        self.assertEqual(self.count(),1)
        self.assertIsNone(self.state(product="subB"))

    def test_06_mock_refund_revokes(self):
        self.apply()
        self.apply(self.event(event_id="ev2",kind="MOCK_REFUNDED"))
        self.assertEqual(self.state(),"INACTIVE")

    def test_07_mock_expiry_revokes(self):
        self.apply()
        self.apply(self.event(event_id="ev2",kind="MOCK_EXPIRED"))
        self.assertEqual(self.state(),"INACTIVE")

    def test_08_mock_cancel_revokes_sandbox_only(self):
        self.apply()
        self.apply(self.event(event_id="ev2",kind="MOCK_CANCELED"))
        self.assertEqual(self.state(),"INACTIVE")

    def test_09_mock_renewal_reactivates(self):
        self.apply(self.event(kind="MOCK_EXPIRED"))
        self.assertEqual(self.state(),"INACTIVE")
        self.apply(self.event(event_id="ev2",kind="MOCK_RENEWED"))
        self.assertEqual(self.state(),"ACTIVE")

    def test_10_separate_owners_isolated(self):
        self.apply()
        self.assertIsNone(self.state(owner="ownerB"))
        self.apply(self.event(event_id="ev2",owner="ownerB"),owner="ownerB")
        self.assertEqual(self.state(owner="ownerB"),"ACTIVE")
        self.assertEqual(self.count(),2)

    def test_11_wrong_actor_rejected(self):
        with self.assertRaises(PermissionError):
            self.apply(owner="ownerB")
        self.assertEqual(self.count(),0)

    def test_12_real_provider_receipt_rejected(self):
        with self.assertRaises(MockBillingError):
            self.apply(self.event(kind="PURCHASED"))
        self.assertEqual(self.count(),0)

    def test_13_bad_identifier_rejected(self):
        s="x';DROP TABLE sandbox_entitlements;--"
        with self.assertRaises(MockBillingError):
            self.apply(self.event(owner=s),owner=s)
        self.assertEqual(self.count(),0)

    def test_14_live_mode_rejected(self):
        with self.assertRaises(MockBillingError):
            self.apply(mode="PRODUCTION")
        self.assertEqual(self.count(),0)

    def test_15_transaction_rollback_on_error(self):
        with self.assertRaisesRegex(RuntimeError,"deliberate test"):
            self.apply(fault_after_insert=True)
        self.assertEqual(self.count(),0)
        self.assertIsNone(self.state())

    def test_16_cross_owner_event_collision_rejected(self):
        self.apply()
        with self.assertRaises(MockReplayConflict):
            self.apply(self.event(owner="ownerB"),owner="ownerB")
        self.assertEqual(self.count(),1)
        self.assertIsNone(self.state(owner="ownerB"))


class TestOrbaMockIsolation(unittest.TestCase):
    """Four additional DB-backed negative controls; no production semantics."""
    setUp = TestOrbaMockPostgres.setUp
    tearDown = TestOrbaMockPostgres.tearDown
    event = TestOrbaMockPostgres.event
    apply = TestOrbaMockPostgres.apply
    state = TestOrbaMockPostgres.state
    count = TestOrbaMockPostgres.count

    def test_17_mock_connection_identity(self):
        require_disposable_postgres(self.conn)
        row = self.conn.execute("SELECT current_database(), current_user, current_schema()").fetchone()
        self.assertEqual(row[0:2],("omega_mock","omega_mock"))
        self.assertEqual(row[2],self.namespace)

    def test_18_mock_write_disallowed_after_search_path_escape(self):
        self.conn.execute("SET search_path TO public")
        with self.assertRaisesRegex(MockBillingError, "disposable"):
            self.apply()
        self.conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.namespace)))
        self.assertEqual(self.count(),0)

    def test_19_mock_read_disallowed_after_search_path_escape(self):
        self.conn.execute("SET search_path TO public")
        with self.assertRaisesRegex(MockBillingError, "disposable"):
            self.state()

    def test_20_mock_write_rejects_nonrandom_test_namespace(self):
        self.conn.execute("SET search_path TO pg_catalog")
        with self.assertRaisesRegex(MockBillingError, "disposable"):
            self.apply()
