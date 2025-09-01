from scheduler.ProgramState import ProgramState


class Logger:
    def __init__(self, state: ProgramState):
        self.__state = state

    def __get_scheduling_mode(self):
        return self.__state.scheduling.get().name

    def __log(self, message: str):
        print(message)
        # TODO

    def better_solution_found(self, value, epoch):
        message = f"Better {self.__get_scheduling_mode()} found in epoch {epoch} - {value}"
        self.__log(message)

    def initial_solution(self, value):
        message = f"Initial {self.__get_scheduling_mode()} - {value}"
        self.__log(message)