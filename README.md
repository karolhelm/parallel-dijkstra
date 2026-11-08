# parallel-dijkstra

Porównanie jednowątkowej Dijkstry z równoległym algorytmem delta-stepping
Ulricha Meyera i Petera Sandersa. Wersja równoległa używa OpenMP.
Oba algorytmy liczą odległości od wierzchołka 0 do wszystkich wierzchołków.

Źródła: [Dijkstra](src/dijkstraOneThread.cpp) i [delta-stepping](src/dijkstraDeltaStepping.cpp).

## Wymagania

Linux lub WSL, Python 3 i g++ z OpenMP.
Python korzysta tylko z biblioteki standardowej.

## Uruchomienie benchmarku

Polecenia wykonuje się z katalogu projektu:

```bash
# Losowy: 1 graf z 4 mln wierzchołków, po 3 pomiary każdej konfiguracji
./run.sh --sizes 4000000

# Trzy różne grafy tego samego rozmiaru
./run.sh --sizes 4000000 --graph-count 3

# Warstwowy: domyślnie 2 mln wierzchołków
./run.sh --graph layered

# Ścieżka: domyślnie 10 tys. wierzchołków
./run.sh --graph path
```

`run.sh` uruchamia `benchmark/scaling.py` i przekazuje mu parametry.
Można też wywołać Python bezpośrednio:

```bash
python3 benchmark/scaling.py --graph layered
```

Bez parametrów skrypt bada jeden losowy graf z 4 mln wierzchołków.
Własne rozmiary oraz liczbę wątków można podać tak:

```bash
./run.sh --graph layered --sizes 1000000 2000000 --threads 1 2 4 8
```

Seria losowa na serwerze, z dodatkowym pomiarem dla 72 wątków:

```bash
./run.sh --graph random --sizes 4000000 --graph-count 3 --threads 1 2 4 8 16 72
```

Krótka próba:

```bash
./run.sh --sizes 1000 10000 --threads 1 2 --repeat 2
```

## Rodzaje grafów

| Parametr | Domyślny rozmiar | Konstrukcja |
|---|---:|---|
| `--graph random` | 4 mln | Skierowany cykl i dodatkowe krawędzie do losowych celów |
| `--graph layered` | 2 mln | Źródło i 32 warstwy, krawędzie tylko do następnej warstwy |
| `--graph path` | 10 tys. | Ścieżka `0 → 1 → … → n-1`, dokładnie `n-1` krawędzi |

Wagi są losowane z zakresu 1-1000. Dla każdego rozmiaru domyślnie powstaje jeden
graf. Parametr `--graph-count` zmienia tę liczbę dla każdego typu grafu.
Kolejne grafy używają ziaren 20261107, 20261108, 20261109 itd.,
żeby można było odtworzyć te same dane. Dla ścieżki zmieniają się tylko wagi.
Wszystkie generowane wierzchołki są osiągalne ze źródła.

- **Losowy:** domyślnie z każdego wierzchołka wychodzą cztery krawędzie:
  jedna do następnego w cyklu i trzy do losowych celów. Cykl zapewnia osiągalność.
  Dopuszczone są pętle i krawędzie równoległe. Dla 4 mln wierzchołków jest 16 mln krawędzi.
- **Warstwowy:** wierzchołek 0 łączy się z całą pierwszą warstwą.
  Między kolejnymi warstwami powstają połączenia zapewniające osiągalność każdego
  wierzchołka oraz dodatkowe losowe krawędzie. Ostatnia warstwa nie ma krawędzi
  wychodzących. Szerokie fronty pozwalają dzielić pracę między wątki, ale zysk zależy
  od rozmiaru grafu i kosztów synchronizacji.
- **Ścieżka:** każdy wierzchołek poza ostatnim ma jedną krawędź do następnego.
  Pokazuje przypadek z małą ilością pracy równoległej.

`--degree` określa liczbę krawędzi wychodzących w grafie losowym (domyślnie 4).
W warstwowym daje `degree-1` dodatkowych krawędzi z każdego wierzchołka
poza źródłem i ostatnią warstwą. `--degree 1` dla grafu losowego zostawia sam cykl.

Liczbę warstw można zmienić przez `--layers`, a liczbę pomiarów jednego grafu
przez `--repeat`. Domyślnie są to trzy pomiary dla każdego typu grafu.

## Pomiary i poprawność

1. Python kompiluje źródła C++ bez zmieniania ich treści.
2. Generuje graf i uruchamia Dijkstrę po odpowiedź wzorcową, osobno dla każdego grafu.
3. Dla każdego rozmiaru mierzy `--graph-count` grafów (domyślnie jeden).
   Każdą konfigurację na każdym grafie mierzy domyślnie trzy razy.
   Domyślne liczby wątków delta-stepping to 1, 2, 4, 8 i 16; Dijkstra używa jednego.
   W każdej rundzie kolejność konfiguracji jest mieszana.
4. Porównuje wszystkie odległości z wzorcem i liczy mediany osobno dla każdego grafu.
   Przyspieszenie to iloraz median czasów, a nie mediana ilorazów.

Czas **compute** mierzy C++ wokół wywołania funkcji. Obejmuje inicjalizację,
obliczenia i zwolnienie struktur roboczych. W delta-stepping obejmuje także podział
light/heavy i skopiowanie odległości atomowych do wyniku. Wczytywanie grafu
i wypisywanie odległości są poza tym czasem.

Czas **whole** mierzy Python: obejmuje cały proces wraz z I/O.
Kompilacja i generowanie grafu nie wchodzą do żadnego z tych czasów.

Skrypt ustawia liczbę wątków OpenMP i wyłącza jej dynamiczną zmianę.
Rozmieszczeniem wątków na rdzeniach zajmują się OpenMP i system operacyjny.

## Wyniki

Wyniki pojawiają się w terminalu: czasy kolejnych pomiarów, a po każdym grafie
tabela median compute i zysków względem Dijkstry. Numer grafu jest
widoczny przy pomiarach i tabelach. Każdy graf ma osobną tabelę median.
Zysk poniżej 1 oznacza spowolnienie.
Graf i skompilowane programy są w katalogu tymczasowym, usuwanym po zakończeniu.
Skrypt nie zapisuje plików z wynikami. W razie potrzeby można zachować tekst:

```bash
./run.sh --graph layered > wyniki.txt
```

## Samodzielna kompilacja i format danych

```bash
g++ src/dijkstraOneThread.cpp -O3 -std=c++17 -o dijkstraOneThread
g++ src/dijkstraDeltaStepping.cpp -O3 -std=c++17 -fopenmp -o dijkstraDeltaStepping
```

Na wejściu jest liczba grafów `z`, a dla każdego grafu: `n m` i `m` wierszy
`u v w`. Indeksy wierzchołków to 0..n-1; wagi są nieujemnymi liczbami całkowitymi.

Obie funkcje zwracają `vector<long long>`. Programy wypisują na stdout
po jednym wierszu odległości dla każdego grafu, ze spacjami między wartościami.
`-1` oznacza nieosiągalny wierzchołek. Na stderr wypisują
`BENCH_SOLVE <sekundy>`, czyli sumę czasów obliczeń dla wszystkich grafów z wejścia.

## Raport i literatura

[Raport projektu](raport.pdf) opisuje implementację i pomiary na serwerze oraz laptopie.
[Prezentacja](prezentacja.pdf) zawiera siedem slajdów o algorytmach, OpenMP i wynikach.
W przedstawionych seriach wykonano po trzy pomiary dla grafów losowych oraz po pięć
dla ścieżki i grafu warstwowego. Obecnie skrypt domyślnie wykonuje po trzy pomiary.

U. Meyer, P. Sanders, *Δ-stepping: a parallelizable shortest path algorithm*,
Journal of Algorithms 49(1), 114-152, 2003.
