"""Security and acceptance checks for the deterministic OMEGA proof gate."""
import base64
import json
import tempfile
import unittest
from pathlib import Path
from importlib.util import find_spec
from unittest.mock import patch

from scripts.omega_acceptance_gate import EvidenceError, evaluate, _local_file, _hash_file, _bounded_json_file, main


def manifest():
    return {"schema": "omega.acceptance.v1", "requirements": [
        {"id": f"OMEGA-{i:03d}", "status": "BLOCKED", "reason": "missing independent acceptance"}
        for i in range(1, 101)]}


class ProofGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_100_unique_blocked(self):
        report = evaluate(manifest(), self.root)
        self.assertEqual((report['evaluated'], report['verified'], report['blocked']), (100, 0, 100))
        self.assertFalse(report['production_accepted'])

    def test_official_default_manifest(self):
        path = Path(__file__).resolve().parents[1] / 'evidence/omega-100-acceptance.json'
        self.assertEqual(evaluate(json.loads(path.read_text()), self.root)['verified'], 0)

    def test_duplicated_json_property_denied(self):
        bad = self.root/'bad.json'
        bad.write_text('{"schema":"omega.acceptance.v1","schema":"other"}')
        with self.assertRaisesRegex(EvidenceError, "duplicate JSON property"):
            _bounded_json_file(bad)

    def test_nested_json_property_ambiguity_denied(self):
        bad = self.root/'bad.json'
        bad.write_text('{"schema":"omega.acceptance.v1","requirements":[{"id":"A","id":"B"}]}')
        with self.assertRaisesRegex(EvidenceError, "duplicate JSON property"):
            _bounded_json_file(bad)

    def test_nonfinite_json_value_denied(self):
        bad = self.root/'bad.json'
        bad.write_text('{"schema":"omega.acceptance.v1","requirements":NaN}')
        with self.assertRaisesRegex(EvidenceError, "nonfinite JSON"):
            _bounded_json_file(bad)

    def test_unexpected_unsigned_proof_field_denied(self):
        m = manifest()
        m["requirements"][0].update(status="VERIFIED", proof={
            "source_commit":"a"*40, "test_log_path":"test.log",
            "test_log_sha256":"0"*64, "run_id":"run-1",
            "reviewer":"independent-auditor","device":"linux-x86_64",
            "owner_accepted":True,"signature":"not-signed",
            "owner_signature":"not-signed","override_release":True
        })
        report = evaluate(m,self.root)
        self.assertEqual(report["verified"],0)
        self.assertIn("unexpected unsigned",report["findings"][0]["reason"])

    def test_missing_rejected(self):
        m = manifest(); m['requirements'].pop();
        with self.assertRaises(EvidenceError): evaluate(m, self.root)

    def test_duplicate_rejected(self):
        m = manifest(); m['requirements'][99]['id'] = 'OMEGA-001'
        with self.assertRaises(EvidenceError): evaluate(m, self.root)

    def test_wrong_order_rejected(self):
        m = manifest(); m['requirements'].reverse()
        with self.assertRaises(EvidenceError): evaluate(m, self.root)

    def test_invented_101_rejected(self):
        m = manifest(); m['requirements'][0]['id'] = 'OMEGA-101'
        with self.assertRaises(EvidenceError): evaluate(m, self.root)

    def test_unrecognized_verdict_rejected(self):
        m = manifest(); m['requirements'][0]['status'] = 'ACCEPTED'
        with self.assertRaises(EvidenceError): evaluate(m, self.root)

    def test_blocked_must_have_reason(self):
        m = manifest(); m['requirements'][0]['reason'] = '  '
        with self.assertRaises(EvidenceError): evaluate(m, self.root)

    def test_signed_label_without_proof_blocked(self):
        m = manifest(); m['requirements'][0]['status'] = 'VERIFIED'
        report = evaluate(m, self.root)
        self.assertEqual(report['verified'], 0)
        self.assertIn('proof', report['findings'][0]['reason'])

    def test_unsigned_local_log_not_accepted(self):
        m = manifest(); log = self.root/'test.log'; log.write_text('PASS\n')
        m['requirements'][0].update(status='VERIFIED', proof={
            'source_commit':'a'*40, 'test_log_path':'test.log',
            'test_log_sha256':_hash_file(log),'run_id':'run-1',
            'reviewer':'auditor-A','device':'linux-x86_64',
            'owner_accepted':True,'signature':'garbage','owner_signature':'garbage'})
        r = evaluate(m, self.root)
        self.assertEqual(r['verified'],0)
        self.assertIn('not configured',r['findings'][0]['reason'])

    def test_invalid_attestation_signature_denied(self):
        m = manifest(); log=self.root/'test.log';log.write_text('PASS\n')
        key = self.root/'pub.pem';key.write_text('invalid-key')
        owner_key = self.root/'owner.pem';owner_key.write_text('invalid-key')
        m['requirements'][0].update(status='VERIFIED',proof={
            'source_commit':'a'*40,'test_log_path':'test.log',
            'test_log_sha256':_hash_file(log),'run_id':'run-1',
            'reviewer':'auditor-B','device':'linux','owner_accepted':True,
            'signature':base64.b64encode(b'fake-signature').decode(), 'owner_signature':base64.b64encode(b'fake-signature').decode()})
        self.assertEqual(evaluate(m,self.root,key,owner_key)['verified'],0)

    @unittest.skipUnless(find_spec("cryptography"), "optional Ed25519 verifier dependency unavailable")
    def test_correct_external_ed25519_signature(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        m = manifest(); log=self.root/'test.log'; log.write_text('PASS\n')
        p={'source_commit':'a'*40,'test_log_path':'test.log','test_log_sha256':_hash_file(log),
           'run_id':'run-1','reviewer':'auditor','device':'linux','owner_accepted':True}
        priv=Ed25519PrivateKey.generate();key=self.root/'pub.pem'
        owner=Ed25519PrivateKey.generate();owner_key=self.root/'owner.pem'
        key.write_bytes(priv.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
        owner_key.write_bytes(owner.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
        msg=json.dumps({'requirement_id':'OMEGA-001','proof':p},sort_keys=True,separators=(',',':')).encode()
        p['signature']=base64.b64encode(priv.sign(msg)).decode()
        p['owner_signature']=base64.b64encode(owner.sign(msg)).decode()
        m['requirements'][0].update(status='VERIFIED',proof=p)
        r=evaluate(m,self.root,key,owner_key)
        self.assertEqual((r['verified'],r['blocked']),(1,99))
        self.assertEqual(evaluate(m,self.root,key,key)['verified'],0)
        p['owner_signature'] = base64.b64encode(priv.sign(msg)).decode()
        self.assertEqual(evaluate(m,self.root,key,owner_key)['verified'],0)
        p['owner_signature']=base64.b64encode(owner.sign(msg)).decode()
        m['requirements'][1].update(status='VERIFIED',proof=p)
        self.assertEqual(evaluate(m,self.root,key,owner_key)['verified'],1)
        p['test_log_sha256']='0'*64
        self.assertEqual(evaluate(m,self.root,key,owner_key)['verified'],0)

    def test_no_owner_approval(self):
        m=manifest();m['requirements'][0].update(status='VERIFIED',proof={
            'source_commit':'a'*40,'test_log_path':'test.log','test_log_sha256':'0'*64,
            'run_id':'run','reviewer':'rev','device':'linux','owner_accepted':False,'signature':'foo','owner_signature':'foo'})
        self.assertIn('owner',evaluate(m,self.root)['findings'][0]['reason'])

    def test_traversal_denied(self):
        for name in ('../secret','/etc/passwd','a/../../tmp/x','C:\\secret','./x'):
            with self.subTest(name=name), self.assertRaises(EvidenceError): _local_file(self.root,name)

    def test_symlink_denied(self):
        (self.root/'log').write_text('123')
        (self.root/'alias').symlink_to('log')
        with self.assertRaises(EvidenceError):_local_file(self.root,'alias')

    def test_huge_log_rejected(self):
        log=self.root/'huge';log.write_bytes(b'x'*1025)
        with self.assertRaises(EvidenceError):_hash_file(log,limit_bytes=1024)

    def test_malformed_json_error_and_exit_code(self):
        inp=self.root/'in.json';inp.write_text('{')
        with patch('sys.stdout'):
            self.assertEqual(main(['--manifest',str(inp)]),2)

    def test_enforce_denies_no_100(self):
        inp=self.root/'in.json';inp.write_text(json.dumps(manifest()))
        with patch('sys.stdout'):
            self.assertEqual(main(['--manifest',str(inp),'--enforce']),1)
            self.assertEqual(main(['--manifest',str(inp)]),0)

    def test_malformed_attested_proof_does_not_crash(self):
        m=manifest();m['requirements'][0].update(status='VERIFIED',proof={
            'source_commit':'a'*40,'test_log_path':{},'test_log_sha256':'0'*64,
            'run_id':'run','reviewer':'reviewer','device':'linux',
            'owner_accepted':True,'signature':'foo','owner_signature':'foo'})
        self.assertEqual(evaluate(m,self.root)['verified'],0)


if __name__=='__main__':unittest.main()
