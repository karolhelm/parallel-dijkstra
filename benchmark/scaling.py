#!/usr/bin/env python3
"""Generate larger graphs and report compute/process timings on Linux/WSL."""
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

TIMER_HEADER = r'''
#include <chrono>
#include <iostream>
#include <iomanip>
#include <utility>
namespace bench {
using Clock = std::chrono::steady_clock;
double solve = 0;
double seconds(Clock::time_point start) {
    return std::chrono::duration<double>(Clock::now() - start).count();
}
struct Report {
    ~Report() { std::cerr << std::setprecision(12) << "BENCH_SOLVE " << solve << "\n"; }
} report;
}
'''


def instrument(text, solver):
    """Add timers/full-distance validation to build copies; keep src untouched."""
    def replace(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError(f"Source changed: cannot locate timing anchor {old!r}")
        text = text.replace(old, new, 1)

    if solver == "dijkstra":
        start = text.index("        priority_queue<node> q;")
        end = text.index("        if(distance[n - 1] == LLONG_MAX){")
        body = text[start:end]
        replace(body, "        auto benchStart = bench::Clock::now();\n"
                "        vector<long long> benchDistance;\n        {\n" + body +
                "        benchDistance = std::move(distance);\n        }\n"
                "        bench::solve += bench::seconds(benchStart);\n")
        value, infinity = "distance[n - 1]", "LLONG_MAX"
    else:
        replace("long long deltaStepping(", "vector<long long> deltaStepping(")
        replace("    return distance[n - 1];", "    vector<long long> result(n);\n"
                "    for(int v = 0; v < n; ++v) result[v] = distance[v].load();\n"
                "    return result;")
        replace("        long long answer = deltaStepping(graph, delta);",
                "        auto benchStart = bench::Clock::now();\n"
                "        vector<long long> benchDistance = deltaStepping(graph, delta);\n"
                "        bench::solve += bench::seconds(benchStart);")
        value, infinity = "answer", "INF"
    replace("        if(" + value + " == " + infinity + "){\n"
            '            cout << -1 << "\\n";\n        }else{\n'
            '            cout << ' + value + ' << "\\n";\n        }',
            r'''        for(int v = 0; v < n; ++v){
            if(v > 0) cout << ' ';
            cout << (benchDistance[v] == LLONG_MAX ? -1 : benchDistance[v]);
        }
        cout << '\n';''')
    return TIMER_HEADER + text


def generate(path, n, degree, seed, weights="uniform", graph="random", layers=32):
    rng = random.Random(seed)

    def weight():
        # Consume the same draws so unit/uniform weights share the random topology.
        value = rng.randint(1, 1000)
        return 1 if weights == "unit" else value

    if graph == "layered":
        starts = [1 + (n - 1) * layer // layers for layer in range(layers + 1)]
        last_width = starts[-1] - starts[-2]
        m = n - 1 + (degree - 1) * (n - 1 - last_width)
        with path.open("w", buffering=1024 * 1024) as file:
            file.write(f"1\n{n} {m}\n")
            chunk = []

            def edge(u, v):
                chunk.append(f"{u} {v} {weight()}\n")
                if len(chunk) >= 4096:
                    file.write("".join(chunk))
                    chunk.clear()

            for v in range(starts[0], starts[1]):
                edge(0, v)
            for layer in range(layers - 1):
                begin, end = starts[layer], starts[layer + 1]
                next_begin, next_end = starts[layer + 1], starts[layer + 2]
                # A backbone reaches every vertex, including unequal layer widths.
                for v in range(next_begin, next_end):
                    edge(begin + (v - next_begin) % (end - begin), v)
                for u in range(begin, end):
                    for _ in range(degree - 1):
                        edge(u, rng.randrange(next_begin, next_end))
            file.write("".join(chunk))
        return m

    m = n * degree
    with path.open("w", buffering=1024 * 1024) as file:
        file.write(f"1\n{n} {m}\n")
        chunk = []
        for u in range(n):
            # A directed cycle guarantees reachability. Other destinations are random.
            chunk.append(f"{u} {(u + 1) % n} {weight()}\n")
            for _ in range(degree - 1):
                chunk.append(f"{u} {rng.randrange(n)} {weight()}\n")
            if len(chunk) >= 4096:
                file.write("".join(chunk))
                chunk.clear()
        file.write("".join(chunk))
    return m


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
    markers = [line.split()[1] for line in process.stderr.decode().splitlines()
               if line.startswith("BENCH_SOLVE ")]
    if len(markers) != 1:
        raise RuntimeError(f"Missing compute timer in {binary.name}")
    compute = float(markers[0])
    if not 0 < compute <= elapsed:
        raise RuntimeError(f"Invalid compute timer in {binary.name}: {compute}")
    return elapsed, compute, process.stdout.split()


def automatic_cpus(count):
    """Use distinct cores on one socket when the available topology permits it."""
    sockets = {}
    try:
        for cpu in sorted(os.sched_getaffinity(0)):
            topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
            socket = int((topology / "physical_package_id").read_text())
            core = int((topology / "core_id").read_text())
            sockets.setdefault(socket, {}).setdefault(core, cpu)
    except (OSError, ValueError):
        return None
    for socket in sorted(sockets):
        cpus = sorted(sockets[socket].values())
        if len(cpus) >= count:
            return cpus[:count]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[250000, 1000000, 2000000, 4000000])
    parser.add_argument("--threads", nargs="+", type=int, default=[1, 2, 4, 8, 16])
    parser.add_argument("--degree", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20261107)
    parser.add_argument("--weights", choices=["uniform", "unit"], default="uniform")
    parser.add_argument("--graph", choices=["random", "layered"], default="random")
    parser.add_argument("--layers", type=int, default=32, help="number of layers after the source in layered graphs")
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
    if args.graph == "layered" and not 1 <= args.layers < min(args.sizes):
        parser.error("layers must be positive and smaller than every graph size")
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
    else:
        cpus = automatic_cpus(max(args.threads))
        if cpus:
            print("Auto CPU pinning:", ",".join(map(str, cpus)), flush=True)
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
        timed = build / (source.stem + '-timed.cpp')
        timed.write_text(instrument(snapshots[name].decode(), name))
        command = ["g++", str(timed), "-O3", "-std=c++17", "-o", str(binaries[name])]
        if name == "delta":
            command.append("-fopenmp")
        subprocess.run(command, check=True)
    metadata = {"date_utc": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
                "host": platform.node(), "python": platform.python_version(),
                "openmp": {"OMP_DYNAMIC": "FALSE", "OMP_PLACES": "cores", "OMP_PROC_BIND": "close"},
                "compiler": subprocess.check_output(["g++", "--version"], text=True),
                "source_sha256": hashes, "affinity": sorted(os.sched_getaffinity(0)),
                "solver_cpu_lists": {str(p): cpus[:p] for p in sorted({1, *args.threads})} if cpus else None,
                "arguments": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
                "weights": [1, 1 if args.weights == "unit" else 1000],
                "timing": {"compute": "initialization, solve, working-structure cleanup; excludes graph input and printing",
                           "wall": "whole process including full-distance output of benchmark copies"},
                "instrumentation": "build copies only; delta includes light/heavy split and final distance copy",
                "validation": "every distance against reference", "load_before": os.getloadavg()}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2))
    fields = ["vertices", "edges", "solver", "threads", "repeat", "wall_s", "compute_s"]
    rows = []
    with (output / "raw.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for n in sorted(set(args.sizes)):
            path = inputs / f"n{n:08d}_d{args.degree}.in"
            print(f"Generating n={n}, graph={args.graph}, weights={args.weights}...", flush=True)
            m = generate(path, n, args.degree, args.seed, args.weights, args.graph, args.layers)
            print(f"Prepared n={n}, m={m}", flush=True)
            # Untimed reference run prepares the expected answer and warms the input cache.
            _, _, expected = run(binaries["dijkstra"], path, 1, cpus, args.timeout)
            if len(expected) != n or expected[0] != b"0" or b"-1" in expected:
                raise RuntimeError(f"Invalid reference answer for {path.name}")
            path.with_suffix(".out").write_bytes(b" ".join(expected) + b"\n")
            configs = [("dijkstra", 1)] + [("delta", p) for p in sorted(set(args.threads))]
            for iteration in range(-args.warmups, args.repeat):
                order = configs.copy()
                random.Random(args.seed + iteration).shuffle(order)
                for solver, threads in order:
                    elapsed, compute, answer = run(binaries[solver], path, threads, cpus, args.timeout)
                    if answer != expected:
                        raise RuntimeError(f"Wrong answer: {path.name}, {solver}, threads={threads}")
                    if iteration < 0:
                        continue
                    row = dict(zip(fields, [n, m, solver, threads, iteration + 1, elapsed, compute]))
                    rows.append(row)
                    writer.writerow(row)
                    file.flush()
                    print(f"n={n} {solver:8s} p={threads:2d} run={iteration + 1}: "
                          f"compute={compute:.4f}s whole={elapsed:.4f}s", flush=True)
    summary = []
    for n in sorted(set(args.sizes)):
        groups = {(solver, threads): [row["wall_s"] for row in rows
                                     if row["vertices"] == n and row["solver"] == solver and row["threads"] == threads]
                  for solver, threads in [("dijkstra", 1)] + [("delta", p) for p in sorted(set(args.threads))]}
        dijkstra = statistics.median(groups[("dijkstra", 1)])
        delta_one = statistics.median(groups[("delta", 1)]) if ("delta", 1) in groups else None
        compute_groups = {key: [row["compute_s"] for row in rows
                               if row["vertices"] == n and (row["solver"], row["threads"]) == key]
                          for key in groups}
        compute_dijkstra = statistics.median(compute_groups[("dijkstra", 1)])
        compute_one = statistics.median(compute_groups[("delta", 1)]) if ("delta", 1) in groups else None
        print(f"\nMEDIANS n={n} (speedup = ratio of medians)", flush=True)
        print("solver     p   compute[s]   vs Dijkstra", flush=True)
        for (solver, threads), times in groups.items():
            median = statistics.median(times)
            compute_times = compute_groups[(solver, threads)]
            compute_median = statistics.median(compute_times)
            compute_speedup = compute_dijkstra / compute_median
            parallel_speedup = compute_one / compute_median if solver == "delta" and compute_one else ""
            m = next(row["edges"] for row in rows if row["vertices"] == n)
            summary.append({"vertices": n, "edges": m, "solver": solver, "threads": threads,
                            "runs": len(times), "median_s": median, "min_s": min(times), "max_s": max(times),
                            "speedup_vs_dijkstra": dijkstra / median,
                            "speedup_vs_delta_1": delta_one / median if solver == "delta" and delta_one else "",
                            "compute_median_s": compute_median, "compute_min_s": min(compute_times),
                            "compute_max_s": max(compute_times), "compute_speedup_vs_dijkstra": compute_speedup,
                            "compute_speedup_vs_delta_1": parallel_speedup})
            print(f"{solver:9s} {threads:2d}   {compute_median:10.4f}   {compute_speedup:10.2f}x", flush=True)
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
