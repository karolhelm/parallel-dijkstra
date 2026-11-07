# Tests

Each `tests/<name>.in` is an input for both solvers, and `tests/<name>.out` is the expected answer
(shortest path from `0` to `n-1`, or `-1`). All tests except `12_many_small` are a single graph with
about 2 million edges.

| test | graph |
|---|---|
| `01_random_sparse` | random, n = 500 000, weights 1 – 10⁶ |
| `02_random_dense` | random, n = 10 000, average out-degree 200, weights 1 – 1000 |
| `03_random_unit` | random, n = 500 000, all weights 1 |
| `04_random_small_weights` | random, n = 500 000, weights 0 – 10 (including zeros) |
| `05_heavy_tail_weights` | random, n = 500 000, 90% weights 1 – 10, 10% weights 10⁸ – 10⁹ |
| `06_power_law` | n = 500 000, power-law degrees with a few high-degree hubs, weights 1 – 1000 |
| `07_grid_2d` | 700 × 700 grid, edges both ways, corner to opposite corner, weights 1 – 100 |
| `08_path` | single path `0 → 1 → … → n-1`, n = 1 000 000, weights 1 – 100 |
| `09_layered` | 40 layers of 12 500 vertices, edges only to the next layer, weights 1 – 1000 |
| `10_unreachable` | random, n = 500 000, no edges into `n-1` (answer −1) |
| `11_early_exit` | random, n = 500 000, plus an edge `0 → n-1` of weight 1 (answer 1) |
| `12_many_small` | 1000 random graphs, n = 500, m = 2 000 each |

## Larger graphs (Linux / WSL / SSH)

Requirements: Python 3 and `g++` with OpenMP. From the repository root:

```bash
python3 benchmark/scaling.py
```

This builds fresh binaries and generates graphs with 250,000, 1,000,000, 2,000,000
and 4,000,000 vertices, each with four outgoing edges (up to 16 million edges).
One edge per vertex forms a directed cycle to guarantee reachability; the other
destinations are random. Weights are 1–1000 and the seed is fixed at 20261107.
Parallel edges and self-loops are allowed. This is a separate family from tests 01–12.

The script compares Dijkstra with delta-stepping on 1/2/4/8/16 threads, using one warmup
and five measured runs per configuration in shuffled order. Compilation, generation
and the initial reference answer are outside the timer. It prints separate **compute**
and **whole-process** timings. Compute includes working-structure initialization,
solving and cleanup, including the light/heavy split for delta-stepping; it excludes
reading/building the input graph and printing. Timers exist only in compiled copies
under `results`; the C++ source files in `src` are untouched.

Build copies expose all distances for validation against the reference. Delta-stepping's
final copy from atomic distances is included in compute time. Whole-process time includes
this full output and therefore differs from the normal scalar-output program. Errors or
timeouts stop the script.

Outputs go to a new `benchmark/results/<timestamp>/` directory: `raw.csv`,
`summary.csv`, machine/compiler/source metadata, generated inputs and binaries.
The final terminal table shows compute medians and speedup versus Dijkstra.
CSV retains medians, ranges and both speedups: versus Dijkstra and versus
single-thread delta-stepping, separately for compute and whole-process time.
Existing `median_s`/`speedup_vs_*` CSV fields refer to whole-process time; the new
`compute_*` fields refer to computations. Results and large generated inputs are ignored by Git.

The 4-million-vertex random case is the family where earlier measurements showed
roughly 3–4× compute speedup versus Dijkstra. This is an observed result, not a fixed
value: other machines, loads, graphs or seeds can produce smaller gains or slowdowns.

Quick check: `python3 benchmark/scaling.py --sizes 1000 10000 --threads 1 2 --repeat 2`.
Use `--sizes`, `--threads`, `--degree`, `--repeat`, `--warmups`, `--timeout` and
`--output` to change the experiment. Optional `--cpus` accepts an ordered list of CPU
IDs; it uses `taskset` and the first p CPUs for p threads. Without this option, the script
automatically selects distinct cores on one socket if enough are available; otherwise
it uses OpenMP's placement. Actual CPU lists are recorded in metadata. Pinning requires
`taskset` and does not reserve the cores. Keep the original tests as limiting cases too.

To focus on the largest random case: `python3 benchmark/scaling.py --sizes 4000000`.
Use `--seed` to test another independently generated graph of the same family.

Additional controlled cases: `--weights unit` assigns weight 1 while preserving the
random graph's topology; `--degree 16` increases its outgoing degree; `--degree 1`
leaves just the directed cycle. `--graph layered --layers 32 --weights unit` creates
32 layers after the source, with edges only to the next layer. A backbone guarantees
reachability and each nonterminal, nonsource vertex gets `degree-1` extra random
edges. The source reaches the whole first layer and the final layer has no outgoing
edges, so its actual edge count differs from `n*degree` and is recorded in CSV.

Server results and interpretation: [REPORT.md](REPORT.md), [summary CSV](report_summary.csv).
