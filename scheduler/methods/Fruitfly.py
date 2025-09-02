from platform import machine

import numpy as np
import scheduler.Common as Common
from lang.Lang import T
from scheduler.Logger import Logger
from scheduler.MethodCache import MethodCache
from scheduler.ProgramState import ProgramState
from scheduler.Registry import MethodRegistrator
from scheduler.methods.BaseMethod import BaseMethod
from scheduler.Parameters import ParamDef, ParamDef2, ParamValueTypes
from scheduler.methods.ParticleSwarmMethod import ParticleSwarmMethod

@MethodRegistrator.register_class
class FruitflyMethod(ParticleSwarmMethod):
    def __init__(self, state: ProgramState, logger: Logger, t: T, cache: MethodCache):
        super().__init__(state, logger, t, cache)

        params = [
            ParamDef2(self.T.t("step size"), ParamValueTypes.FLOAT, 10, self.T.t("Step size in vision phase"),
                      min_value=0.0, max_value=len(self.machines))
        ]

        self.PARAM_DEFS += params

        self._vision_step = params[0].get_value()

        self.name = "Fruitfly"
        self.description = self.T.td({
            self.state.lang.State.pl_PL: """
            Algorytm optymalizacyjny Fruitfly. Rodzaj algorytmu optymalizacyjnego particle swarm.
            
            Osobniki i przestrzeń poszukiwań konstruowane są tak samo, jak zostało przedstawione w opisie metody Dragonfly.
            
            Algorytm definiuje 2 fazy:
            1. Szukanie zapachu (smell search), czyli znalezienie pozycji osobnika z najlepszą wartością funkcji przystosowania, 
            2. Przemieszczenie się w stronę zapachu (vision search).
            
            Algorytm wykonuje te 2 fazy w pętli aż do osiągnięcia warunku końcowego.
            """,
            self.state.lang.State.en_GB: """
            Fruitfly optimisation algorithm. A type of particle swarm optimisation algorithm.
            
            Entities and the search space are constructed in the same way as is defined in the description of the Dragonfly method.
            
            The algorithm defines 2 phases:
            1. Smell search -  finding the position of the entity with the best value of the fitness function,
            2. Vision search - "flying" toward the position of the smell.
            
            The algorithm performs these 2 phases in a loop until a stop condition is reached.
            """
        })

    def optimize(self):
        while not self.stop():
            # smell search
            best_smell = min(
                self.population,
                key=lambda x: self._fitness(self.build_schedule_map(x)).scheduling()
            )

            # vision search
            for inx, individual in enumerate(self.population):
                self.population[inx] = best_smell + np.random.randn(len(self.tasks)) * self._vision_step
                self.population[inx] = np.clip(self.population[inx], 0, len(self.machines) - 1)

            self._evaluate_population_update_best()
            self._epoch += 1