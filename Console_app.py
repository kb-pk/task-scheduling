import Michigan
import Pitt_direct
import Pitt_perm
import Common

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
        Common.scheduling_mode = Common.ENERGY_MODE if Common.scheduling_mode == Common.MAKESPAN_MODE else Common.MAKESPAN_MODE
    elif x == 5:
        Common.output_mode = (Common.output_mode + 1) % len(Common.output_modes)
    elif x == 6:
        exit()
    else:
        print('Wrong choice')
        time.sleep(1)


if __name__ == "__main__":
    while True:
        userInput = int(input("Which algorithm would you like to use?\n"
              "1. Permutation-based Pitt algorithm\n"
              "2. Direct Pitt algorithm\n"
              "3. Michigan algorithm\n"
              "4. Switch scheduling mode (current mode: " + Common.scheduling_modes[Common.scheduling_mode] + ")\n" +
              "5. Switch output mode (current mode: " + Common.output_modes[Common.output_mode] + ")\n" +
              "6. Exit program\n"))

        choices(userInput)







