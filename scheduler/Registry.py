from abc import abstractmethod, ABC
from typing import Type, Dict

class Registry(ABC):
    @classmethod
    def add_to_registry(cls, registered_class):
        cls.get_registry()[registered_class.__name__] = registered_class

    @classmethod
    @abstractmethod
    def get_registry(cls):
        pass


class Registrator(ABC):
    @classmethod
    @abstractmethod
    def get_registry_class(cls) -> Type[Registry]:
        pass

    @classmethod
    def register_class(cls, c):
        cls.get_registry_class().add_to_registry(c)
        return c  # Return the class to make it work as a decorator


class UIRegistry(Registry):
    __registry = {}

    @classmethod
    def get_registry(cls):
        return cls.__registry


class UIRegistrator(Registrator):
    @classmethod
    def get_registry_class(cls) -> Type[Registry]:
        return UIRegistry


class MethodRegistry(Registry):
    __registry = {}

    @classmethod
    def get_registry(cls):
        return cls.__registry


class MethodRegistrator(Registrator):
    @classmethod
    def get_registry_class(cls) -> Type[Registry]:
        return MethodRegistry