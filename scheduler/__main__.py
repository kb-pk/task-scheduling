from .methods import Michigan
from .methods import Pitt_direct
from .methods import Pitt_perm
from .methods import Dragonfly
from . import Common
from . import Utils

import time

def choices(x):
    if x == 1:
        Pitt_perm.main(),
        time.sleep(1)
    elif x == 2:
        Pitt_direct.main(),
        time.sleep(1)
    elif x == 3:
        Michigan.main(),
        time.sleep(1)
    elif x == 4:
        Dragonfly.main(),
        time.sleep(1)
    elif x == 5:
        Common.scheduling_mode = Common.ENERGY_MODE if Common.scheduling_mode == Common.MAKESPAN_MODE else Common.MAKESPAN_MODE
    elif x == 6:
        Common.output_mode = (Common.output_mode + 1) % len(Common.output_modes)
    elif x == 7:
        exit()
    else:
        print('Wrong choice')
        time.sleep(1)


def main():
    Utils.prepare_results_directory()
    while True:
        try:
            userInput = int(input("Which algorithm would you like to use?\n"
                "1. Permutation-based Pitt algorithm\n"
                "2. Direct Pitt algorithm\n"
                "3. Michigan algorithm\n"
                "4. Dragonfly algorithm\n"
                "5. Switch scheduling mode (current mode: " + Common.scheduling_modes[Common.scheduling_mode] + ")\n" +
                "6. Switch output mode (current mode: " + Common.output_modes[Common.output_mode] + ")\n" +
                "7. Exit program\n"))
            choices(userInput)
        except ValueError:
            print("Please enter a valid number.")
            time.sleep(1)


if __name__ == "__main__":
    main()
