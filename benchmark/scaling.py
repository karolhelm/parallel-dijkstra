#!/usr/bin/env python3
"""Generowanie grafów i porównanie Dijkstry z delta-stepping (Linux/WSL)."""
import argparse
import os
from pathlib import Path
import random
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261107

def generate(path, n, degree, graph="random", layers=32, seed=SEED):
    rng = random.Random(seed)
    m = n - 1 if graph == "path" else n * degree
    if graph == "layered":
        starts = [1 + (n - 1) * layer // layers for layer in range(layers + 1)]
        m = n - 1 + (degree - 1) * (starts[-2] - 1)
    with path.open("w", buffering=1024 * 1024) as file:
        file.write(f"1\n{n} {m}\n")

        def edge(u, v):
            w = rng.randint(1, 1000)
            file.write(f"{u} {v} {w}\n")

        if graph == "path":
            for u in range(n - 1):
                edge(u, u + 1)
        elif graph == "random":
            for u in range(n):
                edge(u, (u + 1) % n)  # Cykl zapewnia osiągalność wszystkich wierzchołków.
                for _ in range(degree - 1):
                    edge(u, rng.randrange(n))
        else:
            for v in range(starts[0], starts[1]):
                edge(0, v)
            for layer in range(layers - 1):
                begin, end = starts[layer], starts[layer + 1]
                next_begin, next_end = starts[layer + 1], starts[layer + 2]
                for v in range(next_begin, next_end):
                    edge(begin + (v - next_begin) % (end - begin), v)
                for u in range(begin, end):
                    for _ in range(degree - 1):
                        edge(u, rng.randrange(next_begin, next_end))
    return m


def run(binary, path, threads):
    env = dict(os.environ, OMP_NUM_THREADS=str(threads), OMP_DYNAMIC="FALSE")
    with path.open("rb") as file:
        start = time.perf_counter()
        process = subprocess.run([str(binary)], stdin=file, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=env)
        whole = time.perf_counter() - start
    if process.returncode:
        raise RuntimeError(f"{binary.name}: {process.stderr.decode(errors='replace')}")
    timers = [line.split()[1] for line in process.stderr.decode().splitlines()
              if line.startswith("BENCH_SOLVE ")]
    if len(timers) != 1 or not 0 < float(timers[0]) <= whole:
        raise RuntimeError(f"Niepoprawny czas obliczeń: {binary.name}")
    return whole, float(timers[0]), process.stdout.split()


def summarize(label, measurements):
    medians = {config: statistics.median(times) for config, times in measurements.items()}
    dijkstra = medians["dijkstra", 1]
    print(f"\nMEDIANS {label} (speedup = ratio of medians)")
    print("solver     p   compute[s]   vs Dijkstra")
    for (solver, threads), compute in medians.items():
        speedup = dijkstra / compute
        compute_text = f"{compute:.4f}" if compute >= 0.0001 else f"{compute:.2g}"
        speedup_text = f"{speedup:.2f}x" if speedup >= 0.01 else f"{speedup:.2g}x"
        print(f"{solver:9s} {threads:2d}   {compute_text:>10}   {speedup_text:>11}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int,
                        help="Liczby wierzchołków; domyślnie path: 10000, layered: 2000000, random: 4000000")
    parser.add_argument("--threads", nargs="+", type=int, default=[1, 2, 4, 8, 16])
    parser.add_argument("--degree", type=int, default=4)
    parser.add_argument("--graph", choices=["random", "layered", "path"], default="random")
    parser.add_argument("--graph-count", type=int, default=1, help="Liczba grafów dla każdego rozmiaru (domyślnie 1)")
    parser.add_argument("--layers", type=int, default=32)
    parser.add_argument("--repeat", type=int, help="Pomiary jednego grafu: domyślnie random 3, pozostałe 5")
    args = parser.parse_args()
    if args.repeat is None:
        args.repeat = 3 if args.graph == "random" else 5
    if args.sizes is None:
        args.sizes = {
            "random": [4000000],
            "layered": [2000000],
            "path": [10000],
        }[args.graph]
    if min(args.sizes) < 2 or args.degree < 1 or min(args.threads) < 1 or max(args.sizes) * args.degree > 2147483647:
        parser.error("Wymagane n >= 2, degree i threads >= 1 oraz liczba krawędzi <= INT_MAX")
    if args.graph == "layered" and not 1 <= args.layers < min(args.sizes):
        parser.error("Liczba warstw musi być dodatnia i mniejsza od liczby wierzchołków")
    if args.repeat < 1:
        parser.error("Liczba powtórzeń musi być dodatnia")
    if args.graph_count < 1:
        parser.error("Liczba grafów musi być dodatnia")

    # Plik grafu i programy istnieją tylko na czas uruchomienia skryptu.
    with tempfile.TemporaryDirectory(prefix="dijkstra-") as directory:
        temporary = Path(directory)
        binaries = {}
        for solver, filename in [("dijkstra", "dijkstraOneThread.cpp"), ("delta", "dijkstraDeltaStepping.cpp")]:
            binaries[solver] = temporary / solver
            command = ["g++", str(ROOT / "src" / filename), "-O3", "-std=c++17", "-o", str(binaries[solver])]
            if solver == "delta":
                command.append("-fopenmp")
            subprocess.run(command, check=True)

        configs = [("dijkstra", 1)] + [("delta", p) for p in sorted(set(args.threads))]
        path = temporary / "graph.in"
        for n in sorted(set(args.sizes)):
            for sample in range(args.graph_count):
                seed = SEED + sample
                label = f"n={n} graph={sample + 1}/{args.graph_count}"
                print(f"Generating {label}, type={args.graph}...", flush=True)
                m = generate(path, n, args.degree, args.graph, args.layers, seed=seed)
                print(f"Prepared n={n}, m={m}", flush=True)
                _, _, expected = run(binaries["dijkstra"], path, 1)
                if len(expected) != n or expected[0] != b"0" or b"-1" in expected:
                    raise RuntimeError(f"Niepoprawna odpowiedź wzorcowa: {label}")

                measurements = {config: [] for config in configs}
                for iteration in range(args.repeat):
                    order = configs.copy()
                    random.Random(seed + iteration).shuffle(order)
                    for solver, threads in order:
                        whole, compute, answer = run(binaries[solver], path, threads)
                        if answer != expected:
                            raise RuntimeError(f"Błędny wynik: {label}, {solver}, threads={threads}")
                        measurements[solver, threads].append(compute)
                        print(f"{label} {solver:8s} p={threads:2d} run={iteration + 1}: "
                              f"compute={compute:.4f}s whole={whole:.4f}s", flush=True)
                summarize(label, measurements)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Benchmark failed: {error}")
