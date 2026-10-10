import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest


PROJECT = Path(__file__).resolve().parents[1]


class MetadataPreparationTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=PROJECT / ".tmp")
        self.addCleanup(self.work.cleanup)
        self.output = Path(self.work.name)

    def prepare(self, payload, url=None):
        source_file = self.output / "fixture.jsonl.gz"
        source_file.write_bytes(payload)
        source = self.output / "source.json"
        source.write_text(json.dumps({
            "id": "fixture-metadata",
            "dataset": "interface-fixture",
            "kind": "item_metadata",
            "url": url or source_file.as_uri(),
            "documentation": "interface-fixture",
            "documented_fields": {
                "parent_asin": "str", "title": "str",
                "categories": "list", "description": "list",
            },
        }), encoding="utf-8")
        run = subprocess.run(
            [sys.executable, str(PROJECT / "prepare_data.py"),
             "--stage", "metadata", "--source-manifest", str(source),
             "--output-root", str(self.output)],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
        )
        return run

    def serve(self, payload, status=200, length=None, truncated_chunks=False):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(handler):
                handler.send_response(status)
                if truncated_chunks:
                    handler.send_header("Transfer-Encoding", "chunked")
                else:
                    handler.send_header("Content-Length", str(
                        len(payload) if length is None else length))
                handler.end_headers()
                if truncated_chunks:
                    handler.wfile.write(f"{len(payload):x}\r\n".encode() + payload + b"\r\n")
                else:
                    handler.wfile.write(payload)

            def log_message(handler, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{server.server_port}/metadata.gz"

    def test_full_source_includes_last_record_and_field_diagnostics(self):
        payload = gzip.compress(
            b'{"parent_asin":"FIRST","title":"Tea","categories":[]}\n'
            b'{"parent_asin":"MIDDLE","title":"Coffee","categories":null}\n'
            b'{"parent_asin":"LAST","title":"Barley grain","categories":["Grains"],"description":["Whole barley"]}\n',
            mtime=0,
        )
        run = self.prepare(payload)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(
            (report["status"], report["scan"]["records"],
             report["scan"]["first_parent_asin"], report["scan"]["last_parent_asin"]),
            ("diagnostic_complete", 3, "FIRST", "LAST"),
        )
        self.assertEqual(report["fields"]["description"]["missing"], 2)
        self.assertEqual(report["fields"]["categories"]["types"], {"list": 2, "null": 1})
        self.assertEqual((self.output / report["raw_path"]).read_bytes(), payload)

    def test_source_record_keeps_bytes_identity_and_checksum_outside_data(self):
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"ONLY","title":"Rice"}\n', mtime=0,
        ))
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["download"]["bytes"], 56)
        self.assertEqual(report["source"]["dataset"], "interface-fixture")
        self.assertTrue(report["record_path"].startswith("records/sources/"))
        recorded = json.loads((self.output / report["record_path"]).read_text("utf-8"))
        self.assertEqual(recorded["download"]["sha256"],
                         "05f8cf1d29212ac509860be316f5e49633661145870c073c5046809b63ce9785")

    def test_bad_gzip_trailer_is_diagnostic_failure_and_raw_is_preserved(self):
        good = gzip.compress(b'{"parent_asin":"ONLY","title":"Rice"}\n', mtime=0)
        bad_crc = good[:-8] + bytes([good[-8] ^ 1]) + good[-7:]
        for payload in (good[:-8], bad_crc):
            with self.subTest(payload=payload):
                run = self.prepare(payload)
                self.assertNotEqual(run.returncode, 0)
                report = json.loads(run.stdout)
                self.assertEqual(report["status"], "source_incomplete")
                self.assertFalse(report["scan"]["gzip_verified"])
                self.assertEqual((self.output / report["raw_path"]).read_bytes(), payload)

    def test_partial_or_short_http_response_cannot_pass_full_source_gate(self):
        payload = gzip.compress(b'{"parent_asin":"ONLY"}\n', mtime=0)
        for status, length in ((206, len(payload)), (200, len(payload) + 10)):
            with self.subTest(status=status, length=length):
                run = self.prepare(payload, self.serve(payload, status, length))
                report = json.loads(run.stdout)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(report["status"], "source_incomplete")
                self.assertIsNotNone(report["error"])

    def test_bad_rows_are_located_and_later_records_still_get_diagnosed(self):
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"FIRST"}\n'
            b'{"broken"\n'
            b'[]\n'
            b'\xff\n'
            b'{"parent_asin":"LAST","categories":"unexpected"}\n',
            mtime=0,
        ))
        report = json.loads(run.stdout)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(
            (report["scan"]["lines"], report["scan"]["records"],
             report["scan"]["invalid_json_rows"], report["scan"]["non_object_rows"],
             report["scan"]["last_parent_asin"]),
            (5, 2, 2, 1, "LAST"),
        )
        issues = [json.loads(line) for line in
                  (self.output / report["diagnostic_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([issue["line"] for issue in issues], [2, 3, 4])

    def test_missing_parent_and_duplicate_parent_are_audited_without_cleaning(self):
        run = self.prepare(gzip.compress(
            b'{"title":"No parent"}\n'
            b'{"parent_asin":null}\n'
            b'{"parent_asin":"REAL","categories":null}\n'
            b'{"parent_asin":"REAL","categories":"unexpected"}\n', mtime=0,
        ))
        report = json.loads(run.stdout)
        self.assertEqual(
            (report["status"], report["scan"]["records"],
             report["scan"]["invalid_parent_rows"],
             report["scan"]["unique_parents"], report["scan"]["duplicate_parent_rows"]),
            ("needs_review", 4, 2, 1, 1),
        )
        self.assertEqual(report["fields"]["parent_asin"]["missing"], 1)
        self.assertEqual(report["fields"]["categories"]["types"], {"null": 1, "str": 1})

    def test_failed_refresh_keeps_previously_verified_raw_bytes(self):
        payload = gzip.compress(b'{"parent_asin":"ORIGINAL"}\n', mtime=0)
        first = json.loads(self.prepare(payload).stdout)
        failed = self.prepare(payload[:-8])
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual((self.output / first["raw_path"]).read_bytes(), payload)

    def test_null_empty_and_undocumented_fields_are_reported_without_casting(self):
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"A","title":"","categories":[]}\n'
            b'{"parent_asin":"B","title":" ","categories":["Grains"],"description":null,"extra":{}}\n',
            mtime=0,
        ))
        report = json.loads(run.stdout)
        self.assertEqual(report["fields"]["title"]["empty"], 2)
        self.assertEqual(report["fields"]["categories"]["empty"], 1)
        self.assertEqual(
            (report["fields"]["description"]["missing"],
             report["fields"]["description"]["types"]),
            (1, {"null": 1}),
        )
        self.assertEqual(report["fields"]["extra"]["types"], {"dict": 1})

    def test_empty_gzip_cannot_be_accepted_as_a_complete_metadata_source(self):
        run = self.prepare(gzip.compress(b"", mtime=0))
        report = json.loads(run.stdout)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(report["status"], "source_incomplete")
        self.assertTrue(report["scan"]["gzip_verified"])
        self.assertEqual(report["scan"]["lines"], 0)

    def test_truncated_chunked_http_response_gets_a_machine_diagnostic(self):
        payload = gzip.compress(b'{"parent_asin":"ONLY"}\n', mtime=0)
        run = self.prepare(payload, self.serve(payload, truncated_chunks=True))
        self.assertNotEqual(run.returncode, 0)
        report = json.loads(run.stdout)
        self.assertEqual(report["status"], "source_incomplete")
        self.assertEqual(report["error"]["kind"], "IncompleteRead")
        self.assertFalse(report["scan"]["gzip_verified"])

    def test_download_failure_has_only_this_attempts_row_diagnostics(self):
        payload = gzip.compress(b'{"parent_asin":"ONLY"}\n', mtime=0)
        for previous_errors in (False, True):
            with self.subTest(previous_errors=previous_errors):
                if previous_errors:
                    self.prepare(gzip.compress(b'{"parent_asin":"OLD"}\n{broken\n', mtime=0))
                run = self.prepare(payload, self.serve(b"", status=503))
                report = json.loads(run.stdout)
                self.assertEqual(report["status"], "source_incomplete")
                self.assertEqual(report["scan"]["lines"], 0)
                issues = self.output / report["diagnostic_path"]
                self.assertTrue(issues.is_file())
                self.assertEqual(issues.read_text("utf-8"), "")


if __name__ == "__main__":
    unittest.main()
