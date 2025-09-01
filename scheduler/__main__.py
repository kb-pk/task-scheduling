import time
from typing import Type

import scheduler.Common as Common
from scheduler.MethodRegistry import MethodRegistry
from scheduler.ProgramState import ProgramState
from scheduler.methods.BaseMethod import BaseMethod

from lang.Lang import T as T
from scheduler.methods.Dragonfly import DragonflyMethod
from scheduler.methods.Fruitfly import FruitflyMethod
from scheduler.methods.Michigan import MichiganMethod
from scheduler.methods.Pitt_direct import PittDirectMethod
from scheduler.methods.Pitt_perm import PittPermMethod


class Main:
    def __init__(self, state: ProgramState):
        self.__state = state
        self.T = T(self.__state)

        # intialize registered methods with current state
        self.__methods = {}
        for name, method in MethodRegistry.get_registry().items():
            self.__methods[name] = method(self.__state)

    def main(self):
        Common.prepare_results_directory()

        prompt = self.T.tl([
            "Which algorithm would you like to use?",
            "1. ", "Pitt (direct)",
            "2. ", "Pitt (permutation-based)",
            "3. ", "Michigan",
            "4. ", "Dragonfly",
            "5. ", "Fruitfly",
            "6. ", "Switch scheduling mode (current mode: ", self.__state.scheduling.get(), ")",
            "7. ", "Switch output mode (current mode: ", self.__state.output.get(), ")",
            "8. ", "Exit program"
        ])

        while True:
            try:
                for choice in prompt:
                    print(choice)

                user_choice = int(input())
                self.choices(user_choice)
            except ValueError:
                print(self.T.t("Invalid choice"))
                time.sleep(1)

    def run_algorithm(self, selected_method_name: str):
        instance = self.__methods.get(selected_method_name)

        self.get_params_from_user(instance)
        instance.run()

    def get_params_from_user(self, method: Type[BaseMethod]):
        pass

    def choices(self, x):
        # TODO - this shouldnt be a literal, but a `class.__name__` or just `class`!
        if x == 1:
            self.run_algorithm("PittDirectMethod")
            time.sleep(1)
        elif x == 2:
            self.run_algorithm("PittPermMethod")
            time.sleep(1)
        elif x == 3:
            self.run_algorithm("MichiganMethod")
            time.sleep(1)
        elif x == 4:
            self.run_algorithm("DragonflyMethod")
            time.sleep(1)
        elif x == 5:
            self.run_algorithm("FruitflyMethod")
            time.sleep(1)
        elif x == 6:
            self.__state.scheduling.set(
                (self.__state.scheduling.get() + 1) % len(self.__state.scheduling.State)
            )

            current = self.__state.scheduling.get()
            next = (current + 1) % len(self.__state.scheduling.State) + 1
            self.__state.scheduling.set(next)
        elif x == 7:
            self.__state.output.set(
                (self.__state.output.get() + 1) % len(self.__state.output.State)
            )
        elif x == 8:
            exit()
        else:
            print('Wrong choice')
            time.sleep(1)

if __name__ == "__main__":
    program_state = ProgramState()

    main = Main(program_state).main()
