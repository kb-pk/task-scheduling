from __future__ import annotations
import random
from typing import List, Tuple
import numpy as np

from lang.Lang import T
from scheduler.Logger import Logger
from scheduler.MethodCache import MethodCache
from scheduler.ProgramState import ProgramState
from scheduler.Registry import MethodRegistrator
from scheduler.Parameters import ParamDef, ParamValueTypes
from scheduler.methods.Pitt import BasePittMethod


@MethodRegistrator.register_class
class PittDirectMethod(BasePittMethod):
    def __init__(self, state: ProgramState, logger: Logger, t: T, cache: MethodCache):
        super().__init__(state, logger, t, cache)

        params =  [
            ParamDef(self.T.t("Crossover points"), ParamValueTypes.INT, 1, self.T.t("Number of crossover points"),
                     min_value=1, max_value=len(self.tasks)),
            ParamDef(self.T.t("Mutation probability"), ParamValueTypes.FLOAT, 0.01, self.T.t("Gene mutation probability"),
                     min_value=0.0, max_value=1.0),
        ]

        self.PARAM_DEFS += params

        # defaults (for easier access - therefore hacky)
        self._crossover_points = params[0].get_value()
        self._mutation_probability = params[1].get_value()

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


    def build_schedule_map(self, solution: List[int]):
        schedule_map = {m_id: [] for m_id in self.machines.index.values}
        for task_id, machine_id in enumerate(solution):
            schedule_map[machine_id].append(task_id)

        return schedule_map

    def _generate_individual(self) -> List[int]:
        individual = []

        for task_id, possible_machines in self._tasks_possible_machines.items():
            individual.append(random.choice(possible_machines))

        self.__ensure_all_machines_present(individual)

        return individual

    def __ensure_all_machines_present(self, individual: List[int]):
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

    def _crossover_population(self):
        """
        N‑punktowe krzyżowanie par osobników po losowym przetasowaniu.
        Walidacja: każdy potomek musi zawierać wszystkie machine_id (powtarzamy losowanie segmentów aż spełni warunek).
        """
        shuffled = self.population
        random.shuffle(shuffled)
        new_pop: List[List[int]] = []

        for i in range(0, self._pop_size, 2):
            parents = shuffled[i:i + 2]
            a, b = self.__crossover_pair(parents[0], parents[1])
            new_pop.append(a)
            new_pop.append(b)

        self.population = new_pop

    def __crossover_pair(self, p1: List[int], p2: List[int]) -> Tuple[List[int], List[int]]:
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

            if self.__is_individual_valid(child1) and self.__is_individual_valid(child2):
                return child1, child2
            # w przeciwnym razie spróbuj ponownie

    def __is_individual_valid(self, individual: List[int]) -> bool:
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
            self.__mutate_individual(ind)

    def __mutate_individual(self, individual: List[int]):
        counts = {m: 0 for m in self.machines.index.values}
        for m in individual:
            counts[m] += 1

        for idx, current_m in enumerate(individual):
            # only mutate if the machine has >1 task assigned
            if np.random.uniform(0.0, 1.0) <= self._mutation_probability and counts[current_m] > 1:
                new_m = self.__mutate_gene(current_m)
                individual[idx] = new_m
                counts[current_m] -= 1
                counts[new_m] = counts.get(new_m, 0) + 1

    def __mutate_gene(self, current_machine: int) -> int:
        n_machines = len(self.machines)
        while True:
            val = random.randint(0, n_machines - 1)
            if val != current_machine:
                return val
