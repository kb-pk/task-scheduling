import csv
from random import randint
import numpy as np
import pandas as pd
from sklearn.utils import shuffle

from .BaseMethod import BaseMethod
from .BaseMethod import Lang
import scheduler.Common as Common

class MichiganMethod(BaseMethod):
    """
    Implementacja algorytmu w podejściu Michigan.
    Reprezentacja:
      - Wiersz DataFrame = jedna maszyna (osobnik).
      - Kolumny = kolejne pozycje (sloty) zadań; brak zadania oznaczony NaN.
    Operatory:
      - Krzyżowanie: wymiana ogonów między parami maszyn (top vs bottom).
      - Mutacja: tasowanie (shuffle) fragmentu chromosomu do pierwszego NaN.
    Ocena:
      - Obliczane czasy pracy (busy) każdej maszyny.
      - Makespan = max busy.
      - Energia = suma (busy*P_busy + idle*P_idle).
      - W zależności od trybu (makespan / energy) sortowana jest populacja.
    """
    def __init__(self, iterations=100, pm=0.01, show_chart=True):
        """
        Inicjalizacja obiektu algorytmu.
        :param iterations: liczba epok optymalizacji
        :param pm: prawdopodobieństwo mutacji chromosomu
        :param show_chart: czy rysować wykres Gantta
        """
        super().__init__(show_chart=show_chart)
        self.iterations = iterations
        self.pm = pm
        self.population = None         # bieżąca populacja (DataFrame)
        self.best_population = None    # najlepsza znaleziona populacja (DataFrame)
        self.best_score = None         # wartość optymalizowanej metryki (lower = better)
        self.other_score = None        # druga metryka (informacyjnie)

    def get_method_name(self):
        """
        Zwraca unikalną nazwę metody (używana w plikach wynikowych).
        """
        return "michigan"

    def get_method_description(self, lang: Lang):
        """
        Opis tekstowy algorytmu w wybranym języku.
        :param lang: Lang.PL lub Lang.EN
        :return: opis (str)
        """
        if lang == Lang.PL:
            return """
                Algorytm oparty o podejście Michigan.
                
                Osobnik - reprezentacja pojedynczej maszyny z pakietu maszyn. Składa się z 1 chromosomu.
                Chromosom - reprezentacja przypisanego do osobnika (maszyny) zestawu zadań.
                Gen - reprezentacja pojedynczego zadania z pakietu zadań. 

                Selekcja - brak selekcji pomiędzy epokami.
                
                Krzyżowanie - n-punktowe, każdy osobnik bierze udział.
                
                Mutacja - mieszanie (shuffle) genów (zadań) w chromosomie.
                """.strip()
        elif lang == Lang.EN:
            return """
                Algorithm based on the Michigan approach.
                
                Entity - a representation of a single machine from the machine array (one chromosome).
                Chromosome - tasks assigned to the entity (machine).
                Gene - a single task index.
                
                Selection - none between epochs.
                
                Crossover - n-point, every entity participates.
                
                Mutation - shuffling of genes (tasks) inside the chromosome.
                """.strip()

    def initialize(self):
        """
        Buduje populację początkową oraz wyznacza jej ocenę,
        ustawiając wartości najlepsze na starcie.
        """
        self.population = self._generate_population(self.machines.index.values, self.tasks.index.values)
        self.population, self.best_score, self.other_score = self._sort_population(self.population)
        self.best_population = self.population.copy()

    def optimize(self):
        """
        Pętla główna optymalizacji:
          1. Krzyżowanie populacji.
          2. Mutacja wyników.
          3. Ocena (sortowanie) nowej populacji.
          4. Aktualizacja najlepszego rozwiązania.
        """
        for _ in range(self.iterations):
            crossed = self._cross(self.population)
            mutated = self._mutation(crossed, self.pm)
            mutated, current_score, other = self._sort_population(mutated)
            if current_score < self.best_score:
                self.best_population = mutated.copy()
                self.best_score = current_score
                self.other_score = other
            self.population = mutated
    
    def get_best_solution(self):
        """
        Zwraca najlepszą aktualnie populację (po optymalizacji).
        """
        return self.best_population

    def _generate_population(self, machines, tasks):
        """
        Tworzy populację początkową:
          - Tasuje listę zadań.
          - Rozdziela zadania „kolumnami” po maszynach (rundy przydziału).
          - Wypełnia pozostałe komórki NaN.
        :param machines: tablica identyfikatorów maszyn
        :param tasks: tablica identyfikatorów zadań
        :return: DataFrame populacji
        :raises ValueError: gdy maszyn jest więcej niż zadań
        """
        if len(machines) > len(tasks):
            raise Exception('Each machine must have at least one task')
        tasks_cpy = tasks.copy()
        np.random.shuffle(tasks_cpy)
        arr = np.zeros((len(machines), len(tasks_cpy)))
        arr.fill(np.nan)
        col = -1
        for i, t in enumerate(tasks_cpy):
            m = i % len(machines)
            if m == 0:
                col += 1
            arr[m][col] = t
        return self._arr_to_df(arr, machines)

    def _arr_to_df(self, data, ids):
        """
        Konwertuje macierz numpy na DataFrame o kolumnach task_i.
        :param data: macierz (maszyny x sloty)
        :param ids: indeksy wierszy (ID maszyn)
        :return: DataFrame
        """
        cols = [f"task_{i}" for i in range(data.shape[1])]
        df = pd.DataFrame(data=data, index=ids, columns=cols)
        df.index.name = 'machines'
        return df

    @staticmethod
    def _last_task_index(chrom):
        """
        Zwraca indeks ostatniego rzeczywistego zadania w chromosomie
        (pozycja przed pierwszym NaN).
        :param chrom: tablica z ID zadań i NaN
        :return: indeks (int)
        """
        for i in range(len(chrom)):
            if np.isnan(chrom[i]):
                return i - 1
        return len(chrom) - 1

    def _mutation(self, population, pm):
        """
        Mutacja populacji:
          - Dla każdej maszyny z prawdopodobieństwem pm tasuje prefix chromosomu.
        :param population: DataFrame populacji
        :param pm: prawdopodobieństwo mutacji
        :return: zmutowana populacja (in-place)
        """
        for m_id in population.index:
            if np.random.uniform(0.0, 1.0) <= pm:
                chrom = population.loc[m_id].values
                last = self._last_task_index(chrom)
                if last > 0:
                    np.random.shuffle(chrom[:last+1])
        return population

    def _cross_pair(self, first, second):
        """
        Krzyżuje dwa chromosomy (maszyny) przez wymianę segmentów ogonowych.
        :param first: tablica (chromosom 1)
        :param second: tablica (chromosom 2)
        """
        size_first = self._last_task_index(first) + 1
        size_second = self._last_task_index(second) + 1
        cp1 = randint(1, size_first) if size_first > 1 else 1
        cp2 = randint(1, size_second) if size_second > 1 else 1
        tmp_first = np.concatenate((first[:cp1], second[cp2:size_second]), axis=0)
        tmp_second = np.concatenate((second[:cp2], first[cp1:size_first]), axis=0)
        first[:len(tmp_first)] = tmp_first
        first[len(tmp_first):] = np.nan
        second[:len(tmp_second)] = tmp_second
        second[len(tmp_second):] = np.nan

    def _split_population(self, population):
        """
        Dzieli populację na dwie połowy (top, bottom) i tasuje kolejność w każdej.
        :param population: DataFrame populacji
        :return: (top_df, bottom_df)
        """
        parts = np.array_split(population, 2)
        top = shuffle(parts[0])
        bottom = shuffle(parts[1])
        return top, bottom

    def _cross(self, population):
        """
        Krzyżuje populację parami maszyn (z top i bottom).
        :param population: DataFrame populacji
        :return: nowa populacja po krzyżowaniu
        """
        top, bottom = self._split_population(population)
        limit = (len(population) + 1) / 2
        for i in range(int(limit)):
            self._cross_pair(top.values[i], bottom.values[i])
        return pd.concat([top, bottom], axis=0)

    def _calc_times(self, population):
        """
        Buduje tablicę [machine_id, busy_time] dla każdej maszyny.
        :param population: DataFrame populacji
        :return: ndarray (N,2)
        """
        tmp = np.zeros(shape=(len(population), 2), dtype=np.float64)
        for m_id in population.index.values:
            tmp[m_id] = self._time_on_machine(population.iloc[m_id].values, m_id)
        return tmp

    def _time_on_machine(self, tasks_ids, machine_id):
        """
        Sumuje czasy ETC zadań przypisanych do danej maszyny.
        :param tasks_ids: tablica ID zadań (z NaN jako wypełnieniem)
        :param machine_id: ID maszyny
        :return: (machine_id, suma_czasów)
        """
        s = 0.0
        for t in tasks_ids:
            if np.isnan(t):
                break
            s += self.etc[int(t)][int(machine_id)]
        return machine_id, s

    def _idle_times(self, tmp, mk):
        """
        Wylicza tablicę bezczynności (idle_time = makespan - busy).
        :param tmp: ndarray [machine_id, busy_time]
        :param mk: makespan
        :return: ndarray [machine_id, idle_time]
        """
        new_tmp = np.zeros_like(tmp)
        for i in range(len(tmp)):
            new_tmp[i][0] = tmp[i][0]
            new_tmp[i][1] = mk - tmp[i][1]
        return new_tmp

    def _sort_population(self, population):
        """
        Ocena i sortowanie populacji:
          1. Oblicz busy_time i makespan.
          2. Oblicz idle_time.
          3. Oblicz energię (busy + idle).
          4. W zależności od trybu (energy / makespan) wybierz ordering.
          5. Zwróć posortowany DataFrame oraz (best_score, other_score).
        :param population: DataFrame populacji
        :return: (sorted_population_df, best_score, other_score)
        """
        tmp = self._calc_times(population)
        tmp_sorted = tmp[tmp[:,1].argsort()]
        mk = tmp_sorted[:,1][-1]
        idle = self._idle_times(tmp, mk)
        energy_arr = np.zeros_like(tmp)
        # energia idle
        for idle_row in idle:
            mid = int(idle_row[0])
            energy_arr[mid][0] = mid
            energy_arr[mid][1] = self.machines.values[mid][3] * idle_row[1]
        # energia busy
        for busy_row in tmp:
            mid = int(busy_row[0])
            energy_arr[mid][1] += self.machines.values[mid][2] * busy_row[1]
        energy_sorted = energy_arr[energy_arr[:,1].argsort()]

        if Common.scheduling_mode == Common.ENERGY_MODE:
            ordering_ids = energy_sorted[:,0].astype(int)
            other = mk
            best = energy_sorted[:,1][-1]
        else:
            ordering_ids = tmp_sorted[:,0].astype(int)
            other = energy_sorted[:,1][-1]
            best = mk

        ordered_df = self._arr_to_df(population.values[ordering_ids], ordering_ids)
        return ordered_df, best, other

    def build_schedule_map(self, solution_df):
        """
        Konwersja najlepszej populacji (DataFrame) na mapę harmonogramu:
          {machine_id: [task_id, ...]} z pominięciem NaN.
        :param solution_df: DataFrame najlepszej populacji
        :return: dict[int, list[int]]
        """
        schedule_map = {m_id: [] for m_id in solution_df.index.values}
        for machine_id in solution_df.index.values:
            for task_id in solution_df.loc[machine_id].values:
                if not np.isnan(task_id):
                    schedule_map[machine_id].append(int(task_id))
        return schedule_map
    

if __name__ == "__main__":
    alg = MichiganMethod(iterations=100, pm=0.01)
    alg.run()