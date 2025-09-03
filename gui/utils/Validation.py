"""
Parameter validation utilities for GUI components.
"""
from typing import Optional, Tuple, Any
from scheduler.Parameters import ParamDef, ParamValueTypes
from .CommonInterfaces import ParameterValidator
from ..config import ValidationMessages


class DefaultParameterValidator:
    """Default implementation of parameter validation."""
    
    def validate_parameter(self, param_def: ParamDef, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a parameter value against its definition.
        
        Args:
            param_def: Parameter definition containing validation rules
            value: String value from UI widget
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ptype = param_def.get_ptype()
            
            if ptype == ParamValueTypes.BOOLEAN:
                return self._validate_boolean(value)
            elif ptype == ParamValueTypes.INT:
                return self._validate_integer(param_def, value)
            elif ptype == ParamValueTypes.FLOAT:
                return self._validate_float(param_def, value)
            else:
                # For other types, just try to set the value
                param_def.set_value(value)
                return True, None
                
        except Exception as e:
            return False, str(e)
    
    def _validate_boolean(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate boolean parameter."""
        if value.lower() not in ('true', 'false'):
            return False, "Boolean value must be 'true' or 'false'"
        return True, None
    
    def _validate_integer(self, param_def: ParamDef, value: str) -> Tuple[bool, Optional[str]]:
        """Validate integer parameter."""
        try:
            int_value = int(value)
        except ValueError:
            return False, "Value must be an integer"
        
        min_val = param_def.get_min_value()
        max_val = param_def.get_max_value()
        
        if min_val is not None and int_value < min_val:
            return False, f"Value must be >= {min_val}"
        
        if max_val is not None and int_value > max_val:
            return False, f"Value must be <= {max_val}"
        
        return True, None
    
    def _validate_float(self, param_def: ParamDef, value: str) -> Tuple[bool, Optional[str]]:
        """Validate float parameter."""
        try:
            float_value = float(value)
        except ValueError:
            return False, "Value must be a number"
        
        min_val = param_def.get_min_value()
        max_val = param_def.get_max_value()
        
        if min_val is not None and float_value < min_val:
            return False, f"Value must be >= {min_val}"
        
        if max_val is not None and float_value > max_val:
            return False, f"Value must be <= {max_val}"
        
        return True, None


class ParameterApplier:
    """Applies validated parameters to method instances."""
    
    def __init__(self, validator: ParameterValidator):
        self.validator = validator
    
    def apply_parameters_to_method(self, method: Any, param_controls: dict, 
                                 list_single_groups: list, state: Any) -> list[str]:
        """
        Apply UI parameter values to method instance.
        
        Args:
            method: Method instance to configure
            param_controls: Dictionary of parameter controls
            list_single_groups: List of single-selection parameter groups
            state: Program state for stop criterion
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Apply regular parameters
        for key, ctrl in param_controls.items():
            spec = ctrl["spec"]
            var = ctrl["var"]
            value = var.get()
            
            # Validate before applying
            is_valid, error_msg = self.validator.validate_parameter(spec, value)
            if not is_valid:
                warnings.append(ValidationMessages.INVALID_VALUE.format(
                    param=key, error=error_msg
                ))
                continue
            
            try:
                spec.set_value(value)
            except Exception as e:
                warnings.append(ValidationMessages.INVALID_VALUE.format(
                    param=key, error=str(e)
                ))
        
        # Apply stop criterion if present
        if list_single_groups:
            try:
                selected_index = list_single_groups[0]["var"].get()
                state.stop_criterion.set(state.stop_criterion.State(selected_index))
            except Exception as e:
                warnings.append(ValidationMessages.STOP_CRITERION_ERROR.format(
                    error=str(e)
                ))
        
        return warnings
