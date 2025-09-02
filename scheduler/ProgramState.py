from enum import Enum

class ProgramState:
    """
    A class encompassing the mutable state of the program
    """

    class __SchedulingState:
        """
        Which value the program is currently optimising for - which fitness function it uses
        """
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

    class __OutputState(__SchedulingState):
        """
        Which value the program presents to the user.

        Useful for seeing how other scheduling values change in time when evolving
        """
        pass

    class __StopCriterionState:
        """
        Which stop criterion the program uses to halt the evolution
        """
        class State(Enum):
            iterations = 0
            fitness_function_value = 1

        def __init__(self):
            self.__current_state = self.State.iterations

        def get(self):
            return self.__current_state

        def set(self, value: State):
            if not self.State.__contains__(value):
                raise ValueError("Invalid enum value")

            self.__current_state = self.State(value)

    class __SecurityFeaturesState:
        class State(Enum):
            ON = 0
            OFF = 1

        def __init__(self):
            self.__current_state = self.State.OFF

        def get(self):
            return self.__current_state

        def set(self, value: State):
            if not self.State.__contains__(value):
                raise ValueError("Invalid enum value")

            self.__current_state = self.State(value)

    class __UserInterfaceState:
        """
        Which UI the program presents to the user
        """
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
        """
        What language is used to communicate with the user
        """
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
        self.stop_criterion = self.__StopCriterionState()
        self.security_features = self.__SecurityFeaturesState()
        self.ui = self.__UserInterfaceState()
        self.lang = self.__LangState()

