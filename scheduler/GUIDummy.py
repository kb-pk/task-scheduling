from typing import Type

from scheduler.methods.BaseMethod import BaseMethod


class GUIDummy:
    def __init__(self, method_instances: list[Type[BaseMethod]]):
        pass

    def print_to_diagnostic(self):
        pass