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


def _normalize_options_arg(options: Union[List[str], Dict[str, Any]]) -> Any:
    """Normalize a select-field `options` argument.

    Flat string list -> list of {name, value} dicts.
    Dynamic-options dict ({ref, cases}) -> same dict with each cases[key]
    (must be List[str]) wrapped into {name, value} dicts.

    Raises ValueError if the dict is structurally invalid (missing `cases`,
    non-list `cases` value, list element that isn't a string).
    """
    if isinstance(options, list):
        return [{"name": opt, "value": opt} for opt in options]

    if "cases" not in options or not isinstance(options["cases"], dict):
        raise ValueError(
            "Dynamic options must include a 'cases' dict"
        )

    normalized_cases: Dict[str, Any] = {}
    for case_key, case_value in options["cases"].items():
        if not isinstance(case_value, list) or not all(
            isinstance(item, str) for item in case_value
        ):
            raise ValueError(
                f"cases[{case_key!r}] must be a list of strings; "
                "pre-shaped or mixed lists are not accepted at the helper level"
            )
        normalized_cases[case_key] = [
            {"name": item, "value": item} for item in case_value
        ]

    return {**options, "cases": normalized_cases}


@field_builder(FieldType.STRING)
@typechecked
def select_field(
    default: Optional[str] = None,
    options: Optional[Union[List[str], Dict[str, Any]]] = None,
    discriminator: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a select field with options."""
    result = {}

    if default is not None:
        result["json_schema_extra"] = {"default": default}

    if discriminator is not None:
        result["discriminator"] = discriminator

    if options is not None:
        normalized_options = _normalize_options_arg(options)
        if "json_schema_extra" not in result:
            result["json_schema_extra"] = {}
        result["json_schema_extra"]["parameters"] = {"options": normalized_options}

    return result


@field_builder(FieldType.MULTIPLE)
@typechecked
def multiple_select_field(
    default: Optional[List[str]] = None,
    options: Optional[Union[List[str], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Create a multiple select field that allows selecting multiple values."""
    result = {}

    if default is not None:
        result["json_schema_extra"] = {"default": default}

    if options is not None:
        normalized_options = _normalize_options_arg(options)
        if "json_schema_extra" not in result:
            result["json_schema_extra"] = {}
        result["json_schema_extra"]["parameters"] = {"options": normalized_options}

    return result


@field_builder(FieldType.EXPERIMENT_DESIGN)
def experiment_design_field() -> Dict[str, Any]:
    """Create an experiment design field."""
    return {
        "json_schema_extra": {
            "name": "Sample Metadata",
            "parameters": {
                "datasetsSearch": {"ref": "input_datasets"},
                "columnNames": {"ref": ["condition_column", "control_variables[].column"]}
            }
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

@field_builder(FieldType.CONDITION_COLUMN_MULTI_SELECT)
def condition_column_multi_select_field() -> Dict[str, Any]:
    """Create a condition column multi select field."""
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
                "experimentDesign": {"ref": "experiment_design"},
                "conditionColumn": {"ref": "condition_column"}
            }
        }
    }


@field_builder(FieldType.CONTROL_VARIABLES)
@typechecked
def control_variables_field(
    default: Optional[str] = None,
    radioOptions: List[str] = ["categorical", "numerical"],
) -> Dict[str, Any]:
    """Create a control variables field."""
    result = {}
    
    if default is not None:
        result["json_schema_extra"] = {"default": default}
    
    if "json_schema_extra" not in result:
        result["json_schema_extra"] = {}
    
    result["json_schema_extra"]["parameters"] = {
        "radioOptions": radioOptions,
        "datasetsSearch": { "ref": "input_datasets" },
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


@field_builder(FieldType.SAMPLE_METADATA_VALUE)
def sample_metadata_value_field(
    column_ref: str = "filter_based_on_condition",
) -> Dict[str, Any]:
    """Pick a single value from a sample metadata column.

    The frontend uses `column_ref` to know which field holds the
    selected column name, then dynamically populates the value list
    from the experiment design table.
    """
    return {
        "json_schema_extra": {
            "parameters": {
                "datasetsSearch": {"ref": "input_datasets"},
                "columnName": {"ref": column_ref},
            }
        }
    }