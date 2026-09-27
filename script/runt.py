#!/usr/bin/python

import os
import argparse
import sys
import subprocess as sbp
import queue
import pathlib
import threading
from collections import defaultdict
from typing import TextIO

sys.path.insert(0, os.getcwd())
from runtfile import TARGETS, env # pyright: ignore[reportMissingImports]


FLUSH_THRESHOLD = 5
LOGS_DIR = pathlib.Path(__file__).parent.parent / "logs"
LOG_DAEMON = None
SENTINEL = object()

COLORS = ["\033[36m", "\033[32m", "\033[33m", "\033[35m", "\033[34m"]
RESET = "\033[0m"
CC: int = 0

threads: defaultdict[str, list[threading.Thread]] = defaultdict(list)
procs: defaultdict[str, list[sbp.Popen]] = defaultdict(list)
rcs: defaultdict[str, list[int]] = defaultdict(list)
log_queue = queue.Queue()

env["PYTHONUNBUFFERED"] = "1"

def execute(
    cmd: list[str],
    stdin: TextIO | int | None = sys.stdin,
    stdout: TextIO | int | None = sys.stdout,
    stderr: TextIO | int | None = sys.stdout,
    bufsize: int = -1,
) -> sbp.Popen:
    proc = sbp.Popen(
        cmd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        env=env,
        text=True,
        bufsize=bufsize,
    )
    return proc


def push_logs(
    prefix: str,
    fd: TextIO,
    push_stdout: bool = True,
    push_file: bool = True,
    fp: TextIO | None = sys.stdout,
    fp_prefix: str = "",
) -> None:
    if (not push_stdout) and (not push_file):
        return
    if push_file and fp is None:
        raise TypeError

    for line in iter(fd.readline, ""):
        if push_stdout:
            log_queue.put(prefix + line)
        if push_file:
            fp.write(fp_prefix + line) # type: ignore

    if push_stdout:
        log_queue.put(prefix + "[RUNT] | Captured stdout end\n")

    if push_file:
        fp.flush() # type: ignore
        fp.close() # type: ignore


def write_logs(stdout: TextIO = sys.stdout):
    lines_done: int = 0
    while True:
        line = log_queue.get()

        if line is SENTINEL:
            return

        stdout.write(line)
        lines_done += 1
        if lines_done >= FLUSH_THRESHOLD:
            stdout.flush()

def start_log_daemon():
    global LOG_DAEMON
    if LOG_DAEMON is None:
        LOG_DAEMON = threading.Thread(target=write_logs, daemon=True, name="LOG_DAEMON")
        LOG_DAEMON.start()

def stop_log_daemon():
    if LOG_DAEMON is None:
        return
    log_queue.put(SENTINEL)
    LOG_DAEMON.join(30)

#TODO: simplify logs thread management FSM
def run(target: str, need_file_log: bool = False, need_stdout: bool = False, no_stdout: bool = False):
    cmd = TARGETS[target]
    fp = None

    if need_file_log:
        LOGS_DIR.mkdir(exist_ok=True)

        LOGP = LOGS_DIR / f"{target}.log"
        fp = LOGP.open(mode="w")

    if need_stdout:
        start_log_daemon()

    stdin: TextIO | int | None = None
    stdout: TextIO | int | None = None
    stderr: TextIO | int | None = None
    bufsize: int = -1

    if (need_file_log and need_stdout) or (
        need_stdout and not (need_file_log or no_stdout)
    ):
        stdout = sbp.PIPE
        stderr = sbp.STDOUT
        bufsize = 1
    elif need_file_log and not (need_stdout or no_stdout):
        stdout = fp
        stderr = sbp.STDOUT
    elif no_stdout:
        stdout = sbp.DEVNULL
        stderr = sbp.DEVNULL

    proc = execute(cmd, stdin, stdout, stderr, bufsize=bufsize)
    procs[target].append(proc)

    if bufsize == 1:
        global CC
        color = COLORS[CC]
        prefix = f"{color}{target} |{RESET} "
        CC = (CC + 1) % len(COLORS)

        worker = threading.Thread(
            target=push_logs, args=(prefix, proc.stdout, need_stdout, need_file_log, fp)
        )
        threads[target].append(worker)
        worker.start()

    return proc


def run_targets(targets: list[str], parallel: bool, need_stdout: bool, need_file_log: bool, no_stdout: bool) -> int:
    if need_stdout:
        no_stdout = False

    for target in targets:
        run(target, need_file_log, need_stdout, no_stdout)

        if not parallel:
            finalize(target)

    if parallel:
        for target in targets:
            finalize(target)

    stop_log_daemon()

    for l in rcs.values():
        if any(l):
            return 130

    return 0

def resolve_targets(targets: list[str]) -> list[str]:
    # TODO: oreredSet! / dict
    new_targets = []
    for target in targets:
        res = TARGETS.get(target)
        if res is None:
            print(f"[RUNT] | Warning undefined target: {target}. Skipping...")
            continue
        if isinstance(res, tuple):
            for t in res:
                tres = TARGETS.get(t)
                if isinstance(tres, tuple):
                    print(f"[RUNT] | While resolution, target group \"{target}\" references another target group \"{t}\". Skipping...")
                    continue
                new_targets.append(t)
        else:
            new_targets.append(target)

    return list(dict.fromkeys(new_targets))

def finalize(target: str):
    for p in procs[target]:
        rc = p.wait()
        print(f"[RUNT] | Target \"{target}\" exited with code {rc}")
        rcs[target].append(rc)

    del procs[target]

    for t in threads[target]:
        t.join(timeout=10)
        # if t.is_alive():
        # TODO: Track pesky threads later
    del threads[target]

def valid_dir(path_str: str) -> pathlib.Path:
    path = pathlib.Path(path_str)

    if not path.exists():
        raise argparse.ArgumentTypeError(f"The path '{path_str}' does not exist.")
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"The path '{path_str}' is a file, not a directory.")

    return path

def runt(args) -> int:
    targets = resolve_targets(args.targets)
    if not targets:
        print("[RUNT] | No resolved targets. Exiting...")
        return 0
    print(f"[RUNT] | Resolved targets: {', '.join(targets)}")
    return run_targets(targets, args.parallel, args.parallel_log, args.file_log, args.no_stdout)

def targets(args):
    from pprint import pprint

    print("Currently defined targets: ")
    pprint(TARGETS)

def main(argv=sys.argv):
    # runt -> weak animal
    # also stands for run Tests
    # and run Tasks
    parser = argparse.ArgumentParser(
        prog="runt",
        description="A short and simple command runner!",
        epilog="BTW: A runt is an unusually small and weak animal"
        "born in a litter, or an insulting term for a small person",
    )

    parser.add_argument(
        "--parallel", "-p", action="store_true", help="execute your targets parallely"
    )
    parser.add_argument(
        "--parallel-log",
        "-l",
        action="store_true",
        help="Show all parallel execution logs on stdout",
    )
    parser.add_argument(
        "--file-log",
        "-f",
        action="store_true",
        help="Enables file logging for tasks",
    )
    parser.add_argument(
        "--log-dir",
        "-d",
        type=valid_dir,
        default=SENTINEL,
        help="Create log files in the specified directory",
    )
    parser.add_argument(
        "--no-stdout",
        "-q",
        action="store_true",
        help="If the stdout should NOT be outputted to by targets, using --parallel-log disables this",
    )
    parser.add_argument("targets", action="store", nargs="+", help="The target to run")
    parser.set_defaults(func = runt)
    subparsers = parser.add_subparsers()
    targets_parser = subparsers.add_parser("targets")
    targets_parser.set_defaults(func = targets)

    args = parser.parse_args()

    if args.log_dir is not SENTINEL:
        global LOGS_DIR
        LOGS_DIR = args.log_dir

    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
