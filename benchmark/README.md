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
