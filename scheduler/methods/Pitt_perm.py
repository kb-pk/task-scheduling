from __future__ import annotations
import math
import random
from typing import List, Dict

import numpy as np
from sklearn.utils import shuffle

from lang.Lang import T
from scheduler.MethodCache import MethodCache
from scheduler.Logger import Logger
from scheduler.ProgramState import ProgramState
from scheduler.Registry import MethodRegistrator
from scheduler.Parameters import ParamDef, ParamValueTypes, PittPermCrossoverValidator, InfluenceGroupInstantiator
from scheduler.methods.Pitt import BasePittMethod

@MethodRegistrator.register_class
class PittPermMethod(BasePittMethod):
    def __init__(self, state: ProgramState, logger: Logger, t: T, cache: MethodCache):
        super().__init__(state, logger, t, cache)

        params = [
            * InfluenceGroupInstantiator.set([
                ParamDef(self.T.t("PMX"), ParamValueTypes.BOOLEAN, True,
                         self.T.t("Partial mapped crossover")),
                ParamDef(self.T.t("CX"), ParamValueTypes.BOOLEAN, False,
                         self.T.t("Cycle crossover")),
                ParamDef(self.T.t("OX"), ParamValueTypes.BOOLEAN, False,
                         self.T.t("Ordered crossover")),
            ], PittPermCrossoverValidator),
            ParamDef(self.T.t("Mutation probability (pms)"), ParamValueTypes.FLOAT, 0.01,
                     self.T.t("Gene swap mutation probability"),
                     min_value=0.0, max_value=1.0),
            ParamDef(self.T.t("Mutation probability (pmt)"), ParamValueTypes.FLOAT, 0.01,
                     self.T.t("Gene transposition mutation probability"),
                     min_value=0.0, max_value=1.0),
        ]

        self.PARAM_DEFS += params

        # shorthand
        self._pmx = params[0]
        self._cx = params[1]
        self._ox = params[2]
        self._pms = params[3]
        self._pmt = params[4]

        self.name = self.T.t("Pitt (permutation-based)")
        self.description = self.T.td({
            self.state.lang.State.pl_PL: """
            Algorytm oparty o podejście Pitt, reprezentacja permutowana.
            Osobnik - reprezentacja konkretnego harmonogramu zadań dla wszystkich maszyn. Składa się z 2 chromosomów.
            Chromosom 1 - lista zadań w konkretnej kolejności. Składa się z N (liczba zadań) genów.
            Chromosom 2 - liczba zadań z chromosomu 1 przypisanych do maszyn. Składa się z M (liczba maszyn) genów.
            Gen (chromosom 1) - pojedyncze zadanie z listy zadań.
            Gen (chromosom 2) - liczba zadań przypisanych do konkretnej maszyny. Indeks genu w chromosomie definiuje maszynę (machine_id).
            Selekcja - brak selekcji pomiędzy epokami.
            Krzyżowanie - PMX (partial mapped crossover), CX (cycle crossover), OX (ordered crossover). Każdy osobnik bierze udział.
            Mutacja - S (swap mutation - zamiana zadań pomiędzy maszynami) i T (transposition mutation - przeniesienie zadania jednej maszyny do harmonogramu drugiej).
            """,

            self.state.lang.State.en_GB: """
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
        })

    def build_schedule_map(self, solution):
        tasks_sequence, machines_chromosome = solution
        schedule_map = {m: [] for m in range(len(machines_chromosome))}
        offset = 0
        for m_id, count in enumerate(machines_chromosome):
            slice_tasks = tasks_sequence[offset:offset + count]
            schedule_map[m_id].extend(slice_tasks)
            offset += count
        return schedule_map

    def __generate_machines_chromosome(self) -> List[int]:
        n_tasks = len(self.tasks)
        n_machines = len(self.machines)
        tasks_per_machine = math.floor(n_tasks / n_machines)
        chrom = [tasks_per_machine] * n_machines
        remainder = n_tasks - tasks_per_machine * n_machines
        for i in range(remainder):
            chrom[i] += 1
        return chrom

    def __assign_tasks_to_machines(self, machines_chromosome: List[int]) -> Dict[int, List[int]]:
        machines_to_tasks = {m_id: [] for m_id in self.machines.index.values}
        # Zadania, które mają najmniej opcji – najpierw
        sorted_tasks = sorted(self._tasks_possible_machines.items(), key=lambda kv: len(kv[1]))
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

    def _generate_individual(self):
        machines_chromosome = self.__generate_machines_chromosome()
        machines_to_tasks = self.__assign_tasks_to_machines(machines_chromosome)
        ret_tasks = []
        for tasks_list in machines_to_tasks.values():
            ret_tasks += tasks_list

        return [ret_tasks, machines_chromosome]

    def _crossover_population(self):
        if self._pmx.get_value():
            crossover = self.__partial_mapped_crossover
        elif self._cx.get_value():
            crossover = self.__cycle_crossover
        elif self._ox.get_value():
            crossover = self.__ordered_crossover
        else:
            raise NotImplementedError("Crossover method not implemented.")

        shuffled = shuffle(self.population)
        new_pop = []

        for i in range(0, self._pop_size.get_value() - 1):
            chr_1_dad, chr_1_mom = shuffled[i][0], shuffled[i + 1][0]
            chr_1_new_1, chr_1_new_2 = crossover(chr_1_dad, chr_1_mom)

            new_pop.append([chr_1_new_1, shuffled[i][1]])
            new_pop.append([chr_1_new_2, shuffled[i + 1][1]])

        self.population = new_pop

    def __partial_mapped_crossover(self, mom, dad):
        size = len(mom)
        start, end = sorted([random.randrange(size) for _ in range(2)])

        daughter = [None] * size
        son = [None] * size

        daughter[start:end] = dad[start:end]
        son[start:end] = mom[start:end]

        map1 = {dad[i]: mom[i] for i in range(start, end)}
        map2 = {mom[i]: dad[i] for i in range(start, end)}

        def finish_map(parent, child, mapping):
            for i in range(size):
                if child[i] is None:
                    gene = parent[i]
                    while gene in mapping:
                        gene = mapping[gene]
                    child[i] = gene

        finish_map(mom, daughter, map1)
        finish_map(dad, son, map2)

        return daughter, son

    def __cycle_crossover(self, mom, dad):
        def __create_child(primary_parent, other_parent):
            cycle = []

            inx = 0
            cycle.append(inx)

            while True:
                tmp = other_parent[inx]
                inx = primary_parent.index(tmp)
                cycle.append(inx)

                if inx == 0:
                    break

            child = [i for i in range(len(primary_parent))]

            for i, _ in enumerate(child):
                if i in cycle:
                    child[i] = primary_parent[i]
                else:
                    child[i] = other_parent[i]

            return child

        daughter = __create_child(dad, mom)
        son = __create_child(mom, dad)

        return daughter, son

    def __ordered_crossover(self, mom, dad):
        # długość osobnika (ilość zadań)
        size = len(mom)

        # wybierz losową pozycje początku / końca krzyżowania
        daughter, son = [-1] * size, [-1] * size
        start, end = sorted([random.randrange(size) for _ in range(2)])

        # replikuj sekwencję matki dla córki i ojca dla syna
        daughter_inherited = []
        son_inherited = []
        for i in range(start, end + 1):
            daughter[i] = mom[i]
            son[i] = dad[i]
            daughter_inherited.append(mom[i])
            son_inherited.append(dad[i])

        # wypełnij pozostałe pozycje pozostałymi danymi z rodziców
        current_dad_position, current_mom_position = 0, 0

        fixed_pos = list(range(start, end + 1))
        i = 0
        while i < size:
            # pomiń już skrzyzowany fragment
            if i in fixed_pos:
                i += 1
                continue

            # wypełniaj pozostałe fragmenty
            if daughter[i] == -1:  # wymaga wypelnienia
                dad_trait = dad[current_dad_position]
                while dad_trait in daughter_inherited:
                    current_dad_position += 1
                    dad_trait = dad[current_dad_position]
                daughter[i] = dad_trait
                daughter_inherited.append(dad_trait)

            if son[i] == -1:  # wymaga wypelnienia
                mom_trait = mom[current_mom_position]
                while mom_trait in son_inherited:
                    current_mom_position += 1
                    mom_trait = mom[current_mom_position]
                son[i] = mom_trait
                son_inherited.append(mom_trait)
            i += 1

        return daughter, son

    def _mutate_population(self):
        for individual in self.population:
            for index, _ in enumerate(individual[0]):
                if self.__check_swap_mutation():
                    self.__swap_mutation(individual, index)
                if self.__check_transposition_mutation():
                    self.__transposition_mutation(individual, index)

    def __check_swap_mutation(self) -> bool:
        """
        Czy wykonać mutację swap (porównanie z pm_swap).
        """
        return np.random.uniform(0.0, 1.0) <= self._pms.get_value()

    def __check_transposition_mutation(self) -> bool:
        """
        Czy wykonać mutację transposition (porównanie z pm_transposition).
        """
        return np.random.uniform(0.0, 1.0) <= self._pmt.get_value()

    def __swap_mutation(self, individual, gene_index):
        tasks_i = individual[0]
        t = tasks_i[gene_index]
        m_id = self.__get_machine_number_for_task(individual, t)

        # generate j
        # if m_id can run j and new_m_id can run j then ok
        while (j := np.random.randint(0, len(tasks_i))) == gene_index or \
            (new_m_id := self.__get_machine_number_for_task(individual, j)) != m_id or \
            new_m_id not in self._tasks_possible_machines[gene_index]:
            continue

        individual[0][gene_index], individual[0][j] = individual[0][j], individual[0][gene_index]

    def __transposition_mutation(self, individual, gene_index):
        tasks_i = individual[0]
        t = tasks_i[gene_index]
        m_id = self.__get_machine_number_for_task(individual, gene_index)

        # wont perform tm on a machine with 1 task
        if individual[1][m_id] == 1:
            return

        # j here is only used to randomly select a new machine
        while (j := np.random.randint(0, len(tasks_i))) == gene_index or \
            (new_m_id := self.__get_machine_number_for_task(individual, j)) != m_id or \
            new_m_id not in self._tasks_possible_machines[gene_index]:
            continue

        individual[1][m_id] -= 1
        individual[1][new_m_id] += 1

        if gene_index > j:
            tasks_i.pop(gene_index)
            tasks_i.insert(j, t)
        else:
            tasks_i.insert(j, t)
            tasks_i.pop(gene_index)

    def __get_machine_number_for_task(self, individual, task_position):
        counter = 0
        position_number = 0
        for machine in individual[1]:
            position_number += machine
            if position_number >= task_position + 1:
                return counter
            else:
                counter = counter + 1
        return None