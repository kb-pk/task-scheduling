import numpy as np
import scheduler.Common as Common
from .BaseMethod import BaseMethod, Lang
from scheduler.Parametrs import ParamDef, register_method

@register_method
class FruitflyMethod(BaseMethod):
    PARAM_DEFS = [
        ParamDef("iterations", "int", 100, "Number of iterations", min_value=1),
        ParamDef("population_size", "int", 30, "Population size", min_value=2),
        ParamDef("vision_step", "float", 5.0, "Vision phase standard deviation", min_value=0.0, max_value=100.0),
        ParamDef("show_chart", "bool", True, "Display Gantt chart after run")
    ]

    def __init__(self,
                 iterations=100,
                 population_size=30,
                 vision_step=5.0,
                 show_chart=True):
        super().__init__(iterations=iterations, show_chart=show_chart)
        self.population_size = population_size
        self.vision_step = vision_step
        self.population = None
        self.best_pos = None
        self.best_score = None
        self.other_score = None

    def set_parameters(self, iterations=100, population_size=30, vision_step=5.0, show_chart=True):
        self.iterations = iterations
        self.population_size = population_size
        self.vision_step = vision_step
        self.show_chart = show_chart

    def get_method_name(self):
        return "fruitfly"

    # --- lifecycle ---
    def initialize(self):
        tasks_num = len(self.tasks)
        machines_num = len(self.machines)
        self.population = np.random.uniform(0, machines_num - 1, size=(self.population_size, tasks_num))
        fitness = np.array([Common.vector_fitness(x, self.etc, self.machines, Common.scheduling_mode)[0] for x in self.population])
        idx = np.argmin(fitness)
        self.best_pos = self.population[idx].copy()
        self.best_score, self.other_score = Common.vector_fitness(self.best_pos, self.etc, self.machines, Common.scheduling_mode)

    def optimize(self):
        tasks_num = len(self.tasks)
        machines_num = len(self.machines)
        for it in range(self.iterations):
            # Smell search
            smell_vals = np.array([Common.vector_fitness(x, self.etc, self.machines, Common.scheduling_mode)[0] for x in self.population])
            i_smell = np.argmin(smell_vals)
            X_smell = self.population[i_smell].copy()

            # Vision search
            for i in range(self.population_size):
                self.population[i] = X_smell + np.random.randn(tasks_num) * self.vision_step
                self.population[i] = np.clip(self.population[i], 0, machines_num - 1)
                main_val, other_val = Common.vector_fitness(self.population[i], self.etc, self.machines, Common.scheduling_mode)
                if main_val < self.best_score:
                    self.best_score = main_val
                    self.other_score = other_val
                    self.best_pos = self.population[i].copy()
                    print(f"[{it}] new best {Common.scheduling_modes[Common.scheduling_mode]}: {self.best_score:.4f}")

    def get_best_solution(self):
        return self.best_pos

    def build_schedule_map(self, position_vector):
        assign = Common.decode_position_vector(position_vector, len(self.machines))
        schedule_map = {m: [] for m in self.machines.index.values}
        for task_id, m_id in enumerate(assign):
            schedule_map[int(m_id)].append(task_id)
        return schedule_map

if __name__ == "__main__":
    alg = FruitflyMethod(iterations=100, population_size=30, vision_step=5.0, show_chart=True)
    alg.run()