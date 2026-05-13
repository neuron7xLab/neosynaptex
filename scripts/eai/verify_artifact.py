from __future__ import annotations
import argparse
from core.eai.external_verification import run_local_command, write_report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--claim-id', required=True)
    p.add_argument('--output', default='external_verification_report.json')
    p.add_argument('command', nargs='+')
    args = p.parse_args()
    report = run_local_command(args.claim_id, args.command)
    write_report(args.output, report)
    print(report.status)


if __name__ == '__main__':
    main()
