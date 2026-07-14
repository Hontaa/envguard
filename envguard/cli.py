"""envguard CLI — zero-dependency command line interface.

Usage:
    envguard check path/to/.env --schema schema.json
    envguard scan  path/to/.env
    envguard diff  staging.env prod.env
"""

import argparse
import json
import sys

from envguard.core import parse_env, validate
from envguard.leaks import find_leaks
from envguard.diff import diff_envs


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def cmd_check(args):
    env = parse_env(_read(args.path))
    schema = {}
    if args.schema:
        try:
            schema = json.loads(args.schema)
        except json.JSONDecodeError:
            schema = json.loads(_read(args.schema))
    res = validate(env, schema)
    if res.ok:
        print(f"OK: {len(env)} keys validated, no errors")
        return 0
    print(f"FAIL: {len(res.errors)} error(s)")
    for e in res.errors:
        print(f"  - {e.key}: {e.message}")
    return 1


def cmd_scan(args):
    env = parse_env(_read(args.path))
    leaks = find_leaks(env)
    if not leaks:
        print("OK: no secret leaks detected")
        return 0
    print(f"LEAK: {len(leaks)} suspected secret(s)")
    for key, pat in leaks:
        print(f"  - {key}: {pat}")
    return 1


def cmd_diff(args):
    a = parse_env(_read(args.a))
    b = parse_env(_read(args.b))
    d = diff_envs(a, b)
    if not any(d.values()):
        print("OK: no drift")
        return 0
    print("DRIFT:")
    for k, v in d["added"].items():
        print(f"  + added   {k}={v}")
    for k, v in d["removed"].items():
        print(f"  - removed {k}={v}")
    for k, (old, new) in d["changed"].items():
        print(f"  ~ changed {k}: {old} -> {new}")
    return 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="envguard", description=".env/config validator")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("check", help="validate schema")
    pc.add_argument("path")
    pc.add_argument("--schema", default=None)
    pc.set_defaults(func=cmd_check)

    ps = sub.add_parser("scan", help="detect secret leaks")
    ps.add_argument("path")
    ps.set_defaults(func=cmd_scan)

    pd = sub.add_parser("diff", help="compare two env files")
    pd.add_argument("a")
    pd.add_argument("b")
    pd.set_defaults(func=cmd_diff)

    args = p.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
