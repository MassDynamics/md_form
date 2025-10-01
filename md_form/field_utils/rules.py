from typing import Any, Dict, Union, Literal, Optional

class Rule:
    """Base class for validation rules"""
    def as_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

class EqualsToValueRule(Rule):
    """Validation rule for when a field value should equal/not equal a specific value"""
    def __init__(self, rule_name: str, value: Any):
        self.rule_name = rule_name
        self.value = value
    
    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.rule_name,
            "parameters": {
                "value": self.value
            }
        }

class EqualsToFieldRule(Rule):
    """Validation rule for when a field value should equal/not equal another field's value"""
    def __init__(self, rule_name: str, field: str, values: Optional[str] = None):
        self.rule_name = rule_name
        self.field = field
        self.values = values
    
    def as_dict(self) -> Dict[str, Any]:
        parameters = {"field": self.field}
        if self.values is not None:
            parameters["values"] = self.values
        return {
            "name": self.rule_name,
            "parameters": parameters
        }

class RequiredRule(Rule):
    """Validation rule for when a field is required"""
    def __init__(self, rule_name: str):
        self.rule_name = rule_name
    
    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.rule_name
        }
class ColumnValidationRule(Rule):
    """Base class for column validation rules"""
    def __init__(self, rule_name: str, column: str):
        self.rule_name = rule_name
        self.column = column
    
    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.rule_name,
            "parameters": {
                "column": self.column
            }
        }

class ColumnFromFieldValidationRule(Rule):
    """Base class for column validation rules that reference a field"""
    def __init__(self, rule_name: str, values: str, field: Optional[str] = None):
        self.rule_name = rule_name
        self.field = field
        self.values = values
    
    def as_dict(self) -> Dict[str, Any]:
        parameters = {"values": self.values}
        if self.field is not None:
            parameters["field"] = self.field
        return {
            "name": self.rule_name,
            "parameters": parameters
        } 