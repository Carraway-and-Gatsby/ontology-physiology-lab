#!/usr/bin/env python3
"""Collect, run sorted round-robin pytest shards, and audit their execution evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET


def partition(nodeids, shards, index):
    return nodeids[index::shards]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def nodeids_from(manifest):
    ids = manifest["nodeids"]
    check(ids and ids == sorted(set(ids)), "collection must be nonempty, sorted and unique")
    check(all(not n.startswith("/") and "::" in n for n in ids), "expected relative pytest node ids")
    return ids


def audit(args):
    manifest = read(args.collection)
    full = nodeids_from(manifest)
    check(manifest["shards"] == args.shards, "shard count differs from collection")
    executed = []
    for index in range(args.shards):
        name = f"shard-{index}"
        result = read(args.results / (name + ".json"))
        assigned = partition(full, args.shards, index)
        check(result["shard"] == index and result["shards"] == args.shards, "wrong shard identity")
        check(result["assigned"] == assigned, f"{name}: wrong partition")
        check(result["exit_code"] == 0 and not result["skipped"], f"{name}: failed or skipped tests")
        check(Counter(result["executed"]) == Counter(assigned), f"{name}: incomplete execution")
        root = ET.parse(args.results / (name + ".xml")).getroot()
        for suite in root.iter("testsuite"):
            check(all(int(suite.get(key, "0")) == 0 for key in ("skipped", "failures", "errors")),
                  f"{name}: JUnit suite reports skips/failures/errors")
        check(not list(root.iter("skipped")), f"{name}: JUnit has skips")
        check(not list(root.iter("failure")) and not list(root.iter("error")), f"{name}: JUnit has failures/errors")
        xml_ids = []
        for case in root.iter("testcase"):
            ids = [p.get("value") for p in case.findall("./properties/property") if p.get("name") == "ci_nodeid"]
            check(len(ids) == 1, f"{name}: testcase lacks unique ci_nodeid")
            xml_ids.extend(ids)
        check(Counter(xml_ids) == Counter(assigned), f"{name}: JUnit execution differs from partition")
        executed.extend(result["executed"])
    check(Counter(executed) == Counter(full), "executed union differs from full collection or overlaps")
    print(f"shard coverage: {len(full)} collected = {len(executed)} executed; {args.shards} disjoint shards; 0 skips")


class Recorder:
    def __init__(self, args):
        self.args = args
        self.full = []
        self.assigned = []
        self.executed = []
        self.skipped = []

    def pytest_collectreport(self, report):
        if report.skipped:
            self.skipped.append(report.nodeid)

    def pytest_collection_modifyitems(self, config, items):
        import pytest

        self.full = sorted(item.nodeid for item in items)
        if not self.full or len(self.full) != len(set(self.full)):
            raise pytest.UsageError("collection must be nonempty and have unique node ids")
        if self.args.command == "collect":
            return
        manifest = read(self.args.collection)
        if self.full != nodeids_from(manifest) or manifest["shards"] != self.args.shards:
            raise pytest.UsageError("shard collection differs from the reference collection")
        self.assigned = partition(self.full, self.args.shards, self.args.shard)
        wanted = set(self.assigned)
        chosen = {item.nodeid: item for item in items if item.nodeid in wanted}
        config.hook.pytest_deselected(items=[item for item in items if item.nodeid not in wanted])
        items[:] = [chosen[n] for n in self.assigned]
        for item in items:
            item.user_properties.append(("ci_nodeid", item.nodeid))

    def pytest_runtest_logreport(self, report):
        if report.skipped:
            self.skipped.append(report.nodeid)
        if report.when == "call":
            self.executed.append(report.nodeid)


def run_pytest(args):
    import pytest

    recorder = Recorder(args)
    options = ["-q", "--tb=short", *args.paths]
    if args.basetemp is not None:
        options.append(f"--basetemp={args.basetemp}")
    if args.command == "collect":
        options.append("--collect-only")
    else:
        args.results.mkdir(parents=True, exist_ok=True)
        options += [f"--junitxml={args.results / f'shard-{args.shard}.xml'}", "--durations=20"]
    start = time.monotonic()
    code = int(pytest.main(options, plugins=[recorder]))
    if recorder.skipped:
        code = code or 1
    if args.command == "collect":
        if code == 0:
            full = recorder.full
            pieces = [partition(full, args.shards, i) for i in range(args.shards)]
            check(Counter(n for p in pieces for n in p) == Counter(full), "invalid partition")
            check(all(pieces), "shard count exceeds collection size")
            write(args.collection, dict(nodeids=full, shards=args.shards, paths=args.paths))
            print(f"partition verified: {len(full)} node ids; {args.shards} disjoint shards; sizes {min(map(len, pieces))}..{max(map(len, pieces))}")
    else:
        if Counter(recorder.executed) != Counter(recorder.assigned):
            code = code or 1
        write(args.results / f"shard-{args.shard}.json", dict(
            shard=args.shard, shards=args.shards, assigned=recorder.assigned,
            executed=recorder.executed, skipped=recorder.skipped, exit_code=code,
            wall_seconds=round(time.monotonic() - start, 3)))
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect", "run", "coverage"))
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--shards", type=int, required=True)
    parser.add_argument("--shard", type=int)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--basetemp", type=Path, help="override pytest's temporary directory (CI uses RUNNER_TEMP)")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_intermixed_args()
    if args.shards < 1:
        parser.error("--shards must be positive")
    if args.command == "run" and (args.shard is None or not 0 <= args.shard < args.shards):
        parser.error("run requires 0 <= --shard < --shards")
    if args.command != "collect" and args.results is None:
        parser.error("run/coverage require --results")
    if args.command == "coverage":
        audit(args)
        return 0
    if not args.paths:
        parser.error("collect/run require explicit test paths")
    return run_pytest(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, ET.ParseError) as exc:
        sys.exit(f"shard evidence invalid: {exc}")
