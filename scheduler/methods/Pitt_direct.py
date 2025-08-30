from __future__ import annotations
import random
from typing import List, Tuple, Dict

import numpy as np

import scheduler.Common as Common
from .BaseMethod import BaseMethod, Lang


class PittDirectMethod(BaseMethod):
    """
    Algorytm GA (Pitt – reprezentacja bezpośrednia) w schemacie BaseMethod.

    Reprezentacja osobnika:
      - Lista length = liczba zadań.
      - Pozycja i = ID zadania i.
      - Wartość na pozycji i = ID maszyny wykonującej zadanie i.

    Ograniczenia:
      - Każde zadanie przypisane do jednej maszyny spełniającej wymagania bezpieczeństwa.
      - Dodatkowo (walidacja): każdy osobnik musi zawierać przynajmniej jedną instancję
        każdego machine_id (żadna maszyna nie może pozostać bez zadania).

    Operatory:
      - Crossover: n‑punktowy (NUMBER_OF_CROSSOVER_POINTS), wymiana segmentów między dwiema listami.
      - Mutacja: z prawdopodobieństwem pm zmiana genu na inny machine_id (jeśli bieżący machine_id
        występuje w chromosomie co najmniej dwa razy, aby nie pozbawić maszyny wszystkich zadań).
        (Zachowane zachowanie oryginału – bez dodatkowej kontroli zgodności z wymaganiami zadania.)

    Ocena:
      - Makespan = max czas obciążenia maszyn.
      - Energia = suma (busy*P_busy + idle*P_idle).
      - W zależności od Common.scheduling_mode metryka główna to makespan albo energia.

    Wynik:
      - build_schedule_map() tworzy mapę {machine_id: [task_ids]} w kolejności indeksów zadań.
    """
    def __init__(self,
                 iterations: int = 100,
                 population_size: int = 10,
                 crossover_points: int = 1,
                 mutation_probability: float = 0.01,
                 show_chart: bool = True):
        """
        :param iterations: liczba epok
        :param population_size: liczebność populacji (wymagana parzysta)
        :param crossover_points: liczba punktów krzyżowania (>=1)
        :param mutation_probability: prawdopodobieństwo mutacji genu
        :param show_chart: rysowanie wykresu po zakończeniu
        """
        super().__init__(show_chart=show_chart)
        self.iterations = iterations
        self.population_size = population_size
        self.crossover_points = crossover_points
        self.pm = mutation_probability

        self._tasks_possible_machines: Dict[int, List[int]] = {}
        self.population: List[List[int]] = []
        self.best_individual: List[int] | None = None
        self.best_score: float | None = None
        self.other_score: float | None = None

    # ---------- Identyfikacja / opis ----------

    def get_method_name(self) -> str:
        return "pitt_direct"

    # ---------- Cykl życia ----------

    def initialize(self):
        """
        Przygotowanie:
          - Budowa mapy możliwych maszyn dla zadań.
          - Generacja populacji startowej.
          - Ocena i zapamiętanie najlepszego.
        """
        if self.population_size % 2 != 0:
            raise ValueError("Population size should be even for pairing in crossover.")
        if self.crossover_points < 1:
            raise ValueError("crossover_points must be >= 1")

        self._tasks_possible_machines = self._map_possible_machines_to_tasks()
        self.population = [self._generate_individual() for _ in range(self.population_size)]
        self._evaluate_population_initial()

    def optimize(self):
        """
        Pętla epok:
          - Krzyżowanie populacji
          - Mutacja populacji
          - Ocena oraz aktualizacja najlepszego osobnika
        """
        for epoch in range(self.iterations):
            self.population = self._crossover_population(self.population)
            self.population = self._mutate_population(self.population)
            improved = self._evaluate_population_update_best()
            if improved:
                if Common.scheduling_mode == Common.MAKESPAN_MODE:
                    print(f"[{epoch}] New best makespan: {self.best_score:.4f} energy: {self.other_score:.4f}")
                else:
                    print(f"[{epoch}] New best energy: {self.best_score:.4f} makespan: {self.other_score:.4f}")

    def get_best_solution(self):
        """
        Zwraca najlepszy znaleziony osobnik (lista machine_id per task).
        """
        return self.best_individual

    def build_schedule_map(self, solution: List[int]):
        """
        Konwersja listy przypisań (task -> machine_id) na mapę {machine_id: [task_id,...]}.
        Zachowuje rosnący porządek ID zadań.
        """
        schedule_map = {m_id: [] for m_id in self.machines.index.values}
        for task_id, machine_id in enumerate(solution):
            schedule_map[machine_id].append(task_id)
        return schedule_map

    def after_run(self, schedule_map, makespan, total_energy):
        """
        Dodatkowy log wyników do pliku tekstowego.
        """
        if Common.scheduling_mode == Common.MAKESPAN_MODE:
            primary = makespan
            secondary = total_energy
        else:
            primary = total_energy
            secondary = makespan
        with open("results/result_pitt_direct", "a") as f:
            f.write(f"{primary},{secondary}\n")

    # ---------- Generacja / ocena ----------

    def _map_possible_machines_to_tasks(self) -> Dict[int, List[int]]:
        """
        Dla każdego zadania listuje maszyny spełniające wymagania bezpieczeństwa.
        {task_id: [machine_id,...]}
        """
        mapping = {}
        for task_id in self.tasks.index.values:
            allowed = [
                machine_id for machine_id in self.machines.index.values
                if Common.can_execute_task_on_machine(
                    self.machines.iloc[machine_id],
                    self.tasks.iloc[task_id],
                    self.features
                )
            ]
            if not allowed:
                raise ValueError(f"No feasible machine for task {task_id}")
            mapping[task_id] = allowed
        return mapping

    def _generate_individual(self) -> List[int]:
        """
        Losowe przypisanie każdego zadania do jednej z dozwolonych maszyn.
        Gwarantuje (heurystycznie), że każda maszyna pojawi się co najmniej raz:
          - najpierw jedno zadanie per maszyna (jeśli możliwe),
          - potem reszta losowo.
        """
        n_tasks = len(self.tasks)
        n_machines = len(self.machines)
        assignment = [-1] * n_tasks

        # Faza 1: spróbuj zapewnić każdej maszynie jedno zadanie (jeśli liczba zadań >= maszyn)
        unassigned_tasks = list(range(n_tasks))
        random.shuffle(unassigned_tasks)
        used_tasks = set()
        for m_id in range(n_machines):
            # znajdź pierwsze zadanie, które może trafić na m_id
            found = False
            for t in unassigned_tasks:
                if t in used_tasks:
                    continue
                if m_id in self._tasks_possible_machines[t]:
                    assignment[t] = m_id
                    used_tasks.add(t)
                    found = True
                    break
            if not found:
                # fallback: jeśli nie można - pozostaw do losowego przydziału
                pass

        # Faza 2: pozostałe zadania
        for t in range(n_tasks):
            if assignment[t] == -1:
                assignment[t] = random.choice(self._tasks_possible_machines[t])

        # Walidacja – jeśli któraś maszyna nie otrzymała zadania, naprawa
        self._ensure_all_machines_present(assignment)
        return assignment

    def _ensure_all_machines_present(self, individual: List[int]):
        """
        Gwarantuje, że każdy machine_id występuje przynajmniej raz.
        Jeśli brakuje, przenosi losowe zadanie z maszyny posiadającej >1 zadanie.
        """
        counts = {m: 0 for m in self.machines.index.values}
        for m in individual:
            counts[m] += 1
        missing = [m for m, c in counts.items() if c == 0]
        if not missing:
            return
        # dla każdej brakującej, zabierz jedno zadanie z maszyny o największej liczbie zadań
        for m_missing in missing:
            donor = max(counts, key=lambda k: counts[k])
            if counts[donor] <= 1:
                continue
            # znajdź indeks zadania przypisanego do donor
            idx = next(i for i, v in enumerate(individual) if v == donor)
            individual[idx] = m_missing
            counts[donor] -= 1
            counts[m_missing] += 1

    def _evaluate_individual(self, indiv: List[int]) -> Tuple[float, float]:
        """
        Oblicza (primary_metric, secondary_metric):
          - makespan
          - energy
        Wybór primary zależy od scheduling_mode.
        """
        n_machines = len(self.machines)
        machine_times = [0.0] * n_machines
        for task_id, machine_id in enumerate(indiv):
            machine_times[machine_id] += self.etc[task_id][machine_id]
        makespan = max(machine_times)
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
        Ocena pierwszej populacji i ustawienie pól best_*.
        """
        for ind in self.population:
            main_val, other_val = self._evaluate_individual(ind)
            if self.best_individual is None or main_val < self.best_score:
                self.best_individual = ind[:]
                self.best_score = main_val
                self.other_score = other_val
        if Common.scheduling_mode == Common.MAKESPAN_MODE:
            print(f"Initial makespan: {self.best_score:.4f} energy: {self.other_score:.4f}")
        else:
            print(f"Initial energy: {self.best_score:.4f} makespan: {self.other_score:.4f}")

    def _evaluate_population_update_best(self) -> bool:
        """
        Ocena po operatorach. Aktualizuje best_* jeśli znajdzie lepszy osobnik.
        :return: True jeśli poprawiono wynik.
        """
        improved = False
        for ind in self.population:
            main_val, other_val = self._evaluate_individual(ind)
            if main_val < self.best_score:
                self.best_individual = ind[:]
                self.best_score = main_val
                self.other_score = other_val
                improved = True
        return improved

    # ---------- Operatory genetyczne ----------

    def _crossover_population(self, population: List[List[int]]) -> List[List[int]]:
        """
        N‑punktowe krzyżowanie par osobników po losowym przetasowaniu.
        Walidacja: każdy potomek musi zawierać wszystkie machine_id (powtarzamy losowanie segmentów aż spełni warunek).
        """
        shuffled = population[:]
        random.shuffle(shuffled)
        new_pop: List[List[int]] = []
        for i in range(0, len(shuffled), 2):
            parents = shuffled[i:i + 2]
            if len(parents) < 2:
                new_pop.append(parents[0][:])
                break
            a, b = self._crossover_pair(parents[0], parents[1])
            new_pop.append(a)
            new_pop.append(b)
        return new_pop

    def _crossover_pair(self, p1: List[int], p2: List[int]) -> Tuple[List[int], List[int]]:
        """
        Krzyżowanie dwóch rodziców:
          - Losuje self.crossover_points unikalnych punktów (w [0, n-2]).
          - Naprzemiennie dokleja segmenty z rodziców.
          - Waliduje obecność wszystkich maszyn (powtarza jeśli niepoprawne).
        """
        n = len(p1)
        while True:
            points = sorted(random.sample(range(0, n - 1), self.crossover_points))
            child1, child2 = [], []
            prev = 0
            for idx, cp in enumerate(points):
                if idx % 2 == 0:
                    child1.extend(p1[prev:cp])
                    child2.extend(p2[prev:cp])
                else:
                    child1.extend(p2[prev:cp])
                    child2.extend(p1[prev:cp])
                prev = cp
            # ostatni segment
            if len(points) % 2 == 0:
                child1.extend(p1[prev:])
                child2.extend(p2[prev:])
            else:
                child1.extend(p2[prev:])
                child2.extend(p1[prev:])

            if self._is_individual_valid(child1) and self._is_individual_valid(child2):
                return child1, child2
            # w przeciwnym razie spróbuj ponownie

    def _is_individual_valid(self, individual: List[int]) -> bool:
        """
        Sprawdza czy osobnik zawiera przynajmniej jedno zadanie dla każdej maszyny.
        """
        machines_set = set(self.machines.index.values)
        return machines_set.issubset(set(individual))

    def _mutate_population(self, population: List[List[int]]) -> List[List[int]]:
        """
        Mutacja populacji: dla każdego genu wywołanie mutacji z prawdopodobieństwem pm
        (jeśli nie pozbawia maszyny wszystkich zadań).
        """
        mutated = []
        for ind in population:
            mutated.append(self._mutate_individual(ind))
        return mutated

    def _mutate_individual(self, individual: List[int]) -> List[int]:
        """
        Mutacja osobnika – tworzy nową listę (kopię z ewentualnymi zmianami).
        """
        result = individual[:]
        counts = {m: 0 for m in self.machines.index.values}
        for m in result:
            counts[m] += 1
        for idx, current_m in enumerate(result):
            if np.random.uniform(0.0, 1.0) <= self.pm:
                # Możliwość mutacji tylko jeśli maszyna ma >1 zadanie
                if counts[current_m] > 1:
                    new_m = self._mutate_gene(current_m)
                    result[idx] = new_m
                    counts[current_m] -= 1
                    counts[new_m] = counts.get(new_m, 0) + 1
        # Naprawa (teoretycznie zbędna, ale dla pewności):
        self._ensure_all_machines_present(result)
        return result

    def _mutate_gene(self, current_machine: int) -> int:
        """
        Losuje nowy machine_id różny od current_machine.
        (Zachowuje zachowanie oryginalne: brak weryfikacji cech zadania.)
        """
        n_machines = len(self.machines)
        while True:
            val = random.randint(0, n_machines - 1)
            if val != current_machine:
                return val


# Punkt wejścia testowego
if __name__ == "__main__":
    alg = PittDirectMethod(iterations=100,
                           population_size=10,
                           crossover_points=1,
                           mutation_probability=0.01,
                           show_chart=True)
    alg.run()