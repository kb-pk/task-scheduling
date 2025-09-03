from abc import abstractmethod, ABC
import time

from lang.Lang import T
from scheduler.Parameters import ParamDef, ParamValueTypes
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

    def __get_user_entry_choice(self, min = None, max = None):
        try:
            user_choice = int(input())

            if min and user_choice < min:
                return None

            if max and user_choice > max:
                return None

            return user_choice
        except ValueError:
            self.log(self.T.t("Invalid choice"))
            time.sleep(1)
            return None

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
                self.log(choice)

            while (user_choice := self.__get_user_entry_choice(min=1, max=9)) is None:
                continue

            self.__choices(user_choice)

    def __choices(self, x):
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

            instance = self.method_instances.get(methods[x - 1])
            while self.__change_defaults_or_start(instance) is not None:
                continue

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
            raise NotImplementedError

    def __change_defaults_or_start(self, method):
        self.log("1. " + self.T.t("Change default values of parameters"))
        self.log("2. Start")

        while (user_choice := self.__get_user_entry_choice(min=1, max=2)) is None:
            continue

        match user_choice:
            case 1:
                self.__parameter_choices(method)
                return None
            case 2:
                return None
            case _:
                raise NotImplementedError

    def __print_parameter_choices(self, method: BaseMethod) -> list[ParamDef]:
        """
        :return: A list of possible parameter choices
        """
        params = method.get_parameters()
        param_choices = []

        def __add_entry(param: ParamDef):
            nonlocal param_choices

            self.log(f"{len(param_choices) + 1}. {param.get_name()} - {param.get_value()}")
            param_choices.append(param)

        for p in params:
            if p.get_ptype() == ParamValueTypes.LIST_SINGLE:
                self.log(p.get_name())

                for pp in p.get_value():
                    __add_entry(pp)

            else:
                __add_entry(p)

        return param_choices

    def __parameter_choices(self, method: BaseMethod):
        while True:
            param_choices = self.__print_parameter_choices(method)
            i = len(param_choices)

            self.log(f"{(i := i + 1)}. " + self.T.t("Start"))

            while (user_choice := self.__get_user_entry_choice(min=1, max=i)) is None:
                continue

            if 1 <= user_choice <= len(param_choices):
                self.__change_param(param_choices[user_choice - 1])
            elif user_choice == i:
                return None
            else:
                raise NotImplementedError

    def __change_param(self, param: ParamDef):
        self.log(self.T.t("Type - ") + param.get_ptype().name)
        self.log(self.T.t("Default value - ") + str(param.get_default()))
        if not param.get_ptype() == ParamValueTypes.BOOLEAN:
            self.log(self.T.t("Minimum value - ") + param.get_min_value())
            self.log(self.T.t("Maximum value - ") + param.get_max_value())

        self.log(self.T.t("New value: "))
        user_choice = input()

        try:
            param.set_value(user_choice)
        except ValueError:
            self.log(self.T.t("Invalid choice"))


@UIRegistrator.register_class
class GUI(UI):
    def _print_to_diagnostic(self, message):
        pass

    def log(self, message):
        self._print_to_diagnostic(message)

    def start(self):
        pass
