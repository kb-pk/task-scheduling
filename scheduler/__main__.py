from sys import argv

import scheduler.Common as Common
from scheduler.MethodCache import MethodCache
from scheduler.Logger import Logger
from scheduler.Registry import MethodRegistry
from scheduler.ProgramState import ProgramState
from scheduler.Registry import UIRegistry
from scheduler.UI import UI
from lang.Lang import T as T

#### ------------ DO NOT DELETE THESE IMPORTS!! ------------ ####
## PyCharm marks them as unused imports, but if
## they're deleted, Python won't parse the files with methods' classes,
## and they won't be registered in MethodRegistry!
from scheduler.methods.Michigan import MichiganMethod
from scheduler.methods.Pitt_direct import PittDirectMethod
from scheduler.methods.Pitt_perm import PittPermMethod
from scheduler.methods.Dragonfly import DragonflyMethod
from scheduler.methods.Fruitfly import FruitflyMethod


class Main:
    def __init__(self):
        self.__state: ProgramState = ProgramState()
        self.T = T(self.__state)
        self.__logger: Logger = Logger(self.__state, self.__log)

        # intialize registered methods with current state
        self.__methods = {}
        # init with same cache
        cache = MethodCache()
        for name, method in MethodRegistry.get_registry().items():
            self.__methods[name] = method(self.__state, self.__logger, self.T, cache)

        self.__ui: UI = self._spawn_interface()

    def __log(self, message: str):
        self.__ui.log(message)

    def _set_interface(self):
        # tmp logger since we don't have an "UI" yet, yeah hacky
        l = Logger(self.__state, print)

        try:
            ui = argv[1]
            self.__state.ui.set(ui)
        # fallback to default
        except IndexError:
            l.error_no_parameter_ui(self.__state.ui.get().name)
        except KeyError:
            l.error_invalid_parameter_ui(self.__state.ui.get().name)

    def _spawn_interface(self):
        self._set_interface()
        ui = UIRegistry.get_registry().get(self.__state.ui.get().name)

        return ui(self.__state, self.T, self.__methods)

    def main(self):
        self.__ui.start()

if __name__ == "__main__":
    Main().main()
