"""Single-process P1 output quota and offline read boundary."""
import builtins
import io
import os
from pathlib import Path
import subprocess
import sys


class P1StorageGuard:
    def __init__(self, root, limit_bytes, *, run_root=None, run_limit_bytes=None, development=False):
        self.development = development
        if type(limit_bytes) is not int or not 0 < limit_bytes <= (1024**3 if development else 128 * 1024**2):
            raise ValueError('invalid_storage_limit')
        self.root, self.limit_bytes = Path(root).absolute(), limit_bytes
        self.run_root = Path(run_root).absolute() if run_root is not None else None
        self.run_limit_bytes, self.run_charged_bytes = run_limit_bytes, 0
        if ((self.run_root is None) != (run_limit_bytes is None)
                or self.run_root is not None and (self.run_root == self.root
                    or not self.run_root.is_relative_to(self.root) or type(run_limit_bytes) is not int
                    or not 0 < run_limit_bytes <= (128 if development else 64) * 1024**2)):
            raise ValueError('invalid_run_storage_limit')
        self.charged_bytes = 0
        self.active = self.used = self._opening = False
        self.attempts = {'network': 0, 'credentials': 0, 'evaluation': 0}
        self.S_authorized = self.sender_active = False
        self.credential_read = None
        self.allowed = {'credentials': 0, 'response_workers': 0}

    def authorize_S(self, authorization_id):
        from p1_engineering import AUTHORIZATIONS
        if not self.active or authorization_id not in AUTHORIZATIONS:
            raise OSError('S_sender_not_authorized')
        self.S_authorized = True

    def authorize_development(self, authorization_id):
        from development_pilot import AUTHORIZATION
        if not self.active or not self.development or authorization_id != AUTHORIZATION:
            raise OSError('development_sender_not_authorized')
        self.S_authorized = True

    def _path(self, value):
        path = Path(value).absolute()
        if '..' in path.parts or not path.is_relative_to(self.root):
            raise OSError('outside_output')
        if any(p.exists() and (p.is_symlink() or p.is_junction()) for p in (path, *path.parents)):
            raise OSError('reparse_output')
        return path

    def _audit(self, event, args):
        if not self.active:
            return
        if event.startswith(('socket.', 'http.client.', 'subprocess.')):
            expected = [sys.executable, '-B', str(Path(__file__).resolve().with_name('fourrouter_probe.py')), '_http_once']
            if (event == 'subprocess.Popen' and self.S_authorized and self.sender_active
                    and args[0] in (None, sys.executable)
                    and args[1] in (expected, subprocess.list2cmdline(expected))
                    and args[2] is None and args[3] is None):
                self.allowed['response_workers'] += 1
                return
            self.attempts['network'] += 1
            raise OSError('R_network_forbidden')
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            if self.S_authorized and self.sender_active and os.fsdecode(args[0]) == os.devnull:
                return
            path = Path(os.fsdecode(args[0])).absolute()
            parts = {p.lower() for p in path.parts}
            if '.secrets' in parts or path.name == 'id-key.bin':
                expected = Path(__file__).resolve().parent / '.secrets/4router.json'
                if (self.S_authorized and self.credential_read == path == expected
                        and not any(p.exists() and (p.is_symlink() or p.is_junction()) for p in (path, *path.parents))
                        and not args[2] & (os.O_WRONLY | os.O_RDWR)):
                    self.allowed['credentials'] += 1
                    return
                self.attempts['credentials'] += 1
                raise OSError('R_credentials_forbidden')
            if parts & {'private', 'evaluation', 'gold'}:
                self.attempts['evaluation'] += 1
                raise OSError('R_evaluation_forbidden')
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                if not self._opening:
                    raise OSError('unguarded_write')

    def __enter__(self):
        if self.used:
            raise OSError('storage_guard_already_used')
        self.used = True
        self._path(self.root)
        self.charged_bytes = sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file())
        if self.run_root is not None:
            self._path(self.run_root)
            self.run_charged_bytes = sum(p.stat().st_size for p in self.run_root.rglob('*') if p.is_file())
            if self.run_charged_bytes > self.run_limit_bytes:
                raise OSError('run_storage_quota')
        if self.charged_bytes > self.limit_bytes:
            raise OSError('storage_quota')
        self._original = io.open, builtins.open, os.mkdir, os.rename, os.replace
        guard = self

        class File:
            def __init__(self, stream, path):
                self.stream, self.path = stream, path

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def __getattr__(self, name):
                if name in ('buffer', 'raw', 'truncate', 'detach'):
                    raise OSError('unguarded_write')
                return getattr(self.stream, name)

            def write(self, value):
                # Double text bytes conservatively covers Windows newline translation.
                size = len(value.encode(self.stream.encoding)) * 2 if isinstance(value, str) else memoryview(value).nbytes
                if guard.charged_bytes + size > guard.limit_bytes:
                    raise OSError('storage_quota')
                in_run = guard.run_root is not None and self.path.is_relative_to(guard.run_root)
                if in_run and guard.run_charged_bytes + size > guard.run_limit_bytes:
                    raise OSError('run_storage_quota')
                guard.charged_bytes += size
                if in_run:
                    guard.run_charged_bytes += size
                return self.stream.write(value)

            def writelines(self, values):
                for value in values:
                    self.write(value)

        def opened(file, mode='r', *args, **kwargs):
            if type(file) is int and self.S_authorized and self.sender_active:
                return self._original[0](file, mode, *args, **kwargs)
            writing = any(c in mode for c in 'wax+')
            if writing:
                self._path(file)
            self._opening = writing
            try:
                stream = self._original[0](file, mode, *args, **kwargs)
            finally:
                self._opening = False
            return File(stream, Path(file).absolute()) if writing else stream

        def directory(path, *args, **kwargs):
            self._path(path)
            return self._original[2](path, *args, **kwargs)

        def move(operation, source, target, *args, **kwargs):
            self._path(source)
            self._path(target)
            return operation(source, target, *args, **kwargs)

        self.active = True
        sys.addaudithook(self._audit)
        io.open = builtins.open = opened
        os.mkdir = directory
        os.rename = lambda source, target, *a, **k: move(self._original[3], source, target, *a, **k)
        os.replace = lambda source, target, *a, **k: move(self._original[4], source, target, *a, **k)
        return self

    def __exit__(self, *args):
        self.active = False
        io.open, builtins.open, os.mkdir, os.rename, os.replace = self._original
