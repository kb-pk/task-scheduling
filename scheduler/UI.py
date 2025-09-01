from abc import abstractmethod, ABC
import time
from typing import Callable

from lang.Lang import T
from scheduler.ProgramState import ProgramState
from scheduler.Registry import UIRegistrator


class UI(ABC):
    def __init__(self, state: ProgramState, t: T, run_algorithm: Callable[[str], None]):
        self.state = state
        self.T = t
        self.run_algorithm = run_algorithm

    @abstractmethod
    def log(self, message):
        pass

    @abstractmethod
    def start(self):
        pass

@UIRegistrator.register_class
class CLI(UI):
    def log(self, message):
        print(message)

    def start(self):
        while True:
            # reset after every choice
            prompt = [
                self.T.t("Which algorithm would you like to use?"),
                "1. " + self.T.t("Pitt (direct)"),
                "2. " + self.T.t("Pitt (permutation-based)"),
                "3. " + self.T.t("Michigan"),
                "4. " + self.T.t("Dragonfly"),
                "5. " + self.T.t("Fruitfly"),
                "6. " + self.T.t("Switch scheduling mode (current mode: ") + self.state.scheduling.get().name + ")",
                "7. " + self.T.t("Switch output mode (current mode: ") + self.state.output.get().name + ")",
                "8. " + self.T.t("Exit program")
            ]

            try:
                for choice in prompt:
                    print(choice)

                user_choice = int(input())
                self.choices(user_choice)
            except ValueError:
                print(self.T.t("Invalid choice"))
                time.sleep(1)

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
            self.state.scheduling.set(
                (self.state.scheduling.get().value + 1) % len(self.state.scheduling.State)
            )
        elif x == 7:
            self.state.output.set(
                (self.state.output.get().value + 1) % len(self.state.output.State)
            )
        elif x == 8:
            exit()
        else:
            print('Wrong choice')
            time.sleep(1)


@UIRegistrator.register_class
class GUI(UI):
    def _print_to_diagnostic(self, message):
        pass

    def log(self, message):
        self._print_to_diagnostic(message)

    def start(self):
        pass
