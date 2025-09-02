from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Callable, List, Type

from enum import Enum

_CASTERS: Dict[str, Callable[[Any], Any]] = {
    "int": int,
    "float": float,
    "bool": lambda v: v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "t", "yes", "y", "on")
}

class ParamValueTypes(Enum):
    """
    Permitted values of ParamDef
    """
    INT = 0,
    FLOAT = 1,
    BOOLEAN = 2
    LIST_SINGLE = 3


class ParamDef:
    _CASTERS: Dict[ParamValueTypes, Callable[[Any], Any]] = {
        ParamValueTypes.INT: int,
        ParamValueTypes.FLOAT: float,
        ParamValueTypes.BOOLEAN: lambda v: v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "t",
                                                                                                    "yes", "y", "on"),
        ParamValueTypes.LIST_SINGLE: lambda v: v if isinstance(v, list) and
                                                    len(v) > 0 and
                                                    isinstance(v[0], ParamDef) else []
    }

    def __init__(self,
                 name: str,
                 ptype: ParamValueTypes,
                 default: _CASTERS[ParamValueTypes],
                 description: str,
                 min_value: _CASTERS[ParamValueTypes] = None, max_value: _CASTERS[ParamValueTypes] = None,
                 validator: Validator = None):
        self._name = name
        self._ptype = ptype
        self._default = self._CASTERS[ptype](default)
        self._description = description
        self._min_value = min_value
        self._max_value = max_value
        self._validator = validator

        self._value = self._ensure_within_bounds(default)

    def _ensure_within_bounds(self, value):
        if self._max_value is not None and value > self._max_value:
            raise ValueError("Value bigger than max")

        if self._min_value is not None and value < self._min_value:
            raise ValueError("Value smaller than min")

        return value

    def _cast(self, value):
        return self._CASTERS[self._ptype](value)

    def get_name(self):
        return self._name

    def get_ptype(self):
        return self._ptype

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

        casted = self._ensure_within_bounds(casted)

        if self._validator is not None:
            self._validator.validate(casted)

        self._value = casted

class InfluenceGroupInstantiator:
    """
    For params that should influence each other (like ones where only one can be switched on at a time).
    It's just a wrapper at instantiation - it returns the ParamDef's that are passed into it, but properly instantiated

    This is to prevent the client from messing with _* (quote-unquote "private") variables
    """
    @staticmethod
    def set(param_defs: List[ParamDef], validator: Type[InfluenceGroupValidator]):
        for inx, param in enumerate(param_defs):
            influence_group = param_defs.copy()
            # remove the param itself from its influence group
            influence_group.pop(inx)

            v = validator(influence_group)
            param._validator = v

            # to prevent accidentally setting bad defaults
            v.validate(param.get_value())

        return param_defs


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


class InfluenceGroupValidator(Validator, ABC):
    def __init__(self, influence_group: List[ParamDef]):
        super().__init__()
        self.influence_group = influence_group


class PittPermCrossoverValidator(InfluenceGroupValidator):
    def validate(self, value):
        if not self.influence_group:
            raise ValueError(self.message + "influence group is empty")

        # conflicts only arise when two or more methods are active
        if not value:
            return

        for param in self.influence_group:
            if param.get_value() == value:
                raise ValueError("Can't set more than one crossover method")