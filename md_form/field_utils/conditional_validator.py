from pydantic import model_validator
from .when import evaluate_when


class ConditionalRequiredMixin:
    @model_validator(mode="before")
    @classmethod
    def validate_conditional_required(cls, data):
        if not isinstance(data, dict):
            return data

        for field_name, field_info in cls.model_fields.items():
            extra = field_info.json_schema_extra or {}
            rules = extra.get("rules", [])
            when = extra.get("when")

            if not when:
                continue

            if isinstance(rules, dict):
                rules = [rules]

            has_required = any(r.get("name") == "is_required" for r in rules)

            if has_required and evaluate_when(when, data):
                value = data.get(field_name)
                if value is None:
                    msg = f"'{field_name}' is required"
                    raise ValueError(msg)

        return data
