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

@field_builder(FieldType.INTENSITY_INPUT_DATASET)
@typechecked
def datasets_field(
    type: Optional[str] = None,
    multiple: Optional[bool] = None,
    entity_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a dataset search select field configurable for any dataset type.

    `type` filters the available datasets by dataset type (e.g. "INTENSITY",
    "PAIRWISE", "ANOVA"). Omit to allow selection of any dataset type.
    `multiple` controls whether multiple datasets can be selected (default False).
    `entity_type` filters by entity type (e.g. "protein", "gene").
    """
    parameters: Dict[str, Any] = {}
    if type is not None:
        parameters["type"] = type
    if multiple is not None:
        parameters["multiple"] = multiple
    if entity_type is not None:
        parameters["entityType"] = entity_type

    result: Dict[str, Any] = {}
    if parameters:
        result["json_schema_extra"] = {"parameters": parameters}
    return result


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


@field_builder(FieldType.ENTITY_LIST_ENTITY_IDS)
@typechecked
def entity_list_entity_ids_field(
    type: Optional[Union[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Pick an entity list; the field's value is the array of entity_ids in that list.

    `type` is the entity type (e.g. "protein", "peptide", "gene") used to
    filter the available lists. Pass a literal string, or a `{"ref": "<field>"}`
    dict to bind to another field (commonly the entity_type field).
    """
    parameters: Dict[str, Any] = {}
    if type is not None:
        parameters["type"] = type

    result: Dict[str, Any] = {"json_schema_extra": {}}
    if parameters:
        result["json_schema_extra"]["parameters"] = parameters
    return result


@field_builder(FieldType.SAMPLE_METADATA_COLUMNS)
def sample_metadata_columns_field(
    datasets_ref: str = "input_datasets",
) -> Dict[str, Any]:
    """Pick sample metadata column names from the dataset's experiment design.

    Returns an array of sample metadata column names (capped at 4 on the
    frontend). `datasets_ref` is the name of the field that holds the
    dataset reference the frontend uses to populate the available columns.
    """
    return {
        "json_schema_extra": {
            "parameters": {
                "datasetsSearch": {"ref": datasets_ref},
            }
        }
    }


@field_builder(FieldType.SAMPLE_METADATA_VALUES_FILTER)
@typechecked
def sample_metadata_values_filter_field(
    column_ref: str = "filter_based_on_condition",
    datasets_ref: str = "input_datasets",
    filterable: Optional[bool] = None,
    sortable: Optional[bool] = None,
    advanced_filtering: Optional[bool] = None,
    ignored_values: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Pick multiple values to keep from a single sample metadata column.

    The frontend populates the selectable value list from the experiment
    design table using `column_ref` (the field holding the selected column
    name) and `datasets_ref` (the field holding the dataset reference).

    `filterable`, `sortable` and `advanced_filtering` toggle the component's
    add/remove, reordering and advanced-filtering affordances. `ignored_values`
    are values excluded from the selectable list. Each is omitted from the
    payload when left unset so the frontend applies its own default.
    """
    parameters: Dict[str, Any] = {
        "datasetsSearch": {"ref": datasets_ref},
        "columnName": {"ref": column_ref},
    }

    if filterable is not None:
        parameters["filterable"] = filterable
    if sortable is not None:
        parameters["sortable"] = sortable
    if advanced_filtering is not None:
        parameters["advancedFiltering"] = advanced_filtering
    if ignored_values is not None:
        parameters["ignoredValues"] = ignored_values

    return {
        "json_schema_extra": {
            "parameters": parameters,
        }
    }


@field_builder(FieldType.ENTITY_LISTS)
@typechecked
def entity_lists_field(
    type: Optional[Union[str, Dict[str, Any]]] = None,
    datasets_ref: Optional[str] = None,
    resolve_entities: Optional[bool] = None,
    sortable: Optional[bool] = None,
    enable_settings: Optional[bool] = None,
) -> Dict[str, Any]:
    """Pick one or more entity lists (the multi-list entity lists form).

    The field's value is an array of the selected lists. The entity type used
    to filter the available lists comes from either `type` (a literal such as
    "protein"/"peptide"/"gene", or a `{"ref": "<field>"}` dict) or `datasets_ref`
    (the name of a datasets-search field, bound via `entityTypeFromDatasetsSearch`
    as the module instructions do).

    When `resolve_entities` is true each selected list is emitted as
    `{id, name, entityIds}` instead of just `{id}`. `sortable` toggles
    drag-reordering of the selected lists; `enable_settings` toggles the
    per-list settings affordance. Each parameter is omitted when unset so the
    frontend applies its own default.
    """
    parameters: Dict[str, Any] = {}

    if type is not None:
        parameters["type"] = type
    if datasets_ref is not None:
        parameters["entityTypeFromDatasetsSearch"] = {"ref": datasets_ref}
    if resolve_entities is not None:
        parameters["resolveEntities"] = resolve_entities
    if sortable is not None:
        parameters["sortable"] = sortable
    if enable_settings is not None:
        parameters["enableSettings"] = enable_settings

    result: Dict[str, Any] = {"json_schema_extra": {}}
    if parameters:
        result["json_schema_extra"]["parameters"] = parameters
    return result