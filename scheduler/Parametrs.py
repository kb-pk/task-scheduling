from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Optional, Type, Dict, Callable
from .methods.BaseMethod import BaseMethod
import inspect

_CASTERS: Dict[str, Callable[[Any], Any]] = {
    "int": int,
    "float": float,
    "bool": lambda v: v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "t", "yes", "y", "on")
}

@dataclass
class ParamDef:
    name: str
    ptype: str
    default: Any
    description: str = ""
    min_value: float | None = None
    max_value: float | None = None

    def cast(self, raw: Any) -> Any:
        if raw is None:
            return self.default
        caster = _CASTERS.get(self.ptype, lambda x: x)
        try:
            val = caster(raw)
        except Exception as e:
            raise ValueError(f"Parameter '{self.name}': cannot cast value '{raw}' to {self.ptype} ({e})") from e

        if isinstance(val, (int, float)):
            if self.min_value is not None and val < self.min_value:
                raise ValueError(f"Parameter '{self.name}' is below minimum {self.min_value} (got {val})")
            if self.max_value is not None and val > self.max_value:
                raise ValueError(f"Parameter '{self.name}' is above maximum {self.max_value} (got {val})")
        return val

def _signature_param_names(method_cls: Type[BaseMethod]) -> set[str]:
    try:
        sig = inspect.signature(method_cls.__init__)
    except (ValueError, TypeError):
        return set()
    names = set()
    for n, p in sig.parameters.items():
        if n == "self":
            continue
        names.add(n)
    return names

def instantiate_method(method_cls: Type[BaseMethod], values_list: Optional[List[Any]] = None) -> BaseMethod:
    if not hasattr(method_cls, "PARAM_DEFS"):
        raise ValueError(f"{method_cls.__name__} missing PARAM_DEFS attribute")

    specs: List[ParamDef] = getattr(method_cls, "PARAM_DEFS")
    if not isinstance(specs, list) or any(not isinstance(s, ParamDef) for s in specs):
        raise ValueError(f"{method_cls.__name__}.PARAM_DEFS must be a list[ParamDef]")

    if values_list is None:
        values_list = [s.default for s in specs]

    if len(values_list) != len(specs):
        expected = [(s.name, s.default) for s in specs]
        raise ValueError(
            f"Parameter count mismatch: provided {len(values_list)} vs expected {len(specs)}. "
            f"Expected order: {expected}"
        )

    kwargs: Dict[str, Any] = {}
    for spec, raw in zip(specs, values_list):
        try:
            kwargs[spec.name] = spec.cast(raw)
        except ValueError as e:
            # Re-raise with context preserved
            raise ValueError(f"Error casting parameter '{spec.name}': {e}") from e

    ctor_params = _signature_param_names(method_cls)
    unknown = set(kwargs.keys()) - ctor_params
    if unknown:
        pass

    try:
        return method_cls(**kwargs)
    except TypeError as e:
        raise ValueError(
            f"Failed to instantiate {method_cls.__name__} with kwargs {kwargs}. "
            f"TypeError: {e}"
        ) from e
    except Exception as e:
        raise ValueError(
            f"Unexpected error while instantiating {method_cls.__name__}: {e}"
        ) from e

def get_method_param_defs(method_cls: Type[BaseMethod]) -> List[ParamDef]:
    defs = getattr(method_cls, "PARAM_DEFS", [])
    return defs if isinstance(defs, list) else []

_METHOD_REGISTRY: Dict[str, Type[BaseMethod]] = {}

def register_method(method_cls: Type[BaseMethod]):
    try:
        name = method_cls.get_method_name(method_cls)
    except Exception:
        name = method_cls.__name__.lower()
    _METHOD_REGISTRY[name] = method_cls
    return method_cls