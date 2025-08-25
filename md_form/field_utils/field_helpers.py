from typing import Any, Dict, List, Optional, Union
from .field_types import FieldType
from .field_builder import field_builder
from typeguard import typechecked

@field_builder(FieldType.BOOLEAN)
@typechecked
def boolean_field(
    default: Optional[bool] = None,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a boolean field."""
    result = {}
    
    if default is not None:
        result["json_schema_extra"] = {"default": default}
    
    if label is not None:
        if "json_schema_extra" not in result:
            result["json_schema_extra"] = {}
        result["json_schema_extra"]["parameters"] = {"label": label}
    
    return result

@field_builder(FieldType.STRING)
@typechecked
def string_field(
    default: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a string field."""
    result = {}
    
    if default is not None:
        result["json_schema_extra"] = {"default": default}
    
    return result

@field_builder(FieldType.NUMBER)
@typechecked
def number_field(
    default: Optional[Union[int, float]] = None,
    ge: Optional[Union[int, float]] = None,
    le: Optional[Union[int, float]] = None,
) -> Dict[str, Any]:
    """Create a number field."""
    result = {}
    
    if default is not None:
        result["json_schema_extra"] = {"default": default}
    
    if ge is not None:
        result["ge"] = ge
    
    if le is not None:
        result["le"] = le
    
    return result


@field_builder(FieldType.STRING)
@typechecked
def select_field(
    default: Optional[str] = None,
    options: Optional[List[str]] = None,
    discriminator: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a select field with options."""
    result = {}
    
    if default is not None:
        result["json_schema_extra"] = {"default": default}
    
    if discriminator is not None:
        result["discriminator"] = discriminator
    
    if options is not None:
        options_dict = [{"name": opt, "value": opt} for opt in options]
        if "json_schema_extra" not in result:
            result["json_schema_extra"] = {}
        result["json_schema_extra"]["parameters"] = {"options": options_dict}
    
    return result


@field_builder(FieldType.EXPERIMENT_DESIGN)
def experiment_design_field() -> Dict[str, Any]:
    """Create an experiment design field."""
    return {
        "json_schema_extra": {
            "name": "Experiment Design",
        }
    }


@field_builder(FieldType.CONDITION_COLUMN)
def condition_column_field() -> Dict[str, Any]:
    """Create a condition column field."""
    return {
        "json_schema_extra": {
            "parameters": {
                "datasetsSearch": {"ref": "input_datasets"}
            }
        }
    }


@field_builder(FieldType.CONDITION_COMPARISONS)
def condition_comparisons_field() -> Dict[str, Any]:
    """Create a condition comparisons field."""
    return {
        "json_schema_extra": {
            "parameters": {
                "experimentDesigns": {"ref": "experiment_design"},
                "conditionColumn": {"ref": "condition_column"}
            }
        }
    }


@field_builder(FieldType.CONTROL_VARIABLES)
@typechecked
def control_variables_field(
    default: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a control variables field."""
    result = {}
    
    if default is not None:
        result["json_schema_extra"] = {"default": default}
    
    if "json_schema_extra" not in result:
        result["json_schema_extra"] = {}
    
    result["json_schema_extra"]["parameters"] = {
        "radioOptions": ["categorical", "numerical"]
    }
    
    return result


@field_builder(FieldType.NUMBER_RANGE)
@typechecked
def numberrange_field(
    default: Optional[float] = None,
    ge: Optional[float] = None,
    le: Optional[float] = None,
    interval: Optional[float] = None,
) -> Dict[str, Any]:
    """Create a number range field."""
    result = {}
    if default is not None:
        result["json_schema_extra"] = {"default": default}
    if ge is not None:
        result["ge"] = ge
    if le is not None:
        result["le"] = le
    if interval is not None:
        if "json_schema_extra" not in result:
            result["json_schema_extra"] = {}
        result["json_schema_extra"]["parameters"] = {"interval": interval}
    return result

@field_builder(FieldType.INTENSITY_INPUT_DATASET)
@typechecked
def intensity_input_dataset_field() -> Dict[str, Any]:
    """Create an intensity input dataset field."""
    return {
        "json_schema_extra": {
            "name": "Select Intensity dataset",
            "parameters": {
                "type": "INTENSITY",
                "multiple": False
            },
        }
    }

@field_builder(FieldType.ENTITY_TYPE)
@typechecked
def entity_type_field(
    default: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an entity type field."""
    result = {
        "json_schema_extra": {
            "parameters": {
                "datasetsSearch": {"ref": "input_datasets"}
            }
        }
    }
    
    if default is not None:
        result["json_schema_extra"]["default"] = default

    return result
