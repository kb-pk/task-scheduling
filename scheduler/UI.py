from abc import abstractmethod, ABC
import time

from lang.Lang import T
from scheduler.ProgramState import ProgramState
from scheduler.Registry import UIRegistrator
from scheduler.methods.BaseMethod import BaseMethod


class UI(ABC):
    def __init__(self, state: ProgramState, t: T, method_instances: dict[str, BaseMethod]):
        self.state = state
        self.T = t
        self.method_instances = method_instances

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
                "8. " + self.T.t("Switch stop criterion (current mode: " + self.state.stop_criterion.get().name + ")"),
                "9. " + self.T.t("Exit program")
            ]

            for choice in prompt:
                print(choice)

            try:
                user_choice = int(input())
            except ValueError:
                print(self.T.t("Invalid choice"))
                time.sleep(1)
                continue

            self.choices(user_choice)

    def choices(self, x):
        # TODO - this shouldnt be a literal, but a `class.__name__` or just `class`!
        if 1 <= x <= 5:
            # order of methods in the menu
            methods = [
                "PittDirectMethod",
                "PittPermMethod",
                "MichiganMethod",
                "DragonflyMethod",
                "FruitflyMethod",
            ]

            instance = self.method_instances.get(methods[x])
            self.parameter_choices(instance)

            instance.run()
        elif 6 <= x <= 8:
            states = [
                self.state.scheduling,
                self.state.output,
                self.state.stop_criterion,
            ]

            current = states[x - 6]

            current.set(
                (current.get().value + 1) % len (current.State)
            )
        elif x == 9:
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
