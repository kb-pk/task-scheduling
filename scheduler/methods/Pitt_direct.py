from __future__ import annotations
import random
from typing import List, Tuple, Dict
import numpy as np

import scheduler.Common as Common
from scheduler.MethodRegistry import MethodRegistrator
from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod
from scheduler.Parameters import ParamDef2, ParamValueTypes, PopulationValidator

@MethodRegistrator.register_method
class PittDirectMethod(BaseMethod):
    def __init__(self, state: ProgramState):
        super().__init__(state)

        self._tasks_possible_machines: Dict[int, List[int]] = self._map_possible_machines_to_tasks()
        self.population: List[List[int]] = []
        self.best_individual: List[int] | None = None
        self.best_score: float | None = None

        self.PARAM_DEFS = [
            ParamDef2(self.T.t("Iterations"), ParamValueTypes.INT, 100, self.T.t("Number of iterations (epochs)"),
                      min_value=1),
            ParamDef2(self.T.t("Population size"), ParamValueTypes.INT, 10, self.T.t("Population size (must be even)"),
                      min_value=2,
                      validator=PopulationValidator()),
            ParamDef2(self.T.t("Crossover points"), ParamValueTypes.INT, 1, self.T.t("Number of crossover points"),
                      min_value=1, max_value=len(self.tasks)),
            ParamDef2(self.T.t("Mutation probability"), ParamValueTypes.FLOAT, 0.01, self.T.t("Gene mutation probability"),
                      min_value=0.0, max_value=1.0),
        ]

        # defaults (for easier access - therefore hacky)
        self._iterations = self.PARAM_DEFS[0].get_value()
        self._pop_size = self.PARAM_DEFS[1].get_value()
        self._crossover_points = self.PARAM_DEFS[2].get_value()
        self._mutation_probability = self.PARAM_DEFS[3].get_value()

        self.name = self.T.t("Pitt (direct)")
        self.description = self.T.td({
            self.state.lang.State.pl_PL : """
            Algorytm oparty o podejście Pitt, reprezentacja bezpośrednia.

            Osobnik - reprezentacja konkretnego harmonogramu zadań dla wszystkich maszyn. Składa się z 1 chromosomu.
            Chromosom - harmonogram zadań dla wszystkich maszyn. Składa się z N (liczba zadań) genów.
            Gen - reprezentacja maszyny (machine_id). Indeks genu w chromosomie to numer zadania przypisanego do maszyny. Geny mogą powtarzać się w chromosomie.

            Selekcja - brak selekcji pomiędzy epokami.

            Krzyżowanie - n-punktowe, każdy osobnik bierze udział.

            Mutacja - losowanie nowej wartości genu (machine_id) wewnątrz chromosomu.
            """,
            self.state.lang.State.en_GB: """
            Algorithm based on the Pitt approach, direct representation.

            Entity - a representation of a particular schedule of tasks for all machines. Made up of 1 chromosome.
            Chromosome - a particular schedule of tasks for all machines. Made up of N (task number) genes.
            Gene - a representation of a machine (machine_id). The index of a gene in a chromosome is a number of a task that's assigned to this machine. Genes can repeat in the chromosome.

            Selection - no selection between epochs.

            Crossover - n-point, every entity takes part.

            Mutation - a gene's value (machine_id) is replaced with a new, randomly generated one.
            """
        })

    def initialize(self):
        self.population = [self._generate_individual() for _ in range(self._pop_size)]
        self._evaluate_population_initial()

    def optimize(self):
        for epoch in range(self._iterations):
            self._crossover_population()
            self._mutate_population()
            self._evaluate_population_update_best(epoch)

    def get_best_solution(self):
        """
        Zwraca najlepszy znaleziony osobnik (lista machine_id per task).
        """
        return self.best_individual

    def build_schedule_map(self, solution: List[int]):
        schedule_map = {m_id: [] for m_id in self.machines.index.values}
        for task_id, machine_id in enumerate(solution):
            schedule_map[machine_id].append(task_id)
        return schedule_map

    def _map_possible_machines_to_tasks(self) -> Dict[int, List[int]]:
        """
        Mapuje zadania i maszyny, które dane zadanie mogą wykonać (na podstawie features).
        :return: Słownik {task_id: [machine_id, machine_id, ...], ...}
        """
        possible_machines_for_tasks = {task_id: [
            machine_id for machine_id in self.machines.index.values
            if Common.can_execute_task_on_machine(self.machines.iloc[machine_id], self.tasks.iloc[task_id], self.features)
        ] for task_id in self.tasks.index.values}

        return possible_machines_for_tasks

    def _generate_individual(self) -> List[int]:
        individual = []

        for task_id, possible_machines in self._tasks_possible_machines.items():
            individual.append(random.choice(possible_machines))

        self._ensure_all_machines_present(individual)

        return individual

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

    def _evaluate_population(self):
        for individual in self.population:
            decode = self.build_schedule_map(individual)
            fitness = self._fitness_function(decode)

            if self.best_individual is None or fitness < self.best_score:
                self.best_individual = individual.copy()
                self.best_score = fitness

    def _evaluate_population_initial(self):
        """
        Ocena pierwszej populacji i ustawienie pól best_*.
        """
        self._evaluate_population()

        self.logger.initial_solution(self.best_score)

    def _evaluate_population_update_best(self, epoch):
        """
        Ocena po operatorach. Aktualizuje best_* jeśli znajdzie lepszy osobnik.
        """
        last_best = self.best_score
        self._evaluate_population()
        has_improved = last_best != self.best_score
        if has_improved:
            self.logger.better_solution_found(self.best_score, epoch)

    def _crossover_population(self):
        """
        N‑punktowe krzyżowanie par osobników po losowym przetasowaniu.
        Walidacja: każdy potomek musi zawierać wszystkie machine_id (powtarzamy losowanie segmentów aż spełni warunek).
        """
        shuffled = self.population
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

        self.population = new_pop

    def _crossover_pair(self, p1: List[int], p2: List[int]) -> Tuple[List[int], List[int]]:
        """
        Krzyżowanie dwóch rodziców:
          - Losuje self.crossover_points unikalnych punktów (w [0, n-2]).
          - Naprzemiennie dokleja segmenty z rodziców.
          - Waliduje obecność wszystkich maszyn (powtarza jeśli niepoprawne).
        """

        n = len(p1)
        while True:
            points = sorted(random.sample(range(0, n - 1), self._crossover_points))
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

    def _mutate_population(self):
        """
        Mutacja populacji: dla każdego genu wywołanie mutacji z prawdopodobieństwem pm
        (jeśli nie pozbawia maszyny wszystkich zadań).
        """
        for ind in self.population:
            self._mutate_individual(ind)

    def _mutate_individual(self, individual: List[int]):
        counts = {m: 0 for m in self.machines.index.values}
        for m in individual:
            counts[m] += 1

        for idx, current_m in enumerate(individual):
            # only mutate if the machine has >1 task assigned
            if np.random.uniform(0.0, 1.0) <= self._mutation_probability and counts[current_m] > 1:
                new_m = self._mutate_gene(current_m)
                individual[idx] = new_m
                counts[current_m] -= 1
                counts[new_m] = counts.get(new_m, 0) + 1

    def _mutate_gene(self, current_machine: int) -> int:
        n_machines = len(self.machines)
        while True:
            val = random.randint(0, n_machines - 1)
            if val != current_machine:
                return val
