from typing import Any, Dict, List, Union


def evaluate_when(when_dict: Dict[str, Any], data: Dict[str, Any]) -> bool:
    if "operator" in when_dict:
        conditions = when_dict.get("conditions", [])
        if when_dict["operator"] == "and":
            return all(evaluate_when(c, data) for c in conditions)
        if when_dict["operator"] == "or":
            return any(evaluate_when(c, data) for c in conditions)
        return False

    prop = when_dict.get("property")
    value = data.get(prop)

    if "equals" in when_dict:
        return value == when_dict["equals"]
    if "not_equals" in when_dict:
        return value != when_dict["not_equals"]
    if "is_present" in when_dict:
        return value is not None

    return False


class When:
    def __init__(self, property_name: str = None, condition_type: str = None, value: Any = None, 
                 operator: str = None, conditions: List['When'] = None):
        self.property = property_name
        self.condition_type = condition_type
        self.value = value
        self.operator = operator
        self.conditions = conditions or []

    @classmethod
    def equals(cls, property_name: str, value: Any):
        return cls(property_name, "equals", value)

    @classmethod
    def not_equals(cls, property_name: str, value: Any):
        return cls(property_name, "not_equals", value)

    @classmethod
    def is_present(cls, property_name: str):
        return cls(property_name, "is_present", True)

    @classmethod
    def all_of(cls, *conditions: 'When'):
        """Create a When condition that requires ALL conditions to be true (AND operator)"""
        return cls(operator="and", conditions=list(conditions))

    @classmethod
    def any_of(cls, *conditions: 'When'):
        """Create a When condition that requires ANY condition to be true (OR operator)"""
        return cls(operator="or", conditions=list(conditions))

    def evaluate(self, data: Dict[str, Any]) -> bool:
        return evaluate_when(self.as_dict(), data)

    def as_dict(self) -> Dict[str, Any]:
        # If this is a compound condition (has operator)
        if self.operator is not None:
            return {
                "operator": self.operator,
                "conditions": [condition.as_dict() for condition in self.conditions]
            }
        # If this is a simple condition
        else:
            return {"property": self.property, self.condition_type: self.value}