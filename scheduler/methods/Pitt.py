from abc import ABC, abstractmethod
from typing import Dict, List

from lang.Lang import T
from scheduler import Common
from scheduler.MethodCache import MethodCache
from scheduler.Logger import Logger
from scheduler.Parameters import ParamDef2, ParamValueTypes, PopulationValidator
from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod

class BasePittMethod(BaseMethod, ABC):
    def __init__(self, state: ProgramState, logger: Logger, t: T, cache: MethodCache):
        super().__init__(state, logger, t, cache)

        self._tasks_possible_machines = []
        self.population = []

        self.PARAM_DEFS = [
            ParamDef2(self.T.t("Iterations"), ParamValueTypes.INT, 100, self.T.t("Number of iterations (epochs)"),
                      min_value=1),
            ParamDef2(self.T.t("Population size"), ParamValueTypes.INT, 10, self.T.t("Population size (must be even)"),
                      min_value=2,
                      validator=PopulationValidator()),
        ]

        # defaults (for easier access - therefore hacky)
        self._iterations = self.PARAM_DEFS[0].get_value()
        self._pop_size = self.PARAM_DEFS[1].get_value()

    @abstractmethod
    def _generate_individual(self):
        pass

    @abstractmethod
    def _crossover_population(self):
        pass

    @abstractmethod
    def _mutate_population(self):
        pass

    def initialize(self):
        self._tasks_possible_machines = self._map_possible_machines_to_tasks()
        self.population = [self._generate_individual() for _ in range(self._pop_size)]
        self._evaluate_population_initial()

    def optimize(self):
        for epoch in range(self._iterations):
            self._crossover_population()
            self._mutate_population()
            self._evaluate_population_update_best(epoch)

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