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
            ParamDef2(self.T.t("Population size"), ParamValueTypes.INT, 10, self.T.t("Population size (must be even)"),
                      min_value=2,
                      validator=PopulationValidator()),
            ParamDef2(self.T.t("Stop criterion"), ParamValueTypes.LIST_SINGLE, [
                ParamDef2(self.T.t("Iterations"), ParamValueTypes.INT, 100,
                          self.T.t("Number of iterations (epochs)"),
                          min_value=1),
                ParamDef2(self.T.t("Fitness function value"), ParamValueTypes.FLOAT, 6000,
                          self.T.t("The value which the algorithm is optimising (") +
                          self.T.t(self.state.scheduling.get().name) + ")",
                          min_value=1),
            ],
                self.T.t("Criterion for stopping the evolution")
            )
        ]

        self._pop_size = self.PARAM_DEFS[0].get_value()
        self._stop_criteria = self.PARAM_DEFS[1].get_value()
        self._iterations = self._stop_criteria[0].get_value()
        self._sched_value = self._stop_criteria[1].get_value()

        self._epoch = 0

    def initialize(self):
        self._epoch = 0

        stop_value = self._stop_criteria[self.state.stop_criterion.get().value].get_value()
        self.logger.stop_criterion(stop_value)

        self._generate_population()
        self._evaluate_population_initial()

    def optimize(self):
        while not self.stop():
            self._crossover_population()
            self._mutate_population()
            self._evaluate_population_update_best()
            self._epoch += 1

    def stop(self):
        match self.state.stop_criterion.get():
            case self.state.stop_criterion.State.iterations:
                return self._epoch >= self._iterations
            case self.state.stop_criterion.State.fitness_function_value:
                return self.best_score.scheduling() <= self._sched_value
            case _:
                raise NotImplementedError

    @abstractmethod
    def _generate_population(self):
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

            if self.best_solution is None or f.scheduling() < self.best_score.scheduling():
                self.best_solution = decode
                self.best_score = f

    def _evaluate_population_initial(self):
        self._evaluate_population()

        self.logger.initial_solution(self.best_score.output())

    def _evaluate_population_update_best(self):
        last_best = self.best_score
        self._evaluate_population()
        has_improved = last_best != self.best_score
        if has_improved:
            self.logger.better_solution_found(self.best_score.output(), self._epoch)