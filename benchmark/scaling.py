#!/usr/bin/env python3
"""Generate larger graphs and measure complete solver processes on Linux/WSL."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def generate(path, n, degree, seed):
    rng = random.Random(seed)
    with path.open("w", buffering=1024 * 1024) as file:
        file.write(f"1\n{n} {n * degree}\n")
        chunk = []
        for u in range(n):
            # A directed cycle guarantees reachability. Other destinations are random.
            chunk.append(f"{u} {(u + 1) % n} {rng.randint(1, 1000)}\n")
            for _ in range(degree - 1):
                chunk.append(f"{u} {rng.randrange(n)} {rng.randint(1, 1000)}\n")
            if len(chunk) >= 4096:
                file.write("".join(chunk))
                chunk.clear()
        file.write("".join(chunk))


def run(binary, path, threads, cpus, timeout):
    env = dict(os.environ, OMP_NUM_THREADS=str(threads), OMP_DYNAMIC="FALSE",
               OMP_PROC_BIND="close", OMP_PLACES="cores")
    command = [str(binary)]
    if cpus:
        command = ["taskset", "--cpu-list", ",".join(map(str, cpus[:threads])), *command]
    with path.open("rb") as file:
        start = time.perf_counter()
        process = subprocess.run(command, stdin=file, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=env, timeout=timeout)
        elapsed = time.perf_counter() - start
    if process.returncode:
        raise RuntimeError(f"{binary.name} exited with {process.returncode}: {process.stderr.decode(errors='replace')}")
    return elapsed, process.stdout.split()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[250000, 1000000, 2000000, 4000000])
    parser.add_argument("--threads", nargs="+", type=int, default=[1, 2, 4, 8])
    parser.add_argument("--degree", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20261107)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--cpus", help="optional ordered, comma-separated CPU IDs; uses the first p for p threads")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmark/results" / datetime.now().strftime("%Y%m%d-%H%M%S"))
    args = parser.parse_args()
    if min(args.sizes) < 2 or args.degree < 1 or min(args.threads) < 1:
        parser.error("sizes must be >= 2; degree and thread counts must be positive")
    if max(args.sizes) * args.degree > 2147483647:
        parser.error("the number of edges must fit the solvers' 32-bit input format")
    if args.repeat < 1 or args.warmups < 0 or not 0 < args.timeout < float("inf"):
        parser.error("repeat and timeout must be positive; warmups cannot be negative")
    cpus = None
    if args.cpus:
        try:
            cpus = [int(cpu) for cpu in args.cpus.split(",")]
        except ValueError:
            parser.error("cpus must contain comma-separated integer CPU IDs")
        if len(set(cpus)) != len(cpus) or not set(cpus) <= os.sched_getaffinity(0):
            parser.error("CPU IDs must be distinct and available in the current affinity mask")
        if len(cpus) < max(args.threads):
            parser.error("provide at least as many CPUs as the largest thread count")
    output = args.output.resolve()
    if output.exists():
        parser.error("choose a new output directory to preserve previous results")
    build = output / "build"
    inputs = output / "inputs"
    build.mkdir(parents=True)
    inputs.mkdir()
    sources = {"dijkstra": ROOT / "src/dijkstraOneThread.cpp",
               "delta": ROOT / "src/dijkstraDeltaStepping.cpp"}
    snapshots = {name: path.read_bytes() for name, path in sources.items()}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in snapshots.items()}
    binaries = {name: build / name for name in sources}
    for name, source in sources.items():
        snapshot = build / source.name
        snapshot.write_bytes(snapshots[name])
        command = ["g++", str(snapshot), "-O3", "-std=c++17", "-o", str(binaries[name])]
        if name == "delta":
            command.append("-fopenmp")
        subprocess.run(command, check=True)
    metadata = {"date_utc": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
                "host": platform.node(), "python": platform.python_version(),
                "openmp": {"OMP_DYNAMIC": "FALSE", "OMP_PLACES": "cores", "OMP_PROC_BIND": "close"},
                "compiler": subprocess.check_output(["g++", "--version"], text=True),
                "source_sha256": hashes, "affinity": sorted(os.sched_getaffinity(0)),
                "arguments": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
                "weights": [1, 1000], "timing": "whole process, including input and output",
                "validation": "distance to n-1", "load_before": os.getloadavg()}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2))
    fields = ["vertices", "edges", "solver", "threads", "repeat", "wall_s"]
    rows = []
    with (output / "raw.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for n in sorted(set(args.sizes)):
            path = inputs / f"n{n:08d}_d{args.degree}.in"
            print(f"Generating n={n}, m={n * args.degree}...", flush=True)
            generate(path, n, args.degree, args.seed)
            # Untimed reference run prepares the expected answer and warms the input cache.
            _, expected = run(binaries["dijkstra"], path, 1, cpus, args.timeout)
            if len(expected) != 1 or int(expected[0]) < 0:
                raise RuntimeError(f"Invalid reference answer for {path.name}")
            path.with_suffix(".out").write_bytes(b" ".join(expected) + b"\n")
            configs = [("dijkstra", 1)] + [("delta", p) for p in sorted(set(args.threads))]
            for iteration in range(-args.warmups, args.repeat):
                order = configs.copy()
                random.Random(args.seed + iteration).shuffle(order)
                for solver, threads in order:
                    elapsed, answer = run(binaries[solver], path, threads, cpus, args.timeout)
                    if answer != expected:
                        raise RuntimeError(f"Wrong answer: {path.name}, {solver}, threads={threads}")
                    if iteration < 0:
                        continue
                    row = dict(zip(fields, [n, n * args.degree, solver, threads, iteration + 1, elapsed]))
                    rows.append(row)
                    writer.writerow(row)
                    file.flush()
                    print(f"n={n} {solver:8s} p={threads:2d} run={iteration + 1}: {elapsed:.4f}s", flush=True)
    summary = []
    for n in sorted(set(args.sizes)):
        groups = {(solver, threads): [row["wall_s"] for row in rows
                                     if row["vertices"] == n and row["solver"] == solver and row["threads"] == threads]
                  for solver, threads in [("dijkstra", 1)] + [("delta", p) for p in sorted(set(args.threads))]}
        dijkstra = statistics.median(groups[("dijkstra", 1)])
        delta_one = statistics.median(groups[("delta", 1)]) if ("delta", 1) in groups else None
        for (solver, threads), times in groups.items():
            median = statistics.median(times)
            summary.append({"vertices": n, "edges": n * args.degree, "solver": solver, "threads": threads,
                            "runs": len(times), "median_s": median, "min_s": min(times), "max_s": max(times),
                            "speedup_vs_dijkstra": dijkstra / median,
                            "speedup_vs_delta_1": delta_one / median if solver == "delta" and delta_one else ""})
    with (output / "summary.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    metadata["load_after"] = os.getloadavg()
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print("Saved:", output, flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Benchmark failed: {error}")
