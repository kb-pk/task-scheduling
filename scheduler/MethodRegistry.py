class MethodRegistry:
    __registry = {}

    @classmethod
    def add_to_registry(cls, method_class):
        cls.__registry[method_class.__name__] = method_class

    @classmethod
    def get_registry(cls):
        return cls.__registry

class MethodRegistrator:
    @staticmethod
    def register_method(method):
        MethodRegistry.add_to_registry(method)