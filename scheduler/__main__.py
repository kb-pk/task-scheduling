from .methods import Michigan
from .methods import Pitt_direct
from .methods import Pitt_perm
from .methods import Dragonfly
from .methods import Fruitfly
from .methods.BaseMethod import BaseMethod
from . import Common

import time
from typing import Optional, Type
from .Parametrs import get_or_set_method

current_algorithm: Optional[BaseMethod] = None

def run_algorithm(alg_cls: Type[BaseMethod], values_list=None, *, auto_outputs=True):
    """
    Reuse singleton:
      - create if none
      - else update ALL params (set_parameters) z listy
      - run()
    """
    global current_algorithm
    try:
        current_algorithm = get_or_set_method(alg_cls, values_list)
    except Exception as e:
        print(f"[Param ERROR] {getattr(alg_cls,'__name__',alg_cls)}: {e}")
        return
    try:
        current_algorithm.run()
    except Exception as e:
        print(f"[Run ERROR] {alg_cls.__name__}: {e}")

def choices(x):
    if x == 1:
        run_algorithm(Pitt_perm.PittPermMethod, values_list=[100, 10, 0.01, 0.01, False])
        time.sleep(1)
    elif x == 2:
        run_algorithm(Pitt_direct.PittDirectMethod, values_list=[100, 10, 1, 0.01, False])
        time.sleep(1)
    elif x == 3:
        run_algorithm(Michigan.MichiganMethod, values_list=[100, 0.01, False])
        time.sleep(1)
    elif x == 4:
        run_algorithm(Dragonfly.DragonflyMethod, values_list=[100, 30, 0.9, 0.1, 0.1, 0.1, 2.0, 1.0, 0.5, False])
    elif x == 5:
        run_algorithm(Fruitfly.FruitflyMethod, values_list=[100, 10, 5, False])
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
