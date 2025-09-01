from abc import abstractmethod
from typing import Dict, List

from lang.Lang import T
from scheduler import Common
from scheduler.MethodCache import MethodCache
from scheduler.Logger import Logger
from scheduler.ProgramState import ProgramState
from scheduler.methods.EvolAlgoBaseMethod import EvolAlgoBaseMethod


class BasePittMethod(EvolAlgoBaseMethod):
    def __init__(self, state: ProgramState, logger: Logger, t: T, cache: MethodCache):
        super().__init__(state, logger, t, cache)

        self._tasks_possible_machines = []

    @abstractmethod
    def _generate_individual(self):
        pass

    def _generate_population(self):
        self.population = [self._generate_individual() for _ in range(self._pop_size)]

    @abstractmethod
    def _crossover_population(self):
        pass

    @abstractmethod
    def _mutate_population(self):
        pass

    def initialize(self):
        self._tasks_possible_machines = self._map_possible_machines_to_tasks()
        super().initialize()

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