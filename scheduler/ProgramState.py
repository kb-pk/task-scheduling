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

            self.__current_state = value

    class __OutputState:
        class State(Enum):
            makespan = 0
            energy = 1
            all = 2

        def __init__(self):
            self.__current_state = self.State.makespan

        def get(self):
            return self.__current_state

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

    scheduling = __SchedulingState()
    output = __OutputState()
    lang = __LangState()
