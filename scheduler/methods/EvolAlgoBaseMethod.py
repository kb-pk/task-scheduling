from abc import abstractmethod

from lang.Lang import T
from scheduler.Logger import Logger
from scheduler.MethodCache import MethodCache
from scheduler.Parameters import ParamDef2, ParamValueTypes, PopulationValidator
from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod


class EvolAlgoBaseMethod(BaseMethod):
    def __init__(self, state: ProgramState, logger: Logger, t: T, cache: MethodCache):
        super().__init__(state, logger, t, cache)

        self.population = []

        self.PARAM_DEFS = [
            ParamDef2(self.T.t("Iterations"), ParamValueTypes.INT, 100, self.T.t("Number of iterations (epochs)"),
                      min_value=1),
            ParamDef2(self.T.t("Population size"), ParamValueTypes.INT, 10, self.T.t("Population size (must be even)"),
                      min_value=2,
                      validator=PopulationValidator()),
        ]

        self._iterations = self.PARAM_DEFS[0].get_value()
        self._pop_size = self.PARAM_DEFS[1].get_value()

    def initialize(self):
        self.population = [self._generate_individual() for _ in range(self._pop_size)]
        self._evaluate_population_initial()

    def optimize(self):
        for epoch in range(self._iterations):
            self._crossover_population()
            self._mutate_population()
            self._evaluate_population_update_best(epoch)

    @abstractmethod
    def _generate_individual(self):
        pass

    @abstractmethod
    def _crossover_population(self):
        pass

    @abstractmethod
    def _mutate_population(self):
        pass

    def _evaluate_population(self):
        for individual in self.population:
            decode = self.build_schedule_map(individual)
            f = self._fitness(decode)

            if self.best_individual is None or f.scheduling() < self.best_score.scheduling():
                self.best_individual = decode
                self.best_score = f

    def _evaluate_population_initial(self):
        self._evaluate_population()

        self.logger.initial_solution(self.best_score.output())

    def _evaluate_population_update_best(self, epoch):
        last_best = self.best_score
        self._evaluate_population()
        has_improved = last_best != self.best_score
        if has_improved:
            self.logger.better_solution_found(self.best_score.output(), epoch)