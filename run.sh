#!/usr/bin/env bash
exec > results.txt 2>&1

g++ src/dijkstraOneThread.cpp -O3 -std=c++17 -o dijkstraOneThread
g++ src/dijkstraDeltaStepping.cpp -O3 -std=c++17 -fopenmp -o dijkstraDeltaStepping

for test in benchmark/tests/*.in; do
    echo "Test: $test"

    expected="${test%.in}.out"
    
    echo OneThread:
    time ./dijkstraOneThread < $test > temp.out 
    diff temp.out $expected || break

    echo "DeltaStepping (1 thread)":
    time OMP_NUM_THREADS=1 OMP_DYNAMIC=FALSE ./dijkstraDeltaStepping < $test > temp.out
    diff temp.out $expected || break

    echo "DeltaStepping (4 thread)":
    time OMP_NUM_THREADS=4 OMP_DYNAMIC=FALSE ./dijkstraDeltaStepping < $test > temp.out
    diff temp.out $expected || break

    echo "DeltaStepping (8 thread)":
    time OMP_NUM_THREADS=8 OMP_DYNAMIC=FALSE ./dijkstraDeltaStepping < $test > temp.out
    diff temp.out $expected || break
done