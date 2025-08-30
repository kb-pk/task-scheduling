from __future__ import annotations
import math
import random
from typing import List, Tuple, Dict

import numpy as np
from sklearn.utils import shuffle

import scheduler.Common as Common
from .BaseMethod import BaseMethod, Lang


class PittPermMethod(BaseMethod):
    """
    Implementacja algorytmu GA w podejściu Pitt (reprezentacja permutowana) w zunifikowanym
    schemacie BaseMethod (initialize -> optimize -> get_best_solution -> build_schedule_map).

    Reprezentacja osobnika (individual):
      - Krotka (tasks_sequence, machines_chromosome)
        tasks_sequence: lista długości N (N = liczba zadań), permutacja identyfikatorów zadań.
        machines_chromosome: lista długości M (M = liczba maszyn), gdzie każdy gen mówi
          ile kolejnych zadań z tasks_sequence przypada na daną maszynę.
          Suma machines_chromosome == N.

    Interpretacja harmonogramu:
      - Pierwsze machines_chromosome[0] zadań z tasks_sequence trafia na maszynę 0,
        kolejne machines_chromosome[1] zadań na maszynę 1, itd.

    Ograniczenia wykonalności:
      - Każde zadanie może zostać przypisane tylko do jednej z maszyn spełniających wymagania
        bezpieczeństwa. Przy konstruowaniu osobnika zadania są przydzielane biorąc pod uwagę
        listę dopuszczalnych maszyn (tasks_to_machines).

    Operatory:
      - Crossover (Ordered Crossover – OX) na chromosomie zadań (tasks_sequence) – machines_chromosome
        dziedziczone wprost od rodziców (jak w implementacji pierwotnej).
      - Mutacje dwóch typów:
          * Swap mutation (S): zamiana dwóch zadań, o ile zachowany zostaje warunek wykonalności.
          * Transposition mutation (T): przeniesienie pojedynczego zadania „w inne miejsce” poprzez
            modyfikację machines_chromosome (zmiana liczby zadań na maszynach) oraz przetasowanie
            tasks_sequence odzwierciedlające przesunięcie.

    Funkcja oceny:
      - W zależności od Common.scheduling_mode minimalizujemy:
          * makespan (maksymalny czas wykonywania maszyn) – lub
          * całkowitą energię (busy + idle)
        Druga metryka zapisywana jest jako other_score wyłącznie informacyjnie.

    Wynik końcowy:
      - build_schedule_map() zwraca {machine_id: [task_id, ...]} odczytane z najlepszego osobnika.
    """
    def __init__(self,
                 iterations: int = 100,
                 population_size: int = 10,
                 pm_swap: float = 0.01,
                 pm_transposition: float = 0.01,
                 show_chart: bool = True):
        """
        :param iterations: liczba epok optymalizacji
        :param population_size: liczebność populacji (parzysta zalecana dla parowania w crossover)
        :param pm_swap: prawdopodobieństwo mutacji typu swap dla pojedynczego genu
        :param pm_transposition: prawdopodobieństwo mutacji typu transposition dla pojedynczego genu
        :param show_chart: czy rysować wykres Gantta po zakończeniu
        """
        super().__init__(show_chart=show_chart)
        self.iterations = iterations
        self.population_size = population_size
        self.pm_swap = pm_swap
        self.pm_transposition = pm_transposition

        # Mapa możliwych maszyn dla każdego zadania {task_id: [machine_id,...]}
        self.tasks_to_machines: Dict[int, List[int]] = {}
        # Populacja: lista osobników (tasks_sequence, machines_chromosome)
        self.population: List[Tuple[List[int], List[int]]] = []
        # Najlepszy osobnik + jego metryki
        self.best_individual: Tuple[List[int], List[int]] | None = None
        self.best_score: float | None = None
        self.other_score: float | None = None

    # ------------------------------------------------------------
    # Identyfikacja i opis
    # ------------------------------------------------------------
    def get_method_name(self) -> str:
        """
        Nazwa metody używana w plikach wynikowych.
        """
        return "pitt_perm"

    def get_method_description(self, lang: Lang):
        """
        Opis algorytmu w wybranym języku.
        """
        if lang == Lang.PL:
            return (
                """
                Algorytm oparty o podejście Pitt, reprezentacja permutowana.

                Osobnik - reprezentacja konkretnego harmonogramu zadań dla wszystkich maszyn. Składa się z 2 chromosomów.
                Chromosom 1 - lista zadań w konkretnej kolejności. Składa się z N (liczba zadań) genów.
                Chromosom 2 - liczba zadań z chromosomu 1 przypisanych do maszyn. Składa się z M (liczba maszyn) genów.
                Gen (chromosom 1) - pojedyncze zadanie z listy zadań.
                Gen (chromosom 2) - liczba zadań przypisanych do konkretnej maszyny. Indeks genu w chromosomie definiuje maszynę (machine_id).

                Selekcja - brak selekcji pomiędzy epokami.

                Krzyżowanie - PMX (partial mapped crossover), CX (cycle crossover), OX (ordered crossover). Każdy osobnik bierze udział.

                Mutacja - S (swap mutation - zamiana zadań pomiędzy maszynami) i T (transposition mutation - przeniesienie zadania jednej maszyny do harmonogramu drugiej).
                """
            )
        return (
            """
            Algorithm based on the Pitt approach, permutated representation.

            Entity - a representation of a particular schedule of tasks for all machines. Made up of 2 chromosomes.
            Chromosome 1 - array of tasks in a specific order. Made up of N (task number) genes.
            Chromosome 2 - number of tasks (taken from chromosome 1) assigned to machines. Made up of M (machine number) genes.
            Gene (chromosome 1) - a single task from the task array.
            Gene (chromosome 2) - number of tasks assigned to a specific machine. The index of the gene in a chromosome defined the machine (machine_id).

            Selection - no selection between epochs.

            Crossover - PMX (partial mapped crossover), CX (cycle crossover), OX (ordered crossover). Every entity takes part.

            Mutation - S (swap mutation - swaps tasks between machines) i T (transposition mutation - moves a task from one machine's schedule to another's).
            """
        )

    # ------------------------------------------------------------
    # Cykl życia (BaseMethod hooki)
    # ------------------------------------------------------------
    def initialize(self):
        """
        Inicjalizacja:
          - Budowa mapy tasks_to_machines (zadanie -> możliwe maszyny).
          - Generacja populacji początkowej (self.population_size osobników).
          - Ocena i wybór najlepszego osobnika startowego.
        """
        self.tasks_to_machines = self._map_tasks_to_possible_machines()
        self.population = [self._generate_individual() for _ in range(self.population_size)]
        self._evaluate_population_initial()

    def optimize(self):
        """
        Główna pętla optymalizacji:
          - Crossover całej populacji (Ordered Crossover na kolejnych parach po przetasowaniu).
          - Mutacja (swap + transposition) dla każdego osobnika.
          - Ocena, aktualizacja najlepszego osobnika.
        """
        for epoch in range(self.iterations):
            self.population = self._crossover_population(self.population)
            self.population = self._mutate_population(self.population)
            improved = self._evaluate_population_update_best()
            if improved:
                # Krótki log z aktualnym najlepszym wynikiem
                if Common.scheduling_mode == Common.MAKESPAN_MODE:
                    print(f"[{epoch}] New best makespan: {self.best_score:.4f} energy: {self.other_score:.4f}")
                else:
                    print(f"[{epoch}] New best energy: {self.best_score:.4f} makespan: {self.other_score:.4f}")

    def get_best_solution(self):
        """
        Zwraca najlepszego osobnika (krotka).
        """
        return self.best_individual

    def build_schedule_map(self, solution):
        """
        Konwersja najlepszego osobnika na mapę {machine_id: [task_ids]}.
        :param solution: najlepszy osobnik (tasks_sequence, machines_chromosome)
        """
        tasks_sequence, machines_chromosome = solution
        schedule_map = {m: [] for m in range(len(machines_chromosome))}
        offset = 0
        for m_id, count in enumerate(machines_chromosome):
            slice_tasks = tasks_sequence[offset:offset + count]
            schedule_map[m_id].extend(slice_tasks)
            offset += count
        return schedule_map

    def after_run(self, schedule_map, makespan, total_energy):
        """
        Zapis krótkiego logu do pliku tekstowego (CSV zapisuje baza).
        """
        if Common.scheduling_mode == Common.MAKESPAN_MODE:
            primary = makespan
            secondary = total_energy
        else:
            primary = total_energy
            secondary = makespan
        with open("results/result_pitt_perm", "a") as f:
            f.write(f"{primary},{secondary}\n")

    # ------------------------------------------------------------
    # Generowanie i ocena populacji
    # ------------------------------------------------------------
    def _map_tasks_to_possible_machines(self) -> Dict[int, List[int]]:
        """
        Dla każdego zadania wyznacza listę maszyn spełniających jego wymagania (cechy bezpieczeństwa).
        Zwraca: {task_id: [machine_id, ...]}
        """
        mapping = {}
        for task_id in self.tasks.index.values:
            allowed = []
            task_row = self.tasks.iloc[task_id]
            for machine_id in self.machines.index.values:
                if Common.can_execute_task_on_machine(self.machines.iloc[machine_id], task_row, self.features):
                    allowed.append(machine_id)
            mapping[task_id] = allowed
        return mapping

    def _generate_machines_chromosome(self) -> List[int]:
        """
        Konstruuje machines_chromosome rozdzielając zadania możliwie równo na maszyny.
        """
        n_tasks = len(self.tasks)
        n_machines = len(self.machines)
        base = math.floor(n_tasks / n_machines)
        chrom = [base] * n_machines
        remainder = n_tasks - base * n_machines
        for i in range(remainder):
            chrom[i] += 1
        return chrom

    def _assign_tasks_to_machines(self, machines_chromosome: List[int]) -> Dict[int, List[int]]:
        """
        Przypisuje zadania do maszyn, uwzględniając listę dopuszczalnych maszyn.
          - Zadania sortowane rosnąco po liczbie możliwych maszyn (heurystyka ograniczeń).
          - Wybór losowy spośród dostępnych maszyn, z kontrolą limitu (machines_chromosome[m_id]).
        Zwraca: {machine_id: [task_ids]}
        """
        machines_to_tasks = {m_id: [] for m_id in self.machines.index.values}
        # Zadania, które mają najmniej opcji – najpierw
        sorted_tasks = sorted(self.tasks_to_machines.items(), key=lambda kv: len(kv[1]))
        for task_id, possible in sorted_tasks:
            if len(possible) == 1:
                machines_to_tasks[possible[0]].append(task_id)
                continue
            while True:
                m = random.choice(possible)
                if len(machines_to_tasks[m]) < machines_chromosome[m]:
                    machines_to_tasks[m].append(task_id)
                    break
        return machines_to_tasks

    def _generate_individual(self) -> Tuple[List[int], List[int]]:
        """
        Tworzy pojedynczego osobnika:
          1. Generuje machines_chromosome (liczba zadań na maszynę).
          2. Przydziela zadania do maszyn z zachowaniem ograniczeń.
          3. Łączy listy zadań w jedną sekwencję (tasks_sequence) w kolejności maszyn.
        Zwraca (tasks_sequence, machines_chromosome).
        """
        machines_chromosome = self._generate_machines_chromosome()
        mapping = self._assign_tasks_to_machines(machines_chromosome)
        tasks_sequence: List[int] = []
        for m_id in mapping.keys():
            tasks_sequence.extend(mapping[m_id])
        return tasks_sequence, machines_chromosome

    def _evaluate_individual(self, individual: Tuple[List[int], List[int]]) -> Tuple[float, float]:
        """
        Oblicza (primary_metric, secondary_metric) dla osobnika:
          - makespan: maksymalna suma czasów zadań na maszynie
          - energy: suma busy + idle (wg parametrów maszyn)
        Zwraca (main_score, other_score) zgodnie z scheduling_mode.
        """
        tasks_seq, machines_chrom = individual
        offset = 0
        machine_times = [0.0] * len(machines_chrom)
        for m_id, count in enumerate(machines_chrom):
            for t in range(count):
                task_id = tasks_seq[offset + t]
                machine_times[m_id] += self.etc[task_id][m_id]
            offset += count
        makespan = max(machine_times)
        # Energia
        total_energy = 0.0
        for m_id, busy in enumerate(machine_times):
            p_busy = self.machines.values[m_id][2]
            p_idle = self.machines.values[m_id][3]
            total_energy += busy * p_busy + (makespan - busy) * p_idle
        if Common.scheduling_mode == Common.ENERGY_MODE:
            return total_energy, makespan
        return makespan, total_energy

    def _evaluate_population_initial(self):
        """
        Ocena populacji początkowej – ustawia best_individual / best_score / other_score.
        """
        for ind in self.population:
            main_val, other_val = self._evaluate_individual(ind)
            if self.best_individual is None or main_val < self.best_score:
                self.best_individual = self._clone_individual(ind)
                self.best_score = main_val
                self.other_score = other_val
        if Common.scheduling_mode == Common.MAKESPAN_MODE:
            print(f"Initial makespan: {self.best_score:.4f} energy: {self.other_score:.4f}")
        else:
            print(f"Initial energy: {self.best_score:.4f} makespan: {self.other_score:.4f}")

    def _evaluate_population_update_best(self) -> bool:
        """
        Ocena populacji po operatorach. Aktualizuje best jeśli znajdzie lepszego.
        Zwraca True jeżeli nastąpiła poprawa.
        """
        improved = False
        for ind in self.population:
            main_val, other_val = self._evaluate_individual(ind)
            if main_val < self.best_score:
                self.best_individual = self._clone_individual(ind)
                self.best_score = main_val
                self.other_score = other_val
                improved = True
        return improved

    # ------------------------------------------------------------
    # Operatory genetyczne
    # ------------------------------------------------------------
    def _crossover_population(self, population: List[Tuple[List[int], List[int]]]
                              ) -> List[Tuple[List[int], List[int]]]:
        """
        Ordered crossover (OX) na chromosomie tasks_sequence w parach
        (po przetasowaniu populacji). machines_chromosome dziedziczone
        bez zmian od odpowiedniego rodzica (jak w implementacji pierwotnej).
        """
        shuffled = shuffle(population)
        new_pop: List[Tuple[List[int], List[int]]] = []
        # jeśli nieparzysta populacja – ostatni osobnik przechodzi bez zmian
        limit = len(shuffled) - (len(shuffled) % 2)
        for i in range(0, limit, 2):
            dad_tasks, dad_mach = shuffled[i]
            mom_tasks, mom_mach = shuffled[i + 1]
            child_a_tasks, child_b_tasks = self._ordered_crossover(dad_tasks, mom_tasks)
            # dziedziczenie machines_chromosome – zachowujemy oryginalne (jak było)
            new_pop.append((child_a_tasks, dad_mach.copy()))
            new_pop.append((child_b_tasks, mom_mach.copy()))
        if len(shuffled) % 2 == 1:
            new_pop.append(self._clone_individual(shuffled[-1]))
        return new_pop

    def _ordered_crossover(self, dad: List[int], mom: List[int]) -> Tuple[List[int], List[int]]:
        """
        Ordered Crossover (OX):
          1. Losowy fragment (start:end) z matki trafia do córki, z ojca do syna.
          2. Pozostałe pozycje wypełniane w kolejności danych z drugiego rodzica.
        Zapewnia zachowanie permutacji (brak duplikatów).
        """
        size = len(mom)
        start, end = sorted(random.sample(range(size), 2))
        daughter = [-1] * size
        son = [-1] * size
        # Dziedziczenie segmentu
        daughter[start:end + 1] = mom[start:end + 1]
        son[start:end + 1] = dad[start:end + 1]
        # Elementy już użyte
        d_used = set(daughter[start:end + 1])
        s_used = set(son[start:end + 1])
        # Wypełnianie pozostałych pozycji
        d_idx = 0
        s_idx = 0
        for i in range(size):
            if daughter[i] == -1:
                while dad[d_idx] in d_used:
                    d_idx += 1
                daughter[i] = dad[d_idx]
                d_used.add(dad[d_idx])
                d_idx += 1
            if son[i] == -1:
                while mom[s_idx] in s_used:
                    s_idx += 1
                son[i] = mom[s_idx]
                s_used.add(mom[s_idx])
                s_idx += 1
        return daughter, son

    def _mutate_population(self, population: List[Tuple[List[int], List[int]]]
                           ) -> List[Tuple[List[int], List[int]]]:
        """
        Dla każdego osobnika iterujemy po genie tasks_sequence i:
          - z prawdopodobieństwem pm_swap wykonujemy swap mutation.
          - z prawdopodobieństwem pm_transposition wykonujemy transposition mutation.
        Zwraca zmutowaną populację (operacje in-place na kopiach).
        """
        mutated = []
        for ind in population:
            ind_copy = self._clone_individual(ind)
            tasks_seq, machines_chrom = ind_copy
            for pos in range(len(tasks_seq)):
                if self._check_swap_mutation():
                    self._swap_mutation(tasks_seq, machines_chrom, pos)
                if self._check_transposition_mutation():
                    self._transposition_mutation(tasks_seq, machines_chrom, pos)
            mutated.append(ind_copy)
        return mutated

    def _check_swap_mutation(self) -> bool:
        """
        Czy wykonać mutację swap (porównanie z pm_swap).
        """
        return np.random.uniform(0.0, 1.0) <= self.pm_swap

    def _check_transposition_mutation(self) -> bool:
        """
        Czy wykonać mutację transposition (porównanie z pm_transposition).
        """
        return np.random.uniform(0.0, 1.0) <= self.pm_transposition

    def _swap_mutation(self, tasks_seq: List[int], machines_chrom: List[int], i: int):
        """
        Swap mutation:
          - Losuje drugą pozycję j != i.
          - Sprawdza czy po zamianie zadania nadal mogą wykonać się na maszynach,
            do których należą (wg bieżącego podziału machines_chrom).
        """
        if len(tasks_seq) < 2:
            return
        size = len(tasks_seq) - 1
        j = np.random.randint(0, size + 1)
        while j == i:
            j = np.random.randint(0, size + 1)
        # Określ do jakich maszyn należą pozycje i, j
        machine_i = self._machine_for_task_position(machines_chrom, i)
        machine_j = self._machine_for_task_position(machines_chrom, j)
        task_i = tasks_seq[i]
        task_j = tasks_seq[j]
        # Sprawdź wykonalność po zamianie
        if (machine_j in self.tasks_to_machines[task_i]) and (machine_i in self.tasks_to_machines[task_j]):
            tasks_seq[i], tasks_seq[j] = tasks_seq[j], tasks_seq[i]

    def _transposition_mutation(self, tasks_seq: List[int], machines_chrom: List[int], i: int):
        """
        Transposition mutation:
          - Losuje drugą pozycję j != i.
          - Przesuwa zadanie z pozycji i w nowe miejsce j (rotacja segmentu),
            a machines_chrom aktualizuje liczbę zadań maszyn (zmniejsza dla źródłowej,
            zwiększa dla docelowej), jeśli przenoszone zadanie jest dozwolone na maszynie docelowej.
        """
        if len(tasks_seq) < 2:
            return
        size = len(tasks_seq) - 1
        j = np.random.randint(0, size + 1)
        while j == i:
            j = np.random.randint(0, size + 1)

        source_machine = self._machine_for_task_position(machines_chrom, i)
        dest_machine = self._machine_for_task_position(machines_chrom, j)
        if source_machine == dest_machine:
            return  # bez zmiany przypisania

        task_id = tasks_seq[i]
        if dest_machine not in self.tasks_to_machines[task_id]:
            return  # niedozwolone

        if machines_chrom[source_machine] <= 1:
            return  # nie można pozbawić maszyny jedynego zadania

        # Aktualizacja machines_chrom
        machines_chrom[source_machine] -= 1
        machines_chrom[dest_machine] += 1

        # Fizyczne przesunięcie zadania w sekwencji
        transposed = tasks_seq[i]
        if i < j:
            for pos in range(i, j):
                tasks_seq[pos] = tasks_seq[pos + 1]
            tasks_seq[j] = transposed
        else:
            for pos in range(i, j, -1):
                tasks_seq[pos] = tasks_seq[pos - 1]
            tasks_seq[j] = transposed

    # ------------------------------------------------------------
    # Funkcje pomocnicze
    # ------------------------------------------------------------
    @staticmethod
    def _clone_individual(ind: Tuple[List[int], List[int]]) -> Tuple[List[int], List[int]]:
        """
        Głęboka kopia osobnika (listy).
        """
        return ind[0][:], ind[1][:]

    @staticmethod
    def _machine_for_task_position(machines_chrom: List[int], pos: int) -> int:
        """
        Dla pozycji pos w tasks_sequence zwraca ID maszyny,
        na którą ta pozycja przypada według machines_chromosome.
        """
        cumulative = 0
        for m_id, count in enumerate(machines_chrom):
            cumulative += count
            if cumulative > pos:
                return m_id
        return len(machines_chrom) - 1  # fallback (nie powinno się zdarzyć)


# Pozostawiony punkt wejścia tylko do testów indywidualnych tej klasy.
if __name__ == "__main__":
    alg = PittPermMethod(iterations=100, population_size=10, pm_swap=0.01, pm_transposition=0.01, show_chart=True)
    alg.run()