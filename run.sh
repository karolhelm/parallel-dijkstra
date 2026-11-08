#!/usr/bin/env bash
exec python3 "$(dirname "$0")/benchmark/scaling.py" "$@"

"""

Przykład uruchomienia z parametrami, podajemy typ grafu (random/layered/path), rozmiar
grafu, liczbę różnych grafów do testowania, liczbę wątków na których chcemy testować.

./run.sh --graph layered --sizes 1000000 2000000 --graph-count 3 --threads 1 2 4 8

"""