from typing import Callable, Type

from scheduler.ProgramState import ProgramState

class Logger:
    def __init__(self, state: ProgramState, ui_log: Callable[[str], None]):
        self.__state = state
        self.__ui_log = ui_log

    def __log(self, message: str):
        self.__ui_log(message)

    def __get_scheduling_mode(self):
        return self.__state.scheduling.get().name

    def __get_output_mode(self):
        return self.__state.output.get().name

    def better_solution_found(self, value, epoch):
        message = f"Better {self.__get_scheduling_mode()} found in epoch {epoch}, {self.__get_output_mode()} - {value}"
        self.__log(message)

    def initial_solution(self, value):
        message = f"Initial {self.__get_output_mode()} - {value}"
        self.__log(message)

    def error_invalid_parameter_ui(self, value):
        message = f"Invalid parameter for ui passed, defaulting to {value}"
        self.__log(message)

    def error_no_parameter_ui(self, value):
        message = f"No parameter for ui passed, defaulting to {value}"
        self.__log(message)