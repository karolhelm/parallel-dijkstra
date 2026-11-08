# Projekt z programowania współbieżnego

## Zrównoleglenie SSSP: Dijkstra i delta-stepping

Data pomiarów: 7 listopada 2026.

## 1. Cel i zadanie

Celem projektu było zrównoleglenie wcześniej napisanego rozwiązania problemu najkrótszych ścieżek. Punktem odniesienia jest jednowątkowa Dijkstra z kolejką priorytetową. Wersja współbieżna wykorzystuje delta-stepping i OpenMP. Wątki współpracują przy rozwiązywaniu jednego dużego grafu; przypadki testowe nie są rozdzielane między niezależne wątki.

Dany jest graf skierowany o nieujemnych wagach całkowitych. Obliczane są odległości od wierzchołka 0 do wszystkich osiągalnych wierzchołków. Zachowano pierwotny interfejs programu: na wyjściu znajduje się odległość do n-1 albo -1. Usunięto wcześniejsze zakończenie po ustaleniu wyniku dla celu, dzięki czemu obie wersje wykonują pełne SSSP.

## 2. Sposób zrównoleglenia

Dijkstra przechowuje wstępne odległości i kolejkę priorytetową. Zdejmuje wierzchołek o najmniejszej odległości, pomija nieaktualne wpisy i relaksuje jego krawędzie. Utrzymanie ścisłej kolejności odległości ogranicza możliwość bezpośredniego zrównoleglenia tego rozwiązania.

Delta-stepping [1] grupuje wierzchołki w kubełkach o przedziałach odległości [iΔ, (i+1)Δ). Krawędzie dzieli na lekkie (waga ≤ Δ) i ciężkie (waga > Δ). Dla najmniejszego niepustego kubełka powtarza relaksację lekkich krawędzi aż do jego opróżnienia. Następnie relaksuje ciężkie krawędzie wierzchołków zebranych podczas tej fazy. W implementacji Δ = max(1, floor(2W/m)), gdzie W jest sumą wag; dla m=0 przyjmuje się Δ=1.

Pętle po wierzchołkach bieżącego frontu są dzielone przez omp for. Odległości są atomowe; compare_exchange_weak realizuje aktualizację minimum. Każdy wątek zapisuje udane relaksacje do własnego bufora. Jeden wątek, w sekcji single, scala bufory do wspólnej mapy kubełków. Domyślne bariery OpenMP oddzielają fazy pracy i scalania. Zewnętrzny region parallel utrzymuje jeden zespół wątków przez całe wywołanie.

Sekwencyjne pozostają wczytywanie, budowa grafu, podział light/heavy, inicjalizacja oraz scalanie kubełków. Koszt atomików i barier ogranicza zysk. Statyczny podział wierzchołków nie musi równoważyć liczby krawędzi przy nierównych stopniach. Front o szerokości jeden, np. ścieżka, praktycznie nie daje pracy równoległej.

## 3. Metoda pomiarów

Użyto jednego grafu z 4 000 000 wierzchołków i 16 000 000 krawędzi, ziarno 20261107. Z każdego wierzchołka wychodzą cztery krawędzie: jedna tworzy skierowany cykl zapewniający osiągalność, trzy prowadzą do losowych celów. Wagi są losowane równomiernie z 1-1000. Dopuszczono pętle i krawędzie równoległe. Pliki wejściowe na obu maszynach mają identyczny SHA-256.

Dla każdej konfiguracji wykonano rozgrzewkę i pięć pomiarów, w przemieszanej kolejności. Tabele zawierają mediany. Czas compute rozpoczyna się po odczytaniu i zbudowaniu wejściowego grafu, a kończy przed wypisywaniem. Obejmuje struktury robocze, inicjalizację, obliczenia i sprzątanie; w delta-stepping także podział light/heavy oraz zebranie odległości atomowych do tablicy. Czas whole obejmuje cały proces kopii benchmarkowej.

Timery są dodawane tylko do kopii kompilowanych przez skrypt. Kopie wypisują całą tablicę odległości i każdy wynik jest porównywany z Dijkstrą poza pomiarem. Wszystkie 60 mierzonych uruchomień zakończyło się zgodnością odpowiedzi. Normalne źródła C++ zachowują wyjście dla n-1. Czas whole kopii uwzględnia pełne wyjście i nie jest pomiarem zwykłego programu z pojedynczym wynikiem.

| Środowisko | Laptop / WSL2 | Serwer wydziałowy |
|---|---|---|
| Procesor | Intel Core i7-1260P | 4 × Xeon Gold 6154 |
| CPU | 16 logicznych w WSL | 72 rdzenie / 144 wątki sprzętowe |
| Użyte wątki | 1, 2, 4, 8, 16 | 1, 2, 4, 8, 16; jeden NUMA |
| Kompilator | GCC 11.4, C++17, -O3 | GCC 15.2, C++17, -O3 |
| OpenMP | dynamic=FALSE, places=cores | dynamic=FALSE, places=cores |

Na WSL skrypt nie wybierał jawnej listy CPU; wiązaniem wątków sterowały ustawienia OpenMP. Topologia maszyny wirtualnej nie jest pełnym opisem rdzeni fizycznych laptopa. Na serwerze użyto po jednym wątku sprzętowym z różnych rdzeni jednego procesora/NUMA. Serwer był współdzielony (load około 296-302). Różne kompilatory i polityki przypięcia ograniczają bezpośrednie porównanie sprzętu. Pięć powtórzeń jednego grafu nie zastępuje testów wielu ziaren i rodzin danych.

## 4. Wyniki - mediany czasu obliczeń

Zysk = mediana czasu Dijkstry / mediana czasu danej wersji na tej samej maszynie.

| Wersja | WSL [s] | Zysk WSL | Serwer [s] | Zysk serwer |
|---|---|---|---|---|
| Dijkstra | 8,505 | 1,00× | 4,317 | 1,00× |
| Δ, 1 w. | 3,927 | 2,17× | 2,265 | 1,91× |
| Δ, 2 w. | 3,414 | 2,49× | 2,043 | 2,11× |
| Δ, 4 w. | 4,308 | 1,97× | 1,641 | 2,63× |
| Δ, 8 w. | 4,092 | 2,08× | 1,385 | 3,12× |
| Δ, 16 w. | 3,055 | 2,78× | 1,304 | 3,31× |

Na serwerze czas obliczeń delta-stepping maleje wraz z liczbą wątków: z 2,265 s dla jednego do 1,304 s dla 16. Względem Dijkstry daje to 3,31×. Samo zwiększenie liczby wątków w delta-stepping daje jednak 1,74×; część przewagi pochodzi już ze zmiany algorytmu (Δ1 jest około 1,91× szybsze od Dijkstry).

Na WSL najlepsza mediana obliczeń wyniosła 3,055 s przy 16 wątkach, czyli 2,78× względem Dijkstry i 1,29× względem Δ1. Skalowanie nie jest monotoniczne: 4 i 8 wątków miały mediany gorsze od Δ1. Rozrzut jest duży: Dijkstra 4,338-10,028 s, a Δ16 2,587-8,832 s. Zmienność warunków wykonania może istotnie wpływać na ilorazy median; te dane nie dowodzą trwałej przewagi 16 wątków na laptopie.

Dla całego procesu kopii zysk Δ16 względem Dijkstry wyniósł 1,92× na WSL (14,913 → 7,782 s) i 1,54× na serwerze (8,276 → 5,370 s). Jest mniejszy niż dla compute. Pomiar obejmuje również etapy sekwencyjne i wypisywanie; bez osobnych timerów nie wyznaczamy dokładnego procentowego udziału każdego z nich.

## 5. Kompilacja i odtworzenie

Wymagania: Linux lub WSL, g++ z OpenMP; dla benchmarku Python 3 (biblioteka standardowa), a dla przypięcia CPU także taskset.

```bash
g++ src/dijkstraOneThread.cpp -O3 -std=c++17 -o dijkstraOneThread
g++ src/dijkstraDeltaStepping.cpp -O3 -std=c++17 -fopenmp -o dijkstraDeltaStepping
OMP_NUM_THREADS=16 OMP_DYNAMIC=FALSE ./dijkstraDeltaStepping < test.in
```

Wejście: liczba grafów z, następnie dla każdego n m i m wierszy u v w. Indeksy 0..n-1, wagi nieujemne.

```bash
python3 benchmark/scaling.py --sizes 4000000
```

Skrypt kompiluje kopie z timerami i zapisuje raw.csv, summary.csv oraz metadata.json w benchmark/results/.

## 6. Wnioski

Projekt zrównolegla sam algorytm dla pojedynczego przypadku. Wyniki pokazują praktyczny zysk na dużym losowym grafie, szczególnie na serwerze, oraz ograniczenia części sekwencyjnych i synchronizacji. W badanej serii uzyskano przyspieszenie 3,31× dla median czasu obliczeń względem Dijkstry. Do oceny ogólności wyniku warto użyć innych ziaren, rozmiarów oraz przypadków o wąskich frontach.

## Literatura i dane

[1] U. Meyer, P. Sanders, Δ-stepping: a parallelizable shortest path algorithm, Journal of Algorithms 49(1), 114-152, 2003. https://doi.org/10.1016/S0196-6774(03)00076-2

Seria WSL: benchmark/results/20261107-222438. Seria serwerowa: benchmark/results/20261107-222252. Podstawowe porównanie WSL z serwerem wykorzystuje te dwie serie. Dodatkowe pomiary z 8 listopada opisano oddzielnie w uzupełnieniu. Zgodność źródeł potwierdzają ich skróty w metadata.json.

SHA-256 wejścia: `e99dd46edd07898a59bb9da4e4e9378bcbd9d0837e8c77f05136dcf9b3ed7c43`.

## 7. Uzupełnienie - inne typy grafów (8 listopada 2026)

8 listopada 2026 wykonano na tym samym serwerze trzy pełne serie: dwa dodatkowe typy grafów oraz ponowny losowy test kontrolny. Dla każdej konfiguracji: jedna rozgrzewka i pięć pomiarów w przemieszanej kolejności, p = 1, 2, 4, 8, 16. Kod, kompilator, ustawienia OpenMP i przypięcie CPU są zgodne z wcześniejszą serią serwerową. Wszystkie 90 mierzonych wyników przeszło porównanie pełnych tablic odległości z Dijkstrą. Serwer był współdzielony; load 1 min: 299-332.

Losowy: n = 4 000 000, m = 16 000 000, rodzina jak w części podstawowej. Warstwowy: n = 4 000 000, m = 15 624 996, 32 warstwy za źródłem; krawędzie prowadzą wyłącznie do następnej warstwy. Cykl: n = m = 250 000, krawędzie 0 → 1 → ... → n-1 → 0. We wszystkich seriach wagi 1-1000, ziarno 20261107. Cykl jest mniejszym testem struktury grafu; jego czasów bezwzględnych nie porównujemy z czasami grafów czteromilionowych.

Próba cyklu n = 250 000 na WSL została przerwana po przekroczeniu 120 s przez Δ16 w drugim pomiarze. Nie liczono median z niepełnej serii i nie włączono jej do tabeli. Zestawienie poniżej dotyczy wyłącznie kompletnych pomiarów serwera.

Mediany compute [s]. Zysk Δ16 jest liczony względem Dijkstry.

| Graf | Dijkstra | Δ1 | Δ2 | Δ4 | Δ8 | Δ16 | Zysk Δ16 |
|---|---|---|---|---|---|---|---|
| Losowy | 4,9409 | 2,3360 | 2,0347 | 1,6333 | 1,4095 | 1,4143 | 3,49× |
| Warstwowy | 4,3110 | 1,9519 | 1,9513 | 1,6674 | 1,5232 | 1,5654 | 2,75× |
| Cykl | 0,0032 | 0,9305 | 1,2539 | 1,3676 | 1,8866 | 10,3766 | 0,0003× |

Na cyklu Δ16 jest około 3239× wolniejsze od Dijkstry i 11,2× wolniejsze od Δ1. Front ma szerokość jeden, więc nie ma relaksacji do podziału między wątki. Pozostają koszty barier, atomików i kubełków. Dijkstra ma tu w kolejce najwyżej jeden aktywny wpis.

Na grafie warstwowym Δ16 daje 2,75× względem Dijkstry; w losowym pomiarze kontrolnym jest to 3,49×. Najlepsza mediana delta-stepping przypada odpowiednio na 8 i 8 wątków. Przejście od Δ1 do najlepszej konfiguracji warstwowej daje 1,28×. Szerokie fronty umożliwiają podział pracy, lecz sam rozmiar wejścia nie gwarantuje przyspieszenia. O wyniku współdecydują struktura grafu, liczba faz i synchronizacja. Jedno ziarno na rodzinę nadal nie uzasadnia wniosku o wszystkich grafach danego typu.

Odtworzenie (domyślnie pięć pomiarów i jedna rozgrzewka):

```bash
python3 benchmark/scaling.py --sizes 4000000
python3 benchmark/scaling.py --sizes 4000000 --graph layered --layers 32
python3 benchmark/scaling.py --sizes 250000 --degree 1
```

Surowe wyniki: benchmark/graph_types.csv. Seria kontrolna: 20261108-server-random-4m; warstwowa: 20261108-server-layered-4m; cykl: 20261108-server-cycle-250k. Metadane są w odpowiadających katalogach benchmark/results/. Pliki wejściowe pozostawiono na serwerze; odtwarzają je podane polecenia. Wartości w tabeli to mediany compute [s]; zysk = mediana Dijkstry / mediana Δ16.
