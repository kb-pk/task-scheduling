from random import randint
import numpy as np

from lang.Lang import T
from scheduler.Logger import Logger
from scheduler.MethodCache import MethodCache
from scheduler.ProgramState import ProgramState
from scheduler.Registry import MethodRegistrator
from scheduler.Parameters import ParamDef, ParamValueTypes
from scheduler.methods.EvolAlgoBaseMethod import EvolAlgoBaseMethod


@MethodRegistrator.register_class
class MichiganMethod(EvolAlgoBaseMethod):
    def __init__(self, state: ProgramState, logger: Logger, t: T, cache: MethodCache):
        super().__init__(state, logger, t, cache)

        params = [
            ParamDef(self.T.t("Mutation probability"), ParamValueTypes.FLOAT, 0.01,
                     self.T.t("Gene mutation probability"),
                     min_value=0.0, max_value=1.0),
        ]

        self.PARAM_DEFS += params

        self._pop_size.set_value(len(self.machines))

        self._pm = params[0]

        self.name = self.T.t("Michigan")
        self.description = self.T.td({
            self.state.lang.State.pl_PL: """
            Algorytm oparty o podejście Michigan.

            Osobnik - reprezentacja pojedynczej maszyny z pakietu maszyn. Składa się z 1 chromosomu.
            Chromosom - reprezentacja przypisanego do osobnika (maszyny) zestawu zadań.
            Gen - reprezentacja pojedynczego zadania z pakietu zadań. 
            Selekcja - brak selekcji pomiędzy epokami.

            Krzyżowanie - 1-punktowe, każdy osobnik bierze udział.

            Mutacja - mieszanie (shuffle) genów (zadań) w chromosomie.
            """,

            self.state.lang.State.en_GB: """
            Algorithm based on the Michigan approach.

            Entity - a representation of a single machine from the machine array. Made up of 1 chromosome.
            Chromosome - a representation of the tasks assigned to the entity (machine).
            Gene - a representation of a single task from the task array.

            Selection - no selection between epochs.

            Crossover - 1-point, every entity takes part.

            Mutation - shuffling of genees (tasks) within a chromosome.
            """
        })

    def _generate_population(self):
        tasks_cpy = self.tasks.index.values.copy()
        np.random.shuffle(tasks_cpy)

        tasks_to_machines = np.array_split(list(tasks_cpy), len(self.machines))
        # get rid of ndarray
        self.population = [list(t) for t in tasks_to_machines]

    def __fitness_for_machine(self, machine_id, machine_tasks):
        """
        Makes use of existing fitness functions to get fitness function for a single machine
        """
        faux_map = {m_id: [] for m_id in range(len(self.machines))}
        faux_map[machine_id] = machine_tasks

        return self._fitness(faux_map)

    def __sort_population(self):
        """
        Returns a population sorted by fitness.
        """
        fitness_map = [
            self.__fitness_for_machine(m_id, tasks).scheduling() for m_id, tasks in enumerate(self.population)
        ]

        tmp = sorted(zip(self.population, fitness_map), reverse=True)
        sorted_pop = [t[0] for t in tmp]

        return sorted_pop

        #return sorted(self.population, key=lambda x: self._fitness(self.build_schedule_map(x)).scheduling())

    def _crossover_population(self):
        """
        Krzyżuje populację parami maszyn (z top i bottom).
        :return: nowa populacja po krzyżowaniu
        """
        sorted_pop = self.__sort_population()

        top, bottom = self.__split_population(sorted_pop)
        new_t = top.copy()
        new_b = bottom.copy()
        for i, (t, b) in enumerate(zip(top, bottom)):
            new_t[i], new_b[i] = self.__cross_pair(t, b)

        self.population = new_t + new_b

    def __split_population(self, population):
        """
        Divides the population in half and shuffles the resultant halves.

        :return: shuffled top and bottom halves.
        """
        # guaranteed to be even, but whatever
        mid = self._pop_size.get_value() // 2

        top, bottom = population[:mid], population[mid:]

        np.random.shuffle(top)
        np.random.shuffle(bottom)

        return list(top), list(bottom)

    def __cross_pair(self, first, second):
        """
        Performs crossover between first and second.

        :param first: First chromosome.
        :param second: Second chromosome.
        """
        size_first = len(first)
        size_second = len(second)
        cp1 = randint(1, size_first) if size_first > 1 else 1
        cp2 = randint(1, size_second) if size_second > 1 else 1
        child1 = first[:cp1] + second[cp2:]
        child2 = second[:cp2] + first[cp1:]

        return child1, child2

    def __check_mutation(self):
        return np.random.uniform(0, 1) <= self._pm.get_value()

    def _mutate_population(self):
        """
        Mutacja populacji (in-place shuffle)
        """
        for individual in self.population:
            if self.__check_mutation():
                np.random.shuffle(individual)

    def build_schedule_map(self, solution):
        schedule_map = {
            m_id: tasks for m_id, tasks in enumerate(solution)
        }

        return schedule_map

    def _evaluate_population(self):
        """
        In Michigan representation, the whole population is the solution
        """
        current = self.build_schedule_map(self.population)
        current_f = self._fitness(current)

        if self.best_solution is None or current_f.scheduling() < self.best_score.scheduling():
            self.best_solution = current
            self.best_score = current_f