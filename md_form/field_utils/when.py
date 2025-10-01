from typing import Any, Dict


class When:
    def __init__(self, property: str, condition_type: str, value: Any):
        self.property = property
        self.condition_type = condition_type
        self.value = value

    @classmethod
    def equals(cls, property: str, value: Any):
        return cls(property, "equals", value)

    @classmethod
    def not_equals(cls, property: str, value: Any):
        return cls(property, "not_equals", value)

    @classmethod
    def is_present(cls, property: str):
        return cls(property, "is_present", True)

    def as_dict(self) -> Dict[str, Any]:
        return {"property": self.property, self.condition_type: self.value}