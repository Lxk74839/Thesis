"""Read-only existing-object audit plus PUBLIC-only lossless storage prototype; no new plans."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import statistics
import subprocess
import sys
import time
import zlib

from diagnose_t0_costs import BASE_SECONDS, LEDGER, ROOT, WORK, raw, save, sizes, write_gate

ORIGINAL = ROOT / 'data/ticket12-t0/catalog-0.1.0'
OMIT = {'max_output_tokens', 'service_tier', 'store', 'stream'}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def measured(callback, count=3):
    samples = []
    result = None
    for _ in range(count):
        started = time.perf_counter()
        result = callback()
        samples.append(time.perf_counter() - started)
    return result, {'min': min(samples), 'median': statistics.median(samples), 'max': max(samples), 'repeats': count}


def compact(values):
    """Exact canonical fragments, including each complete input item; P is a closed W projection."""
    fragments, records = {}, []
    started = time.perf_counter()
    for value in values:
        def fragment(item):
            blob = raw(item)
            identity = sha(blob)
            fragments.setdefault(identity, blob)
            return identity
        recipe = {k: {'items': [fragment(item) for item in v]} if k == 'input' else {'fragment': fragment(v)}
                  for k, v in value['wire_body'].items()}
        metadata = {k: v for k, v in value.items() if k not in ('wire_body', 'count_body', 'wire_utf8', 'count_utf8')}
        records.append({'metadata': metadata, 'wire_recipe': recipe})
    factor_seconds = time.perf_counter() - started
    started = time.perf_counter()
    pack, index = bytearray(), {}
    for identity, blob in sorted(fragments.items()):
        compressed = zlib.compress(blob, 1)
        index[identity] = {'offset': len(pack), 'bytes': len(compressed), 'raw_bytes': len(blob)}
        pack.extend(compressed)
    manifest = {'schema_version': 'DIAGNOSTIC-fragment-recipe-0.1.0', 'codec': 'zlib-level1',
        'zlib_version': zlib.ZLIB_VERSION, 'provenance': 'diagnostic_only_not_accepted',
        'count_omit': sorted(OMIT), 'fragments': index, 'records': records, 'pack_sha256': sha(pack)}
    return bytes(pack), manifest, {'factor_seconds': factor_seconds,
        'compress_seconds': time.perf_counter() - started, 'fragments': len(fragments),
        'unique_uncompressed_fragment_bytes': sum(map(len, fragments.values())),
        'unshared_fragment_references': sum(len(v.get('items', [])) or 1 for r in records for v in r['wire_recipe'].values())}


def verify(pack, manifest, originals):
    started = time.perf_counter()
    assert sha(pack) == manifest['pack_sha256']
    fragments = {}
    for identity, entry in manifest['fragments'].items():
        blob = zlib.decompress(pack[entry['offset']:entry['offset'] + entry['bytes']])
        assert len(blob) == entry['raw_bytes'] and sha(blob) == identity
        fragments[identity] = blob
    for record, original in zip(manifest['records'], originals, strict=True):
        fields = {k: b'[' + b','.join(fragments[i] for i in v['items']) + b']' if 'items' in v
                  else fragments[v['fragment']] for k, v in record['wire_recipe'].items()}
        def body(omit):
            return b'{' + b','.join(raw(k) + b':' + fields[k] for k in sorted(fields) if k not in omit) + b'}'
        w, p = body(set()), body(OMIT)
        assert w == original['wire_utf8'].encode() and p == original['count_utf8'].encode()
        assert sha(w) == original['wire_sha256'] and sha(p) == original['count_payload_sha256']
        meta = record['metadata']
        assert sha(raw({k: meta[k] for k in ('wire_sha256', 'count_payload_sha256', 'mapper_version',
            'tool_schema_sha256', 'role_schema_sha256', 'project_id')})) == meta['prepared_id']
    return {'verified_objects': len(originals), 'W_P_bytes_and_sha_match': True,
        'prepared_ids_match': True, 'seconds': time.perf_counter() - started}


def benchmark(value, disk=False):
    w, p = value['wire_utf8'].encode(), value['count_utf8'].encode()
    envelope = raw(value)
    _, serial = measured(lambda: (raw(value['wire_body']), raw(value['count_body'])))
    _, digest = measured(lambda: (sha(w), sha(p)))
    _, outer = measured(lambda: raw(value))
    report = {'W_bytes': len(w), 'P_bytes': len(p), 'envelope_bytes': len(envelope),
        'serialize_W_P_seconds': serial, 'sha_W_P_seconds': digest, 'serialize_full_envelope_seconds': outer}
    if disk:
        target = WORK / 'PUBLIC-write-benchmark.bin'
        _, physical = measured(lambda: target.write_bytes(envelope))
        def memory_write():
            with io.BytesIO() as stream:
                stream.write(envelope)
        _, memory = measured(memory_write)
        report.update(disk_open_write_close_seconds=physical, memory_write_seconds=memory,
            write_semantics='buffered open/write/close; no fsync, same as current object writer')
    return report


def io_controls():
    write_gate()
    blobs = [p.read_bytes() for p in sorted((WORK / 'catalog-baseline/objects').glob('*.json'))]
    joined = b''.join(blobs)
    directory = WORK / 'PUBLIC-io-controls-v2'
    directory.mkdir()
    samples = {name: [] for name in ('26_files', 'one_pack', 'memory')}
    for repeat in range(3):
        def memory_write():
            with io.BytesIO() as stream:
                stream.write(joined)
        operations = {
            '26_files': lambda: [ (directory / ('separate-' + str(repeat) + '-' + str(i))).write_bytes(blob)
                                 for i, blob in enumerate(blobs)],
            'one_pack': lambda: (directory / ('pack-' + str(repeat))).write_bytes(joined),
            'memory': memory_write}
        # Rotate order; byte count and serialization are held fixed.
        order = list(operations)
        for name in order[repeat:] + order[:repeat]:
            started = time.perf_counter()
            operations[name]()
            samples[name].append(time.perf_counter() - started)
    stored = (directory / 'pack-2').read_bytes()
    offset = 0
    for blob in blobs:
        assert stored[offset:offset + len(blob)] == blob
        offset += len(blob)
    assert offset == len(stored) == len(joined)
    result = {'new_plans': 0, 'objects': len(blobs), 'identical_total_bytes': len(joined),
        'seconds': {k: {'samples': v, 'median': statistics.median(v), 'min': min(v), 'max': max(v)}
                    for k, v in samples.items()},
        'packing_round_trip_bytes_match': True, 'semantics': 'buffered open/write/close; preencoded identical bytes; no fsync',
        'diagnostic_work_bytes_before_this_report': sum(sizes().values())}
    save(WORK / 'io-controls-v2.json', result)
    print(json.dumps(result, sort_keys=True))
    return 0


def whole_wire():
    write_gate()
    result = {'new_plans': 0, 'codec': 'zlib-level1', 'groups': {}}
    groups = {case: [json.loads(p.read_bytes()) for p in sorted(
        (WORK / ('catalog-' + case) / 'objects').glob('*.json'))] for case in ('baseline', 'longH')}
    chosen, last_acquire = {}, None
    with (ORIGINAL / 'requests.jsonl').open('rb') as stream:
        for line in stream:
            row = json.loads(line)
            if row['output_kind'] == 'analysis' and 'analysis' not in chosen:
                chosen['analysis'] = row['prepared_id']
            if row['output_kind'] == 'acquire':
                last_acquire = row['prepared_id']
            if row['output_kind'] == 'final_submit':
                chosen.update(acquire=last_acquire, final=row['prepared_id'])
                break
    groups['three_existing'] = [json.loads((ORIGINAL / 'objects' / (pid + '.json')).read_bytes())
                                for pid in chosen.values()]
    for name, values in groups.items():
        started = time.perf_counter()
        pack, records = bytearray(), []
        for value in values:
            body = value['wire_utf8'].encode()
            compressed = zlib.compress(body, 1)
            meta = {k: v for k, v in value.items() if k not in ('wire_body', 'count_body', 'wire_utf8', 'count_utf8')}
            records.append({'metadata': meta, 'offset': len(pack), 'bytes': len(compressed), 'raw_bytes': len(body)})
            pack.extend(compressed)
        manifest = {'schema_version': 'DIAGNOSTIC-whole-W-pack-0.1.0', 'provenance': 'diagnostic_only_not_accepted',
            'codec': 'zlib-level1', 'count_omit': sorted(OMIT), 'records': records, 'pack_sha256': sha(pack)}
        encode_seconds = time.perf_counter() - started
        stored_bytes = len(pack) + len(raw(manifest)) + 1
        if name != 'three_existing':
            path = WORK / ('PUBLIC-whole-W-' + name)
            path.mkdir()
            (path / 'requests.pack').write_bytes(pack)
            save(path / 'manifest.json', manifest)
            pack = (path / 'requests.pack').read_bytes()
            manifest = json.loads((path / 'manifest.json').read_bytes())
        started = time.perf_counter()
        assert sha(pack) == manifest['pack_sha256']
        for record, value in zip(manifest['records'], values, strict=True):
            body = zlib.decompress(pack[record['offset']:record['offset'] + record['bytes']])
            assert len(body) == record['raw_bytes'] and body == value['wire_utf8'].encode() and sha(body) == value['wire_sha256']
            payload = raw({k: v for k, v in json.loads(body).items() if k not in OMIT})
            assert payload == value['count_utf8'].encode() and sha(payload) == value['count_payload_sha256']
            meta = record['metadata']
            assert sha(raw({k: meta[k] for k in ('wire_sha256', 'count_payload_sha256', 'mapper_version',
                'tool_schema_sha256', 'role_schema_sha256', 'project_id')})) == value['prepared_id']
        result['groups'][name] = {'objects': len(values), 'pack_and_manifest_bytes': stored_bytes,
            'legacy_object_bytes': sum(len(raw(v)) + 1 for v in values), 'encode_compress_seconds': encode_seconds,
            'rebuild_verify_seconds': time.perf_counter() - started,
            'W_P_bytes_sha_and_prepared_ids_match': True, 'persisted': name != 'three_existing'}
    save(WORK / 'whole-W-controls.json', result)
    print(json.dumps(result, sort_keys=True))
    return 0


def worker():
    write_gate()
    assert json.loads((WORK / 'state.json').read_bytes())['reserved_plans'] == 12
    report = {'public': {}, 'existing_object_samples': [], 'new_plans': 0,
        'provider_api_calls': {'count': 0, 'generate': 0, 'other': 0}}
    public_sets = []
    for case in ('baseline', 'longH'):
        paths = sorted((WORK / ('catalog-' + case) / 'objects').glob('*.json'))
        values = [json.loads(p.read_bytes()) for p in paths]
        pack, manifest, timings = compact(values)
        destination = WORK / ('PUBLIC-prototype-' + case)
        destination.mkdir()
        (destination / 'fragments.pack').write_bytes(pack)
        save(destination / 'manifest.json', manifest)
        # Round trip from the written PUBLIC files, not the construction variables.
        result = verify((destination / 'fragments.pack').read_bytes(),
            json.loads((destination / 'manifest.json').read_bytes()), values)
        old = sum(p.stat().st_size for p in paths)
        compact_bytes = sum(p.stat().st_size for p in destination.iterdir())
        report['public'][case] = {'objects': len(values), 'legacy_object_bytes': old,
            'one_W_raw_bytes': sum(len(v['wire_utf8'].encode()) for v in values),
            'new_pack_and_manifest_bytes': compact_bytes, 'ratio_to_old_objects': compact_bytes / old,
            **timings, 'round_trip': result, 'microbenchmark_last_object': benchmark(values[-1], disk=True)}
        public_sets.append({v['prepared_id'] for v in values})
    base = WORK / 'catalog-baseline/objects'
    base_ids = {p.stem for p in base.glob('*.json')}
    report['repeat_binding'] = {case: {'same_prepared_ids': base_ids == {p.stem for p in
        (WORK / ('catalog-' + case) / 'objects').glob('*.json')}, 'same_object_file_bytes': all(
        (base / name).read_bytes() == (WORK / ('catalog-' + case) / 'objects' / name).read_bytes()
        for name in (p.name for p in base.glob('*.json')))} for case in ('repeat', 'profile')}
    # Identity differences are observed on exact W/P hashes; no normalization/merging is used.
    baseline_values = [json.loads(p.read_bytes()) for p in sorted(base.glob('*.json'))]
    report['within_run_identity'] = {'N': len(baseline_values), 'U': len(base_ids),
        'unique_wire_sha256': len({v['wire_sha256'] for v in baseline_values}),
        'unique_count_sha256': len({v['count_payload_sha256'] for v in baseline_values}),
        'roles': len({v['source']['role'] for v in baseline_values}),
        'output_kinds': sorted({v['source']['output_kind'] for v in baseline_values}),
        'project_mapper_tool_role_binding_preserved': True}
    catalog = json.loads((ORIGINAL / 'catalog.json').read_bytes())
    chosen, last_acquire = {}, None
    with (ORIGINAL / 'requests.jsonl').open('rb') as stream:
        for line in stream:
            row = json.loads(line)
            if row['output_kind'] == 'analysis' and 'analysis' not in chosen:
                chosen['analysis'] = row['prepared_id']
            if row['output_kind'] == 'acquire':
                last_acquire = row['prepared_id']
            if row['output_kind'] == 'final_submit':
                chosen.update(acquire_after_read=last_acquire, final_submit=row['prepared_id'])
                break
    real_values = []
    for kind, pid in chosen.items():
        assert len(pid) == 64 and all(c in '0123456789abcdef' for c in pid)
        path = ORIGINAL / 'objects' / (pid + '.json')
        before = path.stat()
        blob = path.read_bytes()
        assert sha(blob) == catalog['components']['objects/' + path.name]['sha256']
        value = json.loads(blob)
        real_values.append(value)
        micro = benchmark(value)
        pack, manifest, timing = compact([value])
        roundtrip = verify(pack, manifest, [value])
        after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        report['existing_object_samples'].append({'kind': kind, 'legacy_file_bytes': len(blob),
            'component_sha_matched': True, 'size_and_mtime_unchanged': True, 'microbenchmark': micro,
            'memory_only_compact_bytes': len(pack) + len(raw(manifest)) + 1,
            'memory_only_round_trip': roundtrip, **timing})
    pack, manifest, timing = compact(real_values)
    report['three_existing_objects_combined'] = {'legacy_bytes': sum(v['legacy_file_bytes'] for v in report['existing_object_samples']),
        'memory_only_compact_bytes': len(pack) + len(raw(manifest)) + 1,
        'one_W_raw_bytes': sum(len(v['wire_utf8'].encode()) for v in real_values),
        'round_trip': verify(pack, manifest, real_values), **timing,
        'scope': 'three first-trace objects only; no directory copy, no population bound'}
    report['diagnostic_work_bytes_before_this_report'] = sum(sizes().values())
    save(WORK / 'payload-analysis.json', report)
    print(json.dumps(report, sort_keys=True))
    return 0


def main():
    if sys.argv[1:] == ['--validate-storage']:
        return validate_storage()
    if sys.argv[1:] == ['--worker']:
        return worker()
    if sys.argv[1:] == ['--io-worker']:
        return io_controls()
    if sys.argv[1:] == ['--whole-worker']:
        return whole_wire()
    used = sum(json.loads(row)['seconds'] for row in LEDGER.read_text().splitlines()) - BASE_SECONDS
    assert used < 110, 'diagnostic_time_gate'
    io_mode, whole_mode = sys.argv[1:] == ['--io-controls'], sys.argv[1:] == ['--whole-W-controls']
    label = 'io-controls-v2' if io_mode else 'whole-W-controls' if whole_mode else 'payload-analysis'
    with (WORK / (label + '-stdout.txt')).open('xb') as stream:
        try:
            result = subprocess.run([sys.executable, '-B', str(Path(__file__)),
                '--io-worker' if io_mode else '--whole-worker' if whole_mode else '--worker'], cwd=ROOT,
                stdout=stream, stderr=subprocess.STDOUT, timeout=116 - used)
        except subprocess.TimeoutExpired:
            save(WORK / 'analysis-timeout.json', {'status': 'diagnostic_time_gate', 'new_plans': 0})
            return 2
    print((WORK / (label + '-stdout.txt')).read_text(encoding='utf-8'))
    return result.returncode


def validate_storage():
    """Exactly three inherited objects, after program acceptance, on the original T0 ledger."""
    if os.environ.get('THESIS_RESOURCE_DOMAIN') != 't0':
        print(json.dumps({'status': 'validation_denied', 'reason': 't0_domain_required'}))
        return 2
    from run_check import storage_package
    from t0_catalog import PreparedObjectWriter, iter_prepared_objects
    package = storage_package()
    control = ROOT / '.scratch/ticket12-budget-20261018'
    output = ROOT / package['output_roots'][1] / os.environ['THESIS_BATCH_CHECK_LABEL']
    report = {'status': 'storage_validation_incomplete', 'complete': False, 'new_root_plans': 0,
              'original_T0_status': 'T0_A_incomplete', 'provider_api_calls': {'count': 0, 'generate': 0, 'other': 0}}
    try:
        assert Path(os.environ['THESIS_RESOURCE_LEDGER']) == ROOT / package['t0']['ledger'], 'wrong_T0_ledger'
        accepted = json.loads((control / 'acceptance-t0-a-storage-program-20261019.json').read_bytes())
        assert (accepted['status'] == 'T0_A_storage_program_accepted' and accepted['base'] == package['base']
                and re.fullmatch('[0-9a-f]{40}', accepted['candidate'])), 'program_acceptance_required'
        required = {'t0_catalog.py', 'tests/test_t0_catalog.py', 'model_adapter.py', 'provider_openai.py',
            'token_counting.py', 'recommendation_runner.py', 'evidence_access.py',
            '.scratch/ticket12-budget-20261018/diagnostics/run_check.py',
            '.scratch/ticket12-budget-20261018/diagnostics/check_t0_catalog_delivery.py',
            '.scratch/ticket12-budget-20261018/diagnostics/analyze_t0_payloads.py',
            '.scratch/ticket12-budget-20261018/diagnostics/diagnose_t0_costs.py'}
        assert set(accepted['source_sha256']) == required, 'program_source_set_mismatch'
        for name, expected in accepted['source_sha256'].items():
            assert sha((ROOT / name).read_bytes()) == expected, 'program_source_changed'
        assert not subprocess.check_output(['git', 'diff', '--name-only', accepted['candidate'], '--', *sorted(required)],
                                           cwd=ROOT).strip(), 'candidate_source_changed'
        for axis in ('Standards', 'Spec'):
            review = accepted['reviews'][axis]
            ref = review['record']
            assert (review['candidate'] == accepted['candidate'] and review['blocking_findings'] == 0
                    and ref['path'] == '.scratch/ticket12-budget-20261018/verification-storage-'
                        + axis.lower() + '-' + accepted['candidate'][:7] + '.md'), 'program_review_required'
            assert sha((ROOT / ref['path']).read_bytes()) == ref['sha256'], 'review_record_changed'
        assert not output.exists(), 'validation_output_exists'
        read_bytes, original_bytes = 0, 0

        def source_path(path):
            assert path.is_relative_to(ORIGINAL) and '..' not in path.parts, 'source_path_not_allowed'
            for parent in (path, *path.parents):
                assert not (parent.is_symlink() or parent.is_junction()
                    or parent.lstat().st_file_attributes & 1024), 'reparse_source'
                if parent == ROOT:
                    break
            assert time.time() < float(os.environ['THESIS_RESOURCE_DEADLINE_UNIX']) - 10, 'resource_closeout_required'
            return path

        def source_read(path, maximum):
            nonlocal read_bytes
            source_path(path)
            before = path.stat()
            assert before.st_size <= maximum and read_bytes + before.st_size <= 64 * 1024**2, 'source_read_limit'
            with path.open('rb') as stream:
                blob = stream.read(before.st_size)
            read_bytes += len(blob)
            after = path.stat()
            assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'source_changed'
            return blob, (before.st_size, before.st_mtime_ns)

        blob, catalog_stat = source_read(ORIGINAL / 'catalog.json', 8 * 1024**2)
        assert sha(blob) == '010c4157ca700744b85fec212eef318dc36b81ec29bae291642fcf7846c8824e', 'original_catalog_changed'
        catalog = json.loads(blob)
        chosen, last_acquire, first_key = {}, None, None
        prefix, request_rows = bytearray(), 0
        path = source_path(ORIGINAL / 'requests.jsonl')
        request_stat = (path.stat().st_size, path.stat().st_mtime_ns)
        with path.open('rb') as stream:
            for _ in range(17):
                line = stream.readline(1024**2 - len(prefix))
                assert line and line.endswith(b'\n'), 'request_prefix_limit'
                prefix.extend(line)
                read_bytes += len(line)
                request_rows += 1
                row = json.loads(line)
                key = (row['root_task_id'], row['view_label'], row['method'])
                first_key = first_key or key
                assert key == first_key and row['method'] in ('S', 'M'), 'first_trace_not_closed'
                pid = row['prepared_id']
                assert re.fullmatch('[0-9a-f]{64}', pid), 'invalid_prepared_path'
                if row['output_kind'] == 'analysis' and 'analysis' not in chosen:
                    chosen['analysis'] = pid
                if row['output_kind'] == 'acquire':
                    last_acquire = pid
                if row['output_kind'] == 'final_submit':
                    chosen.update(acquire_after_read=last_acquire, final_submit=pid)
                    break
        assert len(chosen) == 3 and len(set(chosen.values())) == 3, 'three_object_selection_incomplete'
        values, snapshots, bindings = [], [], []
        for kind, pid in chosen.items():
            expected = catalog['components']['objects/' + pid + '.json']
            assert original_bytes + expected['bytes'] <= 24 * 1024**2, 'original_object_read_limit'
            path = ORIGINAL / 'objects' / (pid + '.json')
            blob, snapshot = source_read(path, expected['bytes'])
            assert len(blob) == expected['bytes'] and sha(blob) == expected['sha256'], 'original_component_changed'
            original_bytes += len(blob)
            value = json.loads(blob)
            assert value['prepared_id'] == pid, 'original_prepared_id_mismatch'
            values.append(value)
            snapshots.append((path, snapshot))
            bindings.append({'kind': kind, 'prepared_id': pid, 'original_component': expected,
                'wire_sha256': value['wire_sha256'], 'count_payload_sha256': value['count_payload_sha256'],
                'wire_bytes': value['wire_bytes'], 'count_bytes': len(value['count_utf8'].encode())})
        output.mkdir(parents=True)
        save(output / 'selection.json', {'objects': bindings, 'requests_prefix_sha256': sha(prefix),
            'request_rows_read': request_rows, 'request_prefix_bytes': len(prefix), 'source_read_bytes': read_bytes,
            'full_requests_digest_rescanned': False, 'new_root_plans': 0})
        with PreparedObjectWriter(output) as writer:
            for value in values:
                source_path(ORIGINAL / 'catalog.json')
                writer.add(value)
        for restored, original in zip(iter_prepared_objects(output), values, strict=True):
            assert restored == original, 'production_reader_round_trip_mismatch'
        checker = control / 'diagnostics/check_t0_catalog_delivery.py'
        saved_arguments = sys.argv
        try:
            sys.argv = [str(checker), 'check-objects', '--catalog', str(output), '--output', str(output / 'object-check.json')]
            code = runpy.run_path(str(checker))['main']()
        finally:
            sys.argv = saved_arguments
        assert code == 0, 'independent_object_check_failed'
        for path, snapshot in snapshots + [(ORIGINAL / 'catalog.json', catalog_stat), (ORIGINAL / 'requests.jsonl', request_stat)]:
            after = path.stat()
            assert (after.st_size, after.st_mtime_ns) == snapshot, 'original_source_changed'
        report.update(status='T0_A_storage_component_verified_only', complete=True,
            candidate=accepted['candidate'], verified_objects=3, objects=bindings, source_read_bytes=read_bytes,
            original_object_bytes=original_bytes, request_rows_read=request_rows, request_prefix_bytes=len(prefix),
            pack_and_manifest_bytes=sum(p['bytes'] for p in writer.components.values()),
            W_P_bytes_sha_prepared_id_and_metadata_match=True, original_sources_unchanged=True,
            full_catalog_accepted=False, capacity_judgment='not_performed')
    except (AssertionError, ValueError, OSError, KeyError, TypeError) as exc:
        report['reason'] = str(exc)
    if output.exists():
        save(output / 'validation.json', report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
