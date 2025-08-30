from .methods import Michigan
from .methods import Pitt_direct
from .methods import Pitt_perm
from .methods import Dragonfly
from .methods import Fruitfly
from .methods.BaseMethod import BaseMethod
from . import Common

import time
from typing import Optional, Type

current_algorithm: Optional[BaseMethod] = None  # "wskaznik" na bieżący obiekt algorytmu

def run_algorithm(alg_cls: Type[BaseMethod], **kwargs):
    global current_algorithm
    current_algorithm = alg_cls(**kwargs)
    current_algorithm.run()

def choices(x):
    if x == 1:
        run_algorithm(Pitt_perm.PittPermMethod, iterations=100, population_size=10, pm_swap=0.01, pm_transposition=0.01, show_chart=True)
        time.sleep(1)
    elif x == 2:
        run_algorithm(Pitt_direct.PittDirectMethod, iterations=100, population_size=10, crossover_points = 1, mutation_probability = 0.01, show_chart=True)
        time.sleep(1)
    elif x == 3:
        run_algorithm(Michigan.MichiganMethod, iterations=100, pm=0.01, show_chart=True)
        time.sleep(1)
    elif x == 4:
        run_algorithm(Dragonfly.DragonflyMethod, iterations=100, population_size=30, w_inertia=0.9, w_separation=0.1, w_alignment=0.1, w_cohesion=0.1, w_food=2.0, w_enemy=1.0, neighbour_radius_factor=0.5, show_chart=True)
    elif x == 5:
        run_algorithm(Fruitfly.FruitflyMethod, iterations=100, population_size=10, show_chart=True)
        time.sleep(1)
    elif x == 6:
        Common.scheduling_mode = Common.ENERGY_MODE if Common.scheduling_mode == Common.MAKESPAN_MODE else Common.MAKESPAN_MODE
    elif x == 7:
        Common.output_mode = (Common.output_mode + 1) % len(Common.output_modes)
    elif x == 8:
        exit()
    else:
        print('Wrong choice')
        time.sleep(1)


def main():
    Common.prepare_results_directory()
    while True:
        try:
            userInput = int(input("Which algorithm would you like to use?\n"
                "1. Permutation-based Pitt algorithm\n"
                "2. Direct Pitt algorithm\n"
                "3. Michigan algorithm\n"
                "4. Dragonfly algorithm\n"
                "5. Fruitfly algorithm\n"
                "6. Switch scheduling mode (current mode: " + Common.scheduling_modes[Common.scheduling_mode] + ")\n" +
                "7. Switch output mode (current mode: " + Common.output_modes[Common.output_mode] + ")\n" +
                "8. Exit program\n"))
            choices(userInput)
        except ValueError:
            print("Please enter a valid number.")
            time.sleep(1)


if __name__ == "__main__":
    main()
