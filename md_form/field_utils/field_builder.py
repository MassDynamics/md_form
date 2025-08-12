from typing import Any, Callable, Optional, Dict, Union, List
from pydantic import Field
from functools import wraps
from .field_types import FieldType
from .when import When
from typeguard import typechecked
from .rules import Rule


@typechecked
def field_builder(field_type: FieldType) -> Callable[[Callable], Callable]:
    """
    Decorator that handles common field parameters automatically.
    
    Args:
        field_type: The type of field to create
    """
    def decorator(func: Callable[..., Dict[str, Any]]) -> Callable[..., Field]:
        @wraps(func)
        @typechecked
        def wrapper(
            name: Optional[str] = None,
            description: Optional[str] = None,
            when: Optional[When] = None,
            rules: Optional[Union[Rule, List[Rule]]] = None,
            **kwargs: Any
        ) -> Field:
            # Build json_schema_extra with common parameters
            json_schema_extra: Dict[str, Any] = {
                "field_type": field_type,
            }
            
            if name is not None:
                json_schema_extra["name"] = name
            if description is not None:
                json_schema_extra["description"] = description
            if when is not None:
                json_schema_extra["when"] = when.as_dict()
            
            # Handle validation rules
            if rules is not None:

                if isinstance(rules, list):
                    json_schema_extra["rules"] = [rule.as_dict() for rule in rules]
                    has_required = any(rule.as_dict().get("name") == "is_required" for rule in rules)
                else:
                    json_schema_extra["rules"] = rules.as_dict()
                    has_required = rules.as_dict().get("name") == "is_required"

            else:
                has_required = False
            
            # Call the original function to get field-specific parameters
            field_params: Dict[str, Any] = func(**kwargs)
            
            # Merge field-specific parameters into json_schema_extra
            if "json_schema_extra" in field_params:
                json_schema_extra.update(field_params["json_schema_extra"])
            
            # Build Field kwargs
            field_kwargs: Dict[str, Any] = {"json_schema_extra": json_schema_extra}
            
            # Add default=None if is_required is not in rules so the field is optional
            if not has_required:
                field_kwargs["default"] = None
            
            # Add any non-json_schema_extra parameters (like discriminator)
            for key, value in field_params.items():
                if key != "json_schema_extra":
                    field_kwargs[key] = value
            
            return Field(**field_kwargs)
        
        return wrapper
    return decorator 