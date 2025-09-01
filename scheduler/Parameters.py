from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Callable

from enum import Enum

_CASTERS: Dict[str, Callable[[Any], Any]] = {
    "int": int,
    "float": float,
    "bool": lambda v: v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "t", "yes", "y", "on")
}

class ParamValueTypes(Enum):
    INT = 0,
    FLOAT = 1,
    BOOLEAN = 2


class ParamDef2:
    _CASTERS: Dict[ParamValueTypes, Callable[[Any], Any]] = {
        ParamValueTypes.INT: int,
        ParamValueTypes.FLOAT: float,
        ParamValueTypes.BOOLEAN: lambda v: v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "t",
                                                                                                    "yes", "y", "on")
    }

    def __init__(self,
                 name: str,
                 ptype: ParamValueTypes,
                 default: _CASTERS[ParamValueTypes],
                 description: str,
                 min_value: _CASTERS[ParamValueTypes] = None, max_value: _CASTERS[ParamValueTypes] = None,
                 validator: Validator = None,
                 _value_observer: Callable[[None], None] = None):
        self._name = name
        self._ptype = ptype
        self._default = self._CASTERS[ptype](default)
        self._description = description
        self._min_value = min_value
        self._max_value = max_value
        self._validator = validator

        self._value = default

    def _cast(self, value):
        return self._CASTERS[self.ptype](value)

    def get_name(self):
        return self._name

    def get_description(self):
        return self._description

    def get_default(self):
        return self._default

    def get_min_value(self):
        return self._min_value

    def get_max_value(self):
        return self._max_value

    def get_value(self):
        return self._value

    def set_value(self, new_value):
        casted = self._cast(new_value)

        if self._max_value < casted < self._min_value:
            raise ValueError("Value not withing min/max bounds")

        if self._validator is not None:
            self._validator.validate(casted)

        self._value = casted


class Validator(ABC):
    def __init__(self):
        self.message = "Validator check failed - "

    @abstractmethod
    def validate(self, value):
        raise NotImplementedError()


class PopulationValidator(Validator):
    def validate(self, value):
        if value % 2 != 0:
            raise ValueError(self.message + "population number must be even")


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