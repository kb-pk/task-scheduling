from abc import ABC, abstractmethod
import numpy as np

import scheduler.Common as Common
from lang.Lang import T
from scheduler.Logger import Logger
from scheduler.Parameters import ParamDef
from scheduler.ProgramState import ProgramState


class BaseMethod(ABC):
    PARAM_DEFS = []

    def __init__(self, state: ProgramState, logger: Logger, t: T):
        self.features = Common.read_security_features()
        self.machines = Common.read_machines(self.features)
        self.tasks = Common.read_tasks(self.features)
        self.etc = Common.generate_etc_matrix(self.machines, self.tasks)

        # Cached last run artifacts (for GUI one‑click access)
        self.last_schedule_map = None
        self.last_metrics = {}
        self.last_solution = None

        self.name = None
        self.description = None

        self.state = state
        self.logger = logger
        self.T = t

    def set_parameters(self, method_params: list[ParamDef]):
        """
        Used to update parameters of a given child method
        """
        self.PARAM_DEFS = method_params

    def get_parameters(self):
        return self.PARAM_DEFS

    def get_name(self):
        return self.name

    def get_description(self):
        return self.description

    @abstractmethod
    def initialize(self):
        raise NotImplementedError

    @abstractmethod
    def optimize(self):
        raise NotImplementedError

    @abstractmethod
    def get_best_solution(self):
        raise NotImplementedError

    @abstractmethod
    def build_schedule_map(self, solution):
        """Konwersja solution -> {machine_id: [task_ids]}."""
        raise NotImplementedError

    def _schedule_map_to_direct(self, schedule_map):
        """
        Converts schedule map to direct mapping [machine_id, ...], where the index is the task id
        """
        direct = [0 for _ in range(len(self.tasks))]
        for machine, tasks in schedule_map.items():
            for task in tasks:
                direct[task] = machine

        return direct

    def run(self):
        self.initialize()
        self.optimize()
        solution = self.get_best_solution()
        schedule_map = self.build_schedule_map(solution)
        metrics = self._compute_metrics(schedule_map)

        # cache results
        self.last_solution = solution
        self.last_schedule_map = schedule_map
        self.last_metrics = metrics

    def _get_loads(self, schedule_map):
        loads = [0.0 for _ in range(len(self.machines))]

        for m_id, tasks in schedule_map.items():
            for t in tasks:
                loads[m_id] += self.etc[t][m_id]

        return loads

    def _makespan(self, schedule_map):
        loads = self._get_loads(schedule_map)
        return max(loads)

    def _energy(self, schedule_map):
        loads = self._get_loads(schedule_map)
        makespan_val = max(loads)

        p_busy = self.machines['P_busy'].values
        p_idle = self.machines['P_idle'].values

        # Energy = (BusyTime * P_busy) + (IdleTime * P_idle)
        # where IdleTime = Makespan - BusyTime (load)
        total_energy = np.sum(loads * p_busy + (makespan_val - loads) * p_idle)

        return total_energy

    def _fitness_function(self, schedule_map):
        match Common.scheduling_mode:
            case Common.MAKESPAN_MODE:
                return self._makespan(schedule_map)
            case Common.ENERGY_MODE:
                return self._energy(schedule_map)
            case _:
                raise NotImplementedError

    def _compute_metrics(self, schedule_map):
        makespan = self._makespan(schedule_map)
        energy = self._energy(schedule_map)
        return makespan, energy