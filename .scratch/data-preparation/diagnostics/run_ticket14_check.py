"""Reuse the accepted Windows Job guard with a separate ticket14 resource ledger."""
import run_joint13_check as guard

guard.AUDIT = guard.ROOT / '.scratch/data-preparation/verification/ticket14-20261016'

if __name__ == '__main__':
    raise SystemExit(guard.main())
