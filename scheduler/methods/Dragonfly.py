from abc import ABC

import numpy as np
from lang.Lang import T
from scheduler.Logger import Logger
from scheduler.MethodCache import MethodCache
from scheduler.ProgramState import ProgramState
from scheduler.Registry import MethodRegistrator
from scheduler.Parameters import ParamDef, ParamValueTypes
from scheduler.methods.ParticleSwarmMethod import ParticleSwarmMethod

@MethodRegistrator.register_class
class DragonflyMethod(ParticleSwarmMethod, ABC):
    def __init__(self, state: ProgramState, logger: Logger, t: T, cache: MethodCache):
        super().__init__(state, logger, t, cache)

        params = [
            ParamDef(self.T.t("Inertia"), ParamValueTypes.FLOAT, 0.9, self.T.t("Movement inertia"),
                     min_value=0.0, max_value=1.0),
            ParamDef(self.T.t("Separation"), ParamValueTypes.FLOAT, 0.1, self.T.t("Separation between entities"),
                     min_value=0.0, max_value=1.0),
            ParamDef(self.T.t("Alignment"), ParamValueTypes.FLOAT, 0.1,
                     self.T.t("How closely entity's speed matches that of other entities"),
                     min_value=0.0, max_value=1.0),
            ParamDef(self.T.t("Cohesion"), ParamValueTypes.FLOAT, 0.1,
                     self.T.t("How much the entity is drawn to the center of their neighbourhood"),
                     min_value=0.0, max_value=1.0),
            ParamDef(self.T.t("Food attraction"), ParamValueTypes.FLOAT, 2.0,
                     self.T.t("How much the entity is drawn to food sources"),
                     min_value=0.0, max_value=10.0),
            ParamDef(self.T.t("Enemy repulsion"), ParamValueTypes.FLOAT, 1.0,
                     self.T.t("How much the entity is drawn away from enemy sources"),
                     min_value=0.0, max_value=10.0),
            ParamDef(self.T.t("Neighbour radius"), ParamValueTypes.FLOAT, (len(self.machines) - 1) / 2,
                      "",
                     min_value=0.0, max_value=len(self.machines)),
        ]

        self.PARAM_DEFS += params

        self._inertia = params[0].get_value()
        self._separation = params[1].get_value()
        self._alignment = params[2].get_value()
        self._cohesion = params[3].get_value()
        self._food_attraction = params[4].get_value()
        self._enemy_repulsion = params[5].get_value()
        self._neighbour_radius = params[6].get_value()

        self.name = "Dragonfly"
        self.description = self.T.td({
            self.state.lang.State.pl_PL: """
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

            self.state.lang.State.en_GB: """
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
        })

    def __set_food_and_enemies(self):
        fitness_of_individuals = [
             self._fitness(self.build_schedule_map(individual)).scheduling() for individual in self.population
        ]

        food_inx = np.argmin(fitness_of_individuals)
        enemies_inx = np.argmax(fitness_of_individuals)

        self._food = self.population[food_inx]
        self._enemies = self.population[enemies_inx]

    def _evaluate_population(self):
        super()._evaluate_population()

        self.__set_food_and_enemies()

    def optimize(self):
        while not self.stop():
            dist = np.linalg.norm(self.population[:, None, :] - self.population[None, :, :], axis=2)

            for i in range(self._pop_size):
                neighbors = np.where((dist[i] < self._neighbour_radius) & (dist[i] > 0))[0]

                if len(neighbors) > 0:
                    # Separation
                    S = -np.sum(self.population[neighbors] - self.population[i], axis=0)
                    # Alignment
                    A = np.mean(self._velocity[neighbors], axis=0)
                    # Cohesion
                    C = np.sum(np.mean(self.population[neighbors], axis=0) - self.population[i], axis=0)
                    # Attraction to food (best solution)
                    F = self._food - self.population[i]
                    # Distraction from enemy (worst solution)
                    Rv = self._enemies + self.population[i]
                    # Velocity and position update
                    self._velocity[i] = (self._inertia * self._velocity[i] +
                                         self._separation * S +
                                         self._alignment * A +
                                         self._cohesion * C +
                                         self._food_attraction * F +
                                         self._enemy_repulsion * Rv)
                    self.population[i] += self._velocity[i]
                else:
                    # Random walk (Levy-like)
                    self.population[i] += np.random.randn(len(self.tasks)) * (self.population[i] - self._enemies)
                # Enforce bounds
                self.population[i] = np.clip(self.population[i], 0, len(self.machines) - 1)

            self._evaluate_population_update_best()
            self._epoch += 1