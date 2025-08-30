import numpy as np
import scheduler.Common as Common
from .BaseMethod import BaseMethod, Lang

description = {
    "pl": """
    Algorytm optymalizacyjny Dragonfly. Rodzaj algorytmu optymalizacyjnego particle swarm.

    Algorytm polega na zdefiniowaniu w przestrzeni poszukiwań miejsc z jedzeniem (najlepszym rozwiązaniem z poprzedniej epoki) i z wrogami (najgorszym rozwiązaniem z poprzedniej epoki).
    Poziom przyciągania do źródeł jedzenia i odpychania od wrogów jest dyktowany parametrami.

    Osobniki w pobliżu (próg określony parametrem) tworzą sąsiedztwo danego osobnika.

    Dodatkowo zdefiniowane są parametry (wagi) w postaci:
    1. Bezwładności osobników (inertia)
    2. Separacji osobników od siebie (separation),
    3. Poruszania się z podobną prędkością co reszta osobników (alignment),
    4. Poruszania się w stronę centrum swojego sąsiedztwa (cohesion).

    Przestrzeń poszukiwań można sobie wyobrazić jako N-wymiarową (M = liczba zadań) przestrzeń z osobnikami "latającymi" wewnątrz niej zgodnie z ustalonymi parametrami.
    Pozycja (koordynaty) osobników wyrażają harmonogram w postaci [machine_id, machine_id, ...], gdzie indeks to numer zadania wykonywanego przez maszynę.

    Przykładowo, dla 3 zadań osobniki "latają" po 3-wymiarowej przestrzeni, gdzie ich koordynaty to harmonogram wszystkich maszyn.
    """,

    "en": """
    Dragonfly optimisation algorithm. A type of particle swarm optimisation algorithm.

    Algorithm defines places with food (best solution from last epoch) and enemies (worst solution from last epoch) in the search space.
    Levels of attraction toward food sources and repulsion from enemies are defined with parameters.

    Entities close (threshold is defined with a parameter) to the specific entity are considered its neighbourhood.

    Additionally, the following parameters (weights) are defined:
    1. Inertia of entities,
    2. Separation of entities from each other,
    3. Alignment of the entity in terms of speed with the rest of entities,
    4. Cohesion of entities in terms of being drawn to the center of their neighbourhood.

    The search space can be visualised as a N-dimensional (N = task number) space with the entities "flying" inside of it according to the defined parameters.
    Entity's position (its coordinates) represent a schedule in the form of [machine_id, machine_id, ...], where the index denotes the task number assigned to the machine.

    For example, for 3 machines the entities "fly" through a 3-dimensional space, where each entity's coordinates are a schedule for all the machines.
    """
}


class DragonflyMethod(BaseMethod):
    """
    Implementacja klasowa Dragonfly wykorzystująca wspólne utilsy w Common.
    """
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
        super().__init__(show_chart=show_chart)
        self.iterations = iterations
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

    def get_method_name(self):
        return "dragonfly"

    def get_method_description(self, lang: Lang):
        return description["pl"] if lang == Lang.PL else description["en"]

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

    def after_run(self, schedule_map, makespan, total_energy):
        primary = total_energy if Common.scheduling_mode == Common.ENERGY_MODE else makespan
        secondary = makespan if Common.scheduling_mode == Common.ENERGY_MODE else total_energy
        with open("results/result_dragonfly", "a") as f:
            f.write(f"{primary},{secondary}\n")

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