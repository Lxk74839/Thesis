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

    def prepare(self, payload, url=None, stage="metadata", time_unit="milliseconds"):
        source_file = self.output / "fixture.jsonl.gz"
        source_file.write_bytes(payload)
        source = self.output / "source.json"
        source.write_text(json.dumps({
            "id": "fixture-" + stage,
            "dataset": "interface-fixture",
            "kind": "item_metadata" if stage == "metadata" else "user_reviews",
            "url": url or source_file.as_uri(),
            "documentation": "interface-fixture",
            "documented_fields": {
                "parent_asin": "str", "title": "str",
                "categories": "list", "description": "list",
            } if stage == "metadata" else {
                "parent_asin": "str", "asin": "str", "user_id": "str",
                "rating": "float", "title": "str", "text": "str",
                "timestamp": "int",
            },
            "time_unit": time_unit if stage == "reviews" else None,
        }), encoding="utf-8")
        arguments = ["--metadata-record", str(
            self.output / "records/sources/fixture-metadata.json"
        )] if stage == "reviews" else []
        run = subprocess.run(
            [sys.executable, str(PROJECT / "prepare_data.py"),
             "--stage", stage, "--source-manifest", str(source),
             "--output-root", str(self.output), *arguments],
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

    def test_complete_reviews_reach_last_record_and_preserve_original_bytes(self):
        self.prepare(gzip.compress(
            b'{"parent_asin":"FIRST"}\n{"parent_asin":"LAST"}\n', mtime=0))
        payload = gzip.compress(
            b'{"parent_asin":"FIRST","asin":"V1","user_id":"U1","rating":1.0,"title":" raw ","text":"","timestamp":1609459200123}\n'
            b'{"parent_asin":"LAST","asin":"V2","user_id":"U2","rating":5.0,"title":"End","text":" unchanged ","timestamp":1609459200456}\n',
            mtime=0,
        )
        run = self.prepare(payload, stage="reviews")
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual((report["stage"], report["scan"]["records"],
                          report["scan"]["last_parent_asin"]), ("reviews", 2, "LAST"))
        self.assertEqual((self.output / report["raw_path"]).read_bytes(), payload)
        self.assertEqual(report["fields"]["text"]["empty"], 1)

    def test_reviews_join_parent_metadata_without_falling_back_to_variant(self):
        self.prepare(gzip.compress(b'{"parent_asin":"A"}\n{"parent_asin":"B"}\n', mtime=0))
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"A","asin":"V1"}\n'
            b'{"parent_asin":"A","asin":"V2"}\n'
            b'{"parent_asin":"UNKNOWN","asin":"A"}\n'
            b'{"asin":"A"}\n'
            b'{"parent_asin":null,"asin":"B"}\n', mtime=0), stage="reviews")
        report = json.loads(run.stdout)
        association = report["association"]
        self.assertEqual((association["matched_review_rows"],
                          association["unmatched_review_rows"],
                          association["unmatched_unique_parents"]), (2, 1, 1))
        self.assertEqual((association["metadata_parents_with_reviews"],
                          association["metadata_parents_without_reviews"]), (1, 1))
        self.assertEqual(report["scan"]["invalid_parent_rows"], 2)
        self.assertEqual(association["asin_differs_from_parent_rows"], 3)
        self.assertEqual(report["scan"]["records"], 5)

    def test_review_milliseconds_map_to_utc_without_losing_subsecond_values(self):
        self.prepare(gzip.compress(b'{"parent_asin":"A"}\n', mtime=0))
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"A","timestamp":1609459200123}\n'
            b'{"parent_asin":"A","timestamp":1609459200000}\n', mtime=0), stage="reviews")
        time = json.loads(run.stdout)["time"]
        self.assertEqual(time["unit"], "milliseconds")
        self.assertEqual((time["min_raw"], time["min_utc"]),
                         (1609459200000, "2021-01-01T00:00:00.000+00:00"))
        self.assertEqual((time["max_raw"], time["max_utc"]),
                         (1609459200123, "2021-01-01T00:00:00.123+00:00"))
        self.assertEqual(time["nonzero_millisecond_rows"], 1)

    def test_review_anomalies_are_separate_and_do_not_stop_later_diagnosis(self):
        self.prepare(gzip.compress(b'{"parent_asin":"A"}\n', mtime=0))
        rows = [
            {"parent_asin":"A", "asin":"V", "user_id":"U", "rating":0, "title":"", "text":""},
            {"parent_asin":"A", "asin":"V", "user_id":"U", "rating":1, "title":"", "text":"", "timestamp":None},
            {"parent_asin":"A", "asin":"V", "user_id":"U", "rating":1, "title":"", "text":"", "timestamp":"1609459200000"},
            {"parent_asin":"A", "asin":"V", "user_id":"U", "rating":1, "title":"", "text":"", "timestamp":True},
            {"parent_asin":"A", "asin":"V", "user_id":"U", "rating":1, "title":"", "text":{}, "timestamp":10**30},
            {"parent_asin":"A", "rating":5, "title":"", "text":"ok", "timestamp":1609459200000},
        ]
        body = ("\n".join(json.dumps(row) for row in rows) +
                '\n{broken\n[]\n{"parent_asin":"A","asin":"V","user_id":"U","rating":1,"title":"End","text":"valid","timestamp":1609459200123}\n').encode()
        run = self.prepare(gzip.compress(body, mtime=0), stage="reviews")
        self.assertNotEqual(run.returncode, 0)
        report = json.loads(run.stdout)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual((report["scan"]["lines"], report["scan"]["records"],
                          report["scan"]["invalid_json_rows"], report["scan"]["non_object_rows"]), (9, 7, 1, 1))
        self.assertEqual(report["time"]["invalid_reasons"],
                         {"missing":1, "null":1, "not_integer":2, "unrepresentable":1})
        self.assertEqual(report["time"]["valid_rows"], 2)
        self.assertEqual(report["review_diagnostics"]["invalid_rating_rows"], 1)
        self.assertEqual(report["review_diagnostics"]["invalid_asin_rows"], 1)
        self.assertEqual(report["review_diagnostics"]["invalid_user_rows"], 1)
        self.assertEqual(report["review_diagnostics"]["invalid_text_rows"], 1)
        self.assertEqual(report["fields"]["timestamp"]["missing"], 1)
        self.assertEqual(report["time"]["max_line"], 9)

    def test_review_join_rejects_metadata_bytes_changed_since_verified_record(self):
        metadata = json.loads(self.prepare(gzip.compress(
            b'{"parent_asin":"A"}\n', mtime=0)).stdout)
        (self.output / metadata["raw_path"]).write_bytes(gzip.compress(
            b'{"parent_asin":"OTHER"}\n', mtime=0))
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"A","timestamp":1609459200000}\n', mtime=0), stage="reviews")
        self.assertNotEqual(run.returncode, 0)
        report = json.loads(run.stdout)
        self.assertEqual(report["status"], "source_incomplete")
        self.assertIn("metadata checksum", report["error"]["message"])
        self.assertEqual(report["scan"]["lines"], 0)

    def test_review_time_unit_must_be_explicitly_supported_not_guessed(self):
        self.prepare(gzip.compress(b'{"parent_asin":"A"}\n', mtime=0))
        for unit in (None, "seconds"):
            with self.subTest(unit=unit):
                run = self.prepare(gzip.compress(
                    b'{"parent_asin":"A","timestamp":1609459200000}\n', mtime=0),
                    stage="reviews", time_unit=unit)
                self.assertNotEqual(run.returncode, 0)
                report = json.loads(run.stdout)
                self.assertEqual(report["status"], "source_incomplete")
                self.assertIn("time_unit", report["error"]["message"])
                self.assertEqual(report["scan"]["lines"], 0)

    def test_oversized_rating_is_diagnosed_without_aborting_the_full_review_scan(self):
        self.prepare(gzip.compress(b'{"parent_asin":"A"}\n', mtime=0))
        body = (json.dumps({"parent_asin": "A", "asin": "V", "user_id": "U",
                            "rating": 10**400, "title": "", "text": "", "timestamp": 1609459200000}) +
                '\n{"parent_asin":"A","asin":"V","user_id":"U","rating":5,"title":"End","text":"ok","timestamp":1609459200123}\n').encode()
        run = self.prepare(gzip.compress(body, mtime=0), stage="reviews")
        report = json.loads(run.stdout)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(report["scan"]["records"], 2)
        self.assertTrue(report["scan"]["gzip_verified"])
        self.assertEqual(report["review_diagnostics"]["invalid_rating_rows"], 1)
        self.assertEqual(report["time"]["max_line"], 2)


if __name__ == "__main__":
    unittest.main()
