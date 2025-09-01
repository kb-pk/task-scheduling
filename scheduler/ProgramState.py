from enum import Enum

class ProgramState:
    class __SchedulingState:
        class State(Enum):
            makespan = 0
            energy = 1

        def __init__(self):
            self.__current_state = self.State.makespan

        def get(self):
            return self.__current_state

        def set(self, value: State):
            if not self.State.__contains__(value):
                raise ValueError("Invalid enum value")

            self.__current_state = self.State(value)

    class __OutputState:
        class State(Enum):
            makespan = 0
            energy = 1
            all = 2

        def __init__(self):
            self.__current_state = self.State.makespan

        def get(self):
            return self.__current_state

        def set(self, value: State):
            if not self.State.__contains__(value):
                raise ValueError("Invalid enum value")

            self.__current_state = self.State(value)

    class __UserInterfaceState:
        class State(Enum):
            CLI = 0
            GUI = 1

        def __init__(self):
            self.__current_state = self.State.CLI

        def get(self):
            return self.__current_state

        def set(self, name: str):
            try:
                new_state = self.State[name]
                self.__current_state = new_state
            except KeyError as e:
                # propagate upwards
                raise e

    class __LangState:
        class State(Enum):
            pl_PL = 0
            en_GB = 1

        def __init__(self):
            self.__current_state = self.State.en_GB

        def get(self):
            return self.__current_state

        def set(self, value: State):
            if not self.State.__contains__(value):
                raise ValueError("Invalid enum value")

            self.__current_state = value

    def __init__(self):
        self.scheduling = self.__SchedulingState()
        self.output = self.__OutputState()
        self.ui = self.__UserInterfaceState()
        self.lang = self.__LangState()

