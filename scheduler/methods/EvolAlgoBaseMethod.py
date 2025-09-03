from abc import abstractmethod

from lang.Lang import T
from scheduler.Logger import Logger
from scheduler.MethodCache import MethodCache
from scheduler.Parameters import ParamDef, ParamValueTypes, PopulationValidator
from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod


class EvolAlgoBaseMethod(BaseMethod):
    def __init__(self, state: ProgramState, logger: Logger, t: T, cache: MethodCache):
        super().__init__(state, logger, t, cache)

        self.population = []
        self._tasks_possible_machines = None

        # Track best fitness per epoch for plotting
        self._history_fitness = []

        self.PARAM_DEFS = [
            ParamDef(self.T.t("Population size"), ParamValueTypes.INT, 10, self.T.t("Population size (must be even)"),
                     min_value=2,
                     validator=PopulationValidator()),
            ParamDef(self.T.t("Stop criterion"), ParamValueTypes.LIST_SINGLE, [
                ParamDef(self.T.t("Iterations"), ParamValueTypes.INT, 100,
                         self.T.t("Number of iterations (epochs)"),
                         min_value=1),
                ParamDef(self.T.t("Fitness function value"), ParamValueTypes.FLOAT, 6000,
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
        # Reset history for a fresh run
        self._history_fitness = []

        stop_value = self._stop_criteria[self.state.stop_criterion.get().value].get_value()
        self.logger.stop_criterion(stop_value)

        self._tasks_possible_machines = self._map_possible_machines_to_tasks()

        self._generate_population()
        self._evaluate_population_initial()
        # Record initial best metrics for epoch 0
        self._record_history_point()

    def optimize(self):
        while not self.stop():
            self._crossover_population()
            self._mutate_population()
            self._evaluate_population_update_best()
            # Record current best after this epoch
            self._record_history_point()
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

    # Append current best fitness to history (for plotting best-so-far).
    def _record_history_point(self):
        if self.best_score is not None:
            self._history_fitness.append(self.best_score)

    # Return list[IndividualFitness] history per epoch.
    def get_history(self):
        return list(self._history_fitness)

    def _map_possible_machines_to_tasks(self):
        """
        Mapuje zadania i maszyny, które dane zadanie mogą wykonać (na podstawie features).
        :return: Słownik {task_id: [machine_id, machine_id, ...], ...}
        """
        possible_machines_for_tasks = {task_id: [
            machine_id for machine_id in self.machines.index.values
            if self._can_execute_task_on_machine(self.machines.iloc[machine_id], self.tasks.iloc[task_id], self.features)
        ] for task_id in self.tasks.index.values}

        return possible_machines_for_tasks

    def _can_execute_task_on_machine(self, machine, task, features):
        """
        Sprawdzenie czy można wykonać zadanie na maszynie,
        czyli czy wszystkie wartości cech wymaganych przez zadanie są mniejsze niż cechy maszyny
        :param machine: wiersz określający maszynę
        :param task: wiersz określający zadaine
        :param features: macierz cech bezpieczenstwa
        :return: True jesli można wykonać zadanie, False w przeciwnym wypadku
        """
        for feature_id in features.index.values:
            feature_name = features.values[feature_id][0]
            if task[feature_name] > machine[feature_name]:
                return False

        return True

