from abc import abstractmethod

from lang.Lang import T
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
        self.population = [self._generate_individual() for _ in range(self._pop_size.get_value())]