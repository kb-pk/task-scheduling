import numpy as np
import scheduler.Common as Common
from scheduler.methods.BaseMethod import BaseMethod
from scheduler.Parameters import ParamDef

class DragonflyMethod(BaseMethod):
    PARAM_DEFS = [
        ParamDef("iterations", "int", 100, "Number of iterations", min_value=1),
        ParamDef("population_size", "int", 30, "Swarm size", min_value=2),
        ParamDef("w_inertia", "float", 0.9, "Inertia weight", min_value=0.0, max_value=5.0),
        ParamDef("w_separation", "float", 0.1, "Separation weight", min_value=0.0, max_value=5.0),
        ParamDef("w_alignment", "float", 0.1, "Alignment weight", min_value=0.0, max_value=5.0),
        ParamDef("w_cohesion", "float", 0.1, "Cohesion weight", min_value=0.0, max_value=5.0),
        ParamDef("w_food", "float", 2.0, "Food attraction weight", min_value=0.0, max_value=10.0),
        ParamDef("w_enemy", "float", 1.0, "Enemy repulsion weight", min_value=0.0, max_value=10.0),
        ParamDef("neighbour_radius_factor", "float", 0.5, "Neighbour radius factor", min_value=0.0, max_value=10.0),
        ParamDef("show_chart", "bool", True, "Display Gantt chart after run")
    ]

    def __init__(self,
                 iterations=100,
                 population_size=30,
                 w_inertia=0.9,
                 w_separation=0.1,
                 w_alignment=0.1,
                 w_cohesion=0.1,
                 w_food=2.0,
                 w_enemy=1.0,
                 neighbour_radius_factor=0.5,
                 show_chart=True):
        super().__init__(iterations=iterations, show_chart=show_chart)
        self.population_size = population_size
        self.w_inertia = w_inertia
        self.w_separation = w_separation
        self.w_alignment = w_alignment
        self.w_cohesion = w_cohesion
        self.w_food = w_food
        self.w_enemy = w_enemy
        self.neighbour_radius_thresh = neighbour_radius_factor * (len(self.machines) - 1)

        self.X = None  # positions
        self.V = None  # velocities
        self.best_pos = None
        self.worst_pos = None
        self.best_score = None
        self.other_score = None

    def set_parameters(self, iterations=100, population_size=30, w_inertia=0.9, w_separation=0.1,
                       w_alignment=0.1, w_cohesion=0.1, w_food=2.0, w_enemy=1.0,
                       neighbour_radius_factor=0.5, show_chart=True):
        self.iterations = iterations
        self.population_size = population_size
        self.w_inertia = w_inertia
        self.w_separation = w_separation
        self.w_alignment = w_alignment
        self.w_cohesion = w_cohesion
        self.w_food = w_food
        self.w_enemy = w_enemy
        self.neighbour_radius_factor = neighbour_radius_factor
        self.neighbour_radius_thresh = neighbour_radius_factor * (len(self.machines) - 1)
        self.show_chart = show_chart

    def get_name(self):
        return "dragonfly"

    # --- lifecycle ---
    def initialize(self):
        tasks_num = len(self.tasks)
        machines_num = len(self.machines)
        self.X = np.random.uniform(0, machines_num - 1, size=(self.population_size, tasks_num))
        self.V = np.zeros_like(self.X)
        fitness = np.array([Common.vector_fitness(x, self.etc, self.machines, Common.scheduling_mode)[0] for x in self.X])
        b_idx = np.argmin(fitness)
        w_idx = np.argmax(fitness)
        self.best_pos = self.X[b_idx].copy()
        self.worst_pos = self.X[w_idx].copy()
        self.best_score, self.other_score = Common.vector_fitness(self.best_pos, self.etc, self.machines, Common.scheduling_mode)

    def optimize(self):
        for it in range(self.iterations):
            self._iterate()
            cur, oth = Common.vector_fitness(self.best_pos, self.etc, self.machines, Common.scheduling_mode)
            if cur < self.best_score:
                self.best_score = cur
                self.other_score = oth
                print(f"[{it}] new best {Common.scheduling_modes[Common.scheduling_mode]}: {self.best_score:.4f}")

    def get_best_solution(self):
        return self.best_pos

    def build_schedule_map(self, position_vector):
        assign = Common.decode_position_vector(position_vector, len(self.machines))
        schedule_map = {m: [] for m in self.machines.index.values}
        for task_id, m_id in enumerate(assign):
            schedule_map[int(m_id)].append(task_id)
        return schedule_map

    # --- core iteration ---
    def _iterate(self):
        tasks_num = len(self.tasks)
        machines_num = len(self.machines)
        dist = np.linalg.norm(self.X[:, None, :] - self.X[None, :, :], axis=2)
        prev_best_val = Common.vector_fitness(self.best_pos, self.etc, self.machines, Common.scheduling_mode)[0]
        prev_worst_val = Common.vector_fitness(self.worst_pos, self.etc, self.machines, Common.scheduling_mode)[0]

        for i in range(self.population_size):
            neighbors = np.where((dist[i] < self.neighbour_radius_thresh) & (dist[i] > 0))[0]
            if len(neighbors) > 0:
                S = -np.sum(self.X[neighbors] - self.X[i], axis=0)               # separation
                A = np.mean(self.V[neighbors], axis=0)                            # alignment
                C = np.mean(self.X[neighbors], axis=0) - self.X[i]                # cohesion
                F = self.best_pos - self.X[i]                                     # attraction to food
                Rv = self.worst_pos + self.X[i]                                   # repulsion (as in original)
                self.V[i] = (
                    self.w_inertia * self.V[i] +
                    self.w_separation * S +
                    self.w_alignment * A +
                    self.w_cohesion * C +
                    self.w_food * F +
                    self.w_enemy * Rv
                )
                self.X[i] += self.V[i]
            else:
                # random walk
                self.X[i] += np.random.randn(tasks_num) * (self.X[i] - self.worst_pos)
            self.X[i] = np.clip(self.X[i], 0, machines_num - 1)

        fitness = np.array([Common.vector_fitness(x, self.etc, self.machines, Common.scheduling_mode)[0] for x in self.X])
        cb = np.argmin(fitness)
        cw = np.argmax(fitness)
        if fitness[cb] < prev_best_val:
            self.best_pos = self.X[cb].copy()
        if fitness[cw] > prev_worst_val:
            self.worst_pos = self.X[cw].copy()


if __name__ == "__main__":
    alg = DragonflyMethod(iterations=100, population_size=30, w_inertia=0.9, w_separation=0.1, w_alignment=0.1, w_cohesion=0.1, w_food=2.0, w_enemy=1.0, neighbour_radius_factor=0.5, show_chart=True)
    alg.run()