from abc import ABC, abstractmethod
import numpy as np

from scheduler.MethodCache import MethodCache
from lang.Lang import T
from scheduler.Logger import Logger
from scheduler.Parameters import ParamDef, ParamValueTypes
from scheduler.ProgramState import ProgramState
from scheduler.methods.IndividualFitness import IndividualFitness


class BaseMethod(ABC):
    def __init__(self, state: ProgramState, logger: Logger, t: T, cache: MethodCache):
        self.cache = cache

        self.state = state
        self.logger = logger
        self.T = t

        self.PARAM_DEFS = [
            ParamDef(self.T.t("Enable security features"), ParamValueTypes.BOOLEAN, bool(self.state.security_features.get().value),
                     self.T.t("Enable security features (prevents some machines from running some tasks)")),
        ]

        self._security_features = self.PARAM_DEFS[0]

        # TODO - these should be immutable (hidden behind getters), but whatever...
        self.features = self.cache[MethodCache.CacheObject.security_features]
        self.machines = self.cache[MethodCache.CacheObject.machines]
        self.tasks = self.cache[MethodCache.CacheObject.tasks]
        self.etc = self.cache[MethodCache.CacheObject.etc_matrix]

        if len(self.machines) > len(self.tasks):
            raise AssertionError(self.T.t("Number of tasks exceeds number of machines - machines cannot be without tasks"))

        self.last_solution = None

        self.best_solution = None
        self.best_score = None

        self.name = None
        self.description = None

    def set_parameters(self, method_params: list[ParamDef]):
        self.PARAM_DEFS = method_params

    def get_parameters(self):
        return self.PARAM_DEFS

    def get_name(self):
        return self.name

    def get_description(self):
        return self.description

    def get_best_solution(self):
        return self.best_solution

    @abstractmethod
    def initialize(self):
        """
        Initialise the method - generate population, etc.
        """
        raise NotImplementedError

    @abstractmethod
    def optimize(self):
        """
        Main optimization routine
        """
        raise NotImplementedError

    @abstractmethod
    def build_schedule_map(self, solution):
        """
        Convert method's representation of a schedule to a schedule map in the form of {machine_id: [task_id, task_id, ...], ...}

        :param solution: The method's representation of a schedule
        """
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        """
        Stop criterion
        """
        raise NotImplementedError

    def run(self):
        """
        Main routine of a method
        """
        self._reset()
        self.initialize()
        self.optimize()

        self.last_solution = self.get_best_solution()

    def _reset(self):
        self.best_solution = None
        self.best_score = None

    def _get_loads(self, schedule_map) -> list[float]:
        """
        Returns each machine's loads in a list

        :param schedule_map: A schedule map, as per self.build_schedule_map

        :return: List of machines' loads
        """
        loads = [0.0 for _ in range(len(self.machines))]

        for m_id, tasks in schedule_map.items():
            for t in tasks:
                loads[m_id] += self.etc[t][m_id]

        return loads

    def _makespan(self, schedule_map) -> float:
        """
        Fitness function - makespan (total time to execute the schedule)

        :param schedule_map: A schedule map, as per self.build_schedule_map

        :return: Makespan (scalar) of the schedule
        """
        loads = self._get_loads(schedule_map)
        return max(loads)

    def _energy(self, schedule_map) -> float:
        """
        Fitness function - energy (total energy to execute the schedule)

        :param schedule_map: A schedule map, as per self.build_schedule_map

        :return: Energy used by the machines (scalar) to execute the schedule
        """
        loads = self._get_loads(schedule_map)
        makespan_val = max(loads)

        p_busy = self.machines['P_busy'].values
        p_idle = self.machines['P_idle'].values

        # Energy = (BusyTime * P_busy) + (IdleTime * P_idle)
        # where IdleTime = Makespan - BusyTime (load)
        total_energy = np.sum(loads * p_busy + (makespan_val - loads) * p_idle)

        return total_energy

    def _metrics(self, schedule_map):
        """
        Return all metrics (fitness functions' values) of a schedule map.

        :param schedule_map: A schedule map, as per self.build_schedule_map

        :return: Metrics of the schedule map
        """
        makespan = self._makespan(schedule_map)
        energy = self._energy(schedule_map)

        return {
            self.state.scheduling.State.makespan: makespan,
            self.state.scheduling.State.energy: energy
        }

    def _fitness(self, schedule_map) -> IndividualFitness:
        """
        Build and return metrics of a given schedule map, wrapped into a IndividualFitness class

        :param schedule_map: A schedule map, as per self.build_schedule_map

        :return: Metrics of the schedule, inside a IndividualFitness class
        """
        metrics = self._metrics(schedule_map)
        return IndividualFitness(self.state, metrics)