import math
import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from .field_types import FieldType
from .field_builder import field_builder
from typeguard import typechecked

class FieldDataType(str, Enum):
    BOOLEAN = "boolean"
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    OBJECT = "object"
    ARRAY = "array"

EntityType = Literal["protein", "peptide", "gene", "metabolite", "ptm", "precursor"]

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

@field_builder(FieldType.BLOB)
@typechecked
def blob_field(
    default: Optional[str] = None,
    placeholder: Optional[str] = None,
    rows: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a blob field: free text entered in a multi-line text area.

    The value is free text; its type isn't checked. `placeholder` is shown while the text area is
    empty, and `rows` is its height in lines (at least 1); text longer than
    that scrolls, so it doesn't limit the value. Each parameter is omitted
    when unset so the frontend applies its own default.
    """
    if isinstance(rows, bool):
        raise TypeError(f"rows must be an int, got {rows!r}")
    if rows is not None and rows < 1:
        raise ValueError(f"rows must be >= 1, got {rows}")

    result: Dict[str, Any] = {"json_schema_extra": {}}
    if default is not None:
        result["json_schema_extra"]["default"] = default

    parameters: Dict[str, Any] = {}
    if placeholder is not None:
        parameters["placeholder"] = placeholder
    if rows is not None:
        parameters["rows"] = rows
    if parameters:
        result["json_schema_extra"]["parameters"] = parameters
    return result


@field_builder(FieldType.NUMBER)
@typechecked
def number_field(
    field_data_type: Optional[Literal[FieldDataType.INT, FieldDataType.FLOAT]],
    default: Optional[Union[int, float]] = None,
    ge: Optional[Union[int, float]] = None,
    le: Optional[Union[int, float]] = None,
) -> Dict[str, Any]:
    """Create a number field.

    `field_data_type` must always be passed. It tells the frontend (and the
    validator) whether the number is an int or a float and is emitted as
    `parameters.fieldDataType`; pass None explicitly to accept either.
    """
    result = {}
    
    if default is not None:
        result["json_schema_extra"] = {"default": default}
    
    if field_data_type is not None:
        if "json_schema_extra" not in result:
            result["json_schema_extra"] = {}
        result["json_schema_extra"]["parameters"] = {"fieldDataType": FieldDataType(field_data_type).value}
    
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


@field_builder(FieldType.RADIO_SELECTION)
@typechecked
def radio_selection_field(
    default: Optional[str] = None,
    options: Optional[Union[List[str], Dict[str, Any]]] = None,
    inline: Optional[bool] = None,
) -> Dict[str, Any]:
    """Create a radio selection field: pick one of `options`, shown as radio buttons.

    `options` works as in `select_field`. `inline` lays the radio buttons out
    on one line.
    """
    result: Dict[str, Any] = {}

    if default is not None:
        result["json_schema_extra"] = {"default": default}

    parameters: Dict[str, Any] = {}
    if options is not None:
        parameters["options"] = _normalize_options_arg(options)
    if inline is not None:
        parameters["inline"] = inline
    if parameters:
        result.setdefault("json_schema_extra", {})["parameters"] = parameters

    return result


SELECTION_TYPE_OPTIONS = [
    {"name": "Use Selection", "value": "selection"},
    {"name": "Use List", "value": "list"},
]
SELECTION_TYPE_SINGLE_ENTITY_OPTION = {"name": "Single Entity", "value": "single_entity"}


@field_builder(FieldType.RADIO_SELECTION)
@typechecked
def selection_type_field(
    default: Optional[Literal["selection", "list", "single_entity"]] = "selection",
    inline: Optional[bool] = None,
    include_single_entity: bool = False,
) -> Dict[str, Any]:
    """Create a selection type field: a radio choosing "selection" or "list".

    Always has the options "Use Selection" and "Use List", and emits
    `parameters.selectionType: true` so the frontend can tell it apart from an
    ordinary radio. `include_single_entity` adds a third option, "Single
    Entity" ("single_entity"); a "single_entity" default needs it.
    """
    options = [dict(option) for option in SELECTION_TYPE_OPTIONS]
    if include_single_entity:
        options.append(dict(SELECTION_TYPE_SINGLE_ENTITY_OPTION))
    elif default == "single_entity":
        raise ValueError("default 'single_entity' needs include_single_entity=True")

    parameters: Dict[str, Any] = {
        "options": options,
        "selectionType": True,
    }
    if inline is not None:
        parameters["inline"] = inline

    result: Dict[str, Any] = {"json_schema_extra": {"parameters": parameters}}
    if default is not None:
        result["json_schema_extra"]["default"] = default

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
@typechecked
def condition_column_field(datasets_ref: str = "input_datasets") -> Dict[str, Any]:
    """Create a condition column field.

    `datasets_ref` is the name of the field holding the datasets whose
    sample metadata columns are offered.
    """
    return {
        "json_schema_extra": {
            "parameters": {
                "fieldDataType": FieldDataType.STRING,
                "datasetsSearch": {"ref": datasets_ref}
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
    """Create a condition comparisons field.

    Picks any number of comparisons from the conditions in this form's own
    experiment design. The value is
    `{"condition_comparison_pairs": [["C1", "C2"], ...]}`. Compare
    `condition_comparison_field`, which picks one comparison already in a
    dataset.
    """
    return {
        "json_schema_extra": {
            "parameters": {
                "experimentDesign": {"ref": "experiment_design"},
                "conditionColumn": {"ref": "condition_column"}
            }
        }
    }


@field_builder(FieldType.CONDITION_COMPARISON)
@typechecked
def condition_comparison_field(
    datasets_ref: str = "input_datasets",
) -> Dict[str, Any]:
    """Create a condition comparison field.

    Picks one comparison from those already in the dataset chosen in the
    `datasets_ref` field, and which way round to read it. The value is

        {"comparison": {"condition_pair": "C7 - C5", "left": "C5", "right": "C7"}}

    where `condition_pair` names the dataset's comparison and `left` and
    `right` are its two conditions, each appearing in `condition_pair`, in
    either order.

    This differs from `condition_comparisons_field`
    (`PairwiseConditionComparisons`), which picks any number of
    comparisons, as `[condition, condition]` lists, from the conditions in
    this form's own experiment design.
    """
    return {"json_schema_extra": {"parameters": {"datasetsSearch": {"ref": datasets_ref}}}}


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
    field_data_type: Optional[Literal[FieldDataType.INT, FieldDataType.FLOAT]],
    default: Optional[Union[int, float]] = None,
    ge: Optional[Union[int, float]] = None,
    le: Optional[Union[int, float]] = None,
    interval: Optional[Union[int, float]] = None,
) -> Dict[str, Any]:
    """Create a number range field.

    `field_data_type` must always be passed. It tells the frontend (and the
    validator) whether the number is an int or a float and is emitted as
    `parameters.fieldDataType`; pass None explicitly to accept either.
    """
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
    if field_data_type is not None:
        if "json_schema_extra" not in result:
            result["json_schema_extra"] = {}
        result["json_schema_extra"].setdefault("parameters", {})["fieldDataType"] = FieldDataType(field_data_type).value
    return result

@field_builder(FieldType.INTENSITY_INPUT_DATASET)
@typechecked
def intensity_input_dataset_field(entity_types: Optional[List[EntityType]] = None) -> Dict[str, Any]:
    """Create an intensity input dataset field.

    `entity_types` filters by entity type (e.g. ["protein", "gene"]).
    """
    parameters: Dict[str, Any] = {
        "type": "INTENSITY",
        "multiple": False,
        "min": 1,
        "max": 1,
    }
    if entity_types is not None:
        parameters["entityTypes"] = entity_types

    return {
        "json_schema_extra": {
            "name": "Select Intensity dataset",
            "parameters": parameters,
        }
    }

@field_builder(FieldType.INTENSITY_INPUT_DATASET)
@typechecked
def intensity_input_datasets_field(entity_types: Optional[List[EntityType]] = None, min: int = 1, max: Optional[int] = None) -> Dict[str, Any]:
    """Create an intensity input datasets field (multi-select).

    `entity_types` filters by entity type (e.g. ["protein", "gene"]).
    `min`/`max` bound how many datasets can be selected; `max` is omitted
    when unset, leaving the selection unbounded above.
    """
    parameters: Dict[str, Any] = {
        "type": "INTENSITY",
        "multiple": True,
        "min": min,
    }
    if max is not None:
        parameters["max"] = max
    if entity_types is not None:
        parameters["entityTypes"] = entity_types

    return {
        "json_schema_extra": {
            "name": "Select Intensity dataset",
            "parameters": parameters,
        }
    }

@field_builder(FieldType.INTENSITY_INPUT_DATASET)
@typechecked
def datasets_field(
    type: Optional[str] = None,
    multiple: Optional[bool] = None,
    entity_types: Optional[List[EntityType]] = None,
) -> Dict[str, Any]:
    """Create a dataset search select field configurable for any dataset type.

    `type` filters the available datasets by dataset type (e.g. "INTENSITY",
    "PAIRWISE", "ANOVA"). Omit to allow selection of any dataset type.
    `multiple` controls whether multiple datasets can be selected (default False).
    `entity_types` filters by entity type (e.g. ["protein", "gene"]).
    """
    parameters: Dict[str, Any] = {}
    if type is not None:
        parameters["type"] = type
    if multiple is not None:
        parameters["multiple"] = multiple
    if entity_types is not None:
        parameters["entityTypes"] = entity_types

    result: Dict[str, Any] = {}
    if parameters:
        result["json_schema_extra"] = {"parameters": parameters}
    return result


@field_builder(FieldType.ENTITY_TYPE)
@typechecked
def entity_type_field(
    default: Optional[EntityType] = None,
    datasets_ref: str = "input_datasets",
) -> Dict[str, Any]:
    """Create an entity type field.

    `default` is one of the EntityType values (e.g. "protein").
    `datasets_ref` names the dataset field this entity type applies to; the
    datasets selected there must have the chosen entity type.
    """
    result = {
        "json_schema_extra": {
            "parameters": {
                "datasetsSearch": {"ref": datasets_ref}
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
    type: Optional[Union[EntityType, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Pick an entity list; the field's value is the array of entity_ids in that list.

    `type` is the entity type (e.g. "protein", "peptide", "gene") used to
    filter the available lists. Pass an EntityType value, or a `{"ref": "<field>"}`
    dict to bind to another field (commonly the entity_type field).
    """
    parameters: Dict[str, Any] = {}
    if type is not None:
        parameters["type"] = type

    result: Dict[str, Any] = {"json_schema_extra": {}}
    if parameters:
        result["json_schema_extra"]["parameters"] = parameters
    return result


@field_builder(FieldType.ENTITY_LIST)
@typechecked
def entity_list_field(
    type: Optional[Union[EntityType, Dict[str, Any]]] = None,
    owner_only: Optional[bool] = None,
) -> Dict[str, Any]:
    """Pick a single entity list; the field's value is that list's id.

    `type` is the entity type (e.g. "protein", "peptide", "gene") used to
    filter the available lists. Pass an EntityType value, or a `{"ref": "<field>"}`
    dict to bind to another field (commonly the entity_type field). When
    `owner_only` is true only the user's own lists are offered. Each parameter
    is omitted when unset so the frontend applies its own default.

    Unlike `entity_list_entity_ids_field` the value is the list id, not its
    entity ids, and unlike `entity_lists_field` only one list is picked.
    """
    parameters: Dict[str, Any] = {}
    if type is not None:
        parameters["type"] = type
    if owner_only is not None:
        parameters["ownerOnly"] = owner_only

    result: Dict[str, Any] = {"json_schema_extra": {}}
    if parameters:
        result["json_schema_extra"]["parameters"] = parameters
    return result


@field_builder(FieldType.ENTITY_TITLE)
@typechecked
def entity_title_field(
    entity_type: Optional[Union[EntityType, Dict[str, Any]]] = None,
    datasets_ref: Optional[str] = None,
    include_hierarchical_entities: Optional[bool] = None,
) -> Dict[str, Any]:
    """Pick the column used to label entities, such as "protein_name" or "gene_name".

    The columns offered depend on the entity type, which comes from
    `entity_type` (an EntityType value, or a `{"ref": "<field>"}` dict, commonly
    the entity_type field) or else from the datasets in the field named by
    `datasets_ref`; with neither the frontend uses "protein".
    `include_hierarchical_entities` also offers the parent entity type's
    columns (protein's for a peptide or ptm). Each parameter is omitted when
    unset so the frontend applies its own default.
    """
    parameters: Dict[str, Any] = {}
    if entity_type is not None:
        parameters["entityType"] = entity_type
    if datasets_ref is not None:
        parameters["datasetsSearch"] = {"ref": datasets_ref}
    if include_hierarchical_entities is not None:
        parameters["includeHierarchicalEntities"] = include_hierarchical_entities

    result: Dict[str, Any] = {"json_schema_extra": {}}
    if parameters:
        result["json_schema_extra"]["parameters"] = parameters
    return result


@field_builder(FieldType.ORDERABLE_SAMPLE_METADATA_COLUMNS)
@typechecked
def orderable_sample_metadata_columns_field(
    datasets_ref: str = "input_datasets",
    default: Optional[List[Dict[str, Any]]] = None,
    entity_type: Optional[Union[EntityType, Dict[str, Any]]] = None,
    include_hierarchical_entities: Optional[bool] = None,
    orderable_protein_ids: Optional[bool] = None,
    allow_dataset: Optional[bool] = None,
) -> Dict[str, Any]:
    """Pick an ordered list of columns to group samples by, such as an x axis.

    The value is a list of column objects, in grouping order:
    `{"field": <name>, "field_type": "sample_metadata" | "entity" | "dataset",
    "order": "asc" | "desc" | "none" | "custom", "type": "categorical" |
    "numeric", "order_by_values": [...], "entity_label": <title column>}`.
    Only `field` is required, and `order_by_values` must hold at least one
    value when `order` is "custom".

    `datasets_ref` is the name of the field holding the dataset whose sample
    metadata columns are offered. `entity_type` (an EntityType value or a
    `{"ref": "<field>"}` dict) also offers that entity as a column, with
    `include_hierarchical_entities` adding its parent entity types;
    `orderable_protein_ids` lets an entity column be custom-ordered instead of
    labelled; `allow_dataset` also offers the dataset as a column. Each of
    those is omitted when unset so the frontend applies its own default.
    """
    parameters: Dict[str, Any] = {"datasetsSearch": {"ref": datasets_ref}}
    if entity_type is not None:
        parameters["entityType"] = entity_type
    if include_hierarchical_entities is not None:
        parameters["includeHierarchicalEntities"] = include_hierarchical_entities
    if orderable_protein_ids is not None:
        parameters["orderableProteinIds"] = orderable_protein_ids
    if allow_dataset is not None:
        parameters["allowDataset"] = allow_dataset

    result: Dict[str, Any] = {"json_schema_extra": {"parameters": parameters}}
    if default is not None:
        result["json_schema_extra"]["default"] = default
    return result


@field_builder(FieldType.COLOUR_PALETTE)
def colour_palette_field() -> Dict[str, Any]:
    """Pick one of the organisation's colour palettes; the value is its id.

    The frontend also offers "None" (a null value), and only shows the field
    when the workspace_colour_palettes feature flag is on.
    """
    return {}


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

    The value is `{"values": ["C1", "C3"], "filters": [...]}`: `values` are
    the column values to keep, and `filters`, only filled in with advanced
    filtering, are `{"column": "batch", "value": ["B1"]}` objects that narrow
    which values can be picked. `filters` may be left out.

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


@field_builder(FieldType.DATABASES)
@typechecked
def databases_field(
    knowledge_bases: Optional[Union[List[str], Dict[str, Any]]] = None,
    allow_custom_databases: Optional[bool] = None,
    entity_type: Optional[Union[EntityType, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Create a databases field pairing a knowledge-base multi-select with optional custom analysis sets.

    `knowledge_bases` is the list of preset knowledge base strings offered as
    multi-select options.
    `allow_custom_databases` gates the analysis-sets section; when False (default)
    only `knowledgeBases` is emitted by the field.
    `entity_type` is passed to each analysis set's ProteinListsForm to filter
    available entity lists (e.g. "protein", "peptide", or a {"ref": "<field>"} dict).
    """
    parameters: Dict[str, Any] = {}

    if knowledge_bases is not None:
        parameters["knowledgeBases"] = knowledge_bases
    if allow_custom_databases is not None:
        parameters["allowCustomDatabases"] = allow_custom_databases
    if entity_type is not None:
        parameters["entityType"] = entity_type

    result: Dict[str, Any] = {"json_schema_extra": {}}
    if parameters:
        result["json_schema_extra"]["parameters"] = parameters
    return result


@field_builder(FieldType.DATASET_PARAM_MULTIPLE)
@typechecked
def dataset_param_multiple_field(
    datasets_ref: str = "input_datasets",
    initialise_with_all: bool = True,
) -> Dict[str, Any]:
    """Create a dataset param multiple field.

    Picks any of the databases recorded in the job run params of the dataset
    chosen in the `datasets_ref` field: the knowledge bases and analysis set
    names of its `Databases` params or, failing those, its `sets`. The value
    is a list of those names, such as
    `["GO - Biological Process", "MSigDB-H (hallmark gene sets)"]`.

    With `initialise_with_all` (the default), the frontend starts with every
    database selected.
    """
    return {
        "json_schema_extra": {
            "parameters": {
                "datasetsSearch": {"ref": datasets_ref},
                "initialiseWithAll": initialise_with_all,
            }
        }
    }


@field_builder(FieldType.REFERENCE_DATA_FILE)
@typechecked
def reference_data_file_field(accept: Optional[List[str]] = None) -> Dict[str, Any]:
    """Pick a single reference data file; the field's value is that file's file_id.

    `accept` restricts which file extensions/types are selectable (e.g.
    [".csv", ".tsv"]); it is joined into a comma-separated `accept` string, as
    the frontend file picker expects. Omit it (or pass an empty list) to allow
    any file.
    """
    if accept:
        return {"json_schema_extra": {"parameters": {"accept": ",".join(accept)}}}
    return {}


@field_builder(FieldType.DATASET_TABLE_VALUE)
@typechecked
def dataset_table_value_field(
    table_name: str,
    column_name: str,
    datasets_ref: str = "input_datasets",
    multiple: Optional[bool] = None,
) -> Dict[str, Any]:
    """Pick one or more values from a named column of a dataset's table.

    The frontend reads `table_name` (`datasetTableName`) and `column_name`
    (`datasetTableColumnName`) to know which table/column of the dataset to
    source the selectable values from, and `datasets_ref` (the field holding
    the dataset reference) to resolve the dataset itself.

    `multiple` toggles single vs. multi selection; it is omitted from the
    payload when unset so the frontend applies its own default.
    """
    parameters: Dict[str, Any] = {
        "datasetsSearch": {"ref": datasets_ref},
        "datasetTableName": table_name,
        "datasetTableColumnName": column_name,
    }

    if multiple is not None:
        parameters["multiple"] = multiple

    return {"json_schema_extra": {"parameters": parameters}}


@field_builder(FieldType.ENTITY_LISTS)
@typechecked
def entity_lists_field(
    type: Optional[Union[EntityType, Dict[str, Any]]] = None,
    datasets_ref: Optional[str] = None,
    resolve_entities: Optional[bool] = None,
    sortable: Optional[bool] = None,
    enable_settings: Optional[bool] = None,
) -> Dict[str, Any]:
    """Pick one or more entity lists (the multi-list entity lists form).

    The field's value is an array of the selected lists. The entity type used
    to filter the available lists comes from either `type` (an EntityType value
    such as "protein"/"peptide"/"gene", or a `{"ref": "<field>"}` dict) or `datasets_ref`
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


# Bounds, in pixels, of a fixed plot size's width and height.
PLOT_SIZE_MIN = 1
PLOT_SIZE_MAX = 1000


@field_builder(FieldType.PLOT_SIZE)
@typechecked
def plot_size_field(
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a plot size field.

    The value is `{"fixed": False}` to fit the plot to the module, or
    `{"fixed": True, "width": <px>, "height": <px>}` for a fixed size, with
    width and height between 1 and 1000 pixels.

    The default fits the plot to the module. Pass both `width` and `height`
    to default to a fixed size instead.
    """
    if (width is None) != (height is None):
        raise ValueError("width and height must be passed together")
    if width is None:
        default: Dict[str, Any] = {"fixed": False}
    else:
        for label, size in (("width", width), ("height", height)):
            if not PLOT_SIZE_MIN <= size <= PLOT_SIZE_MAX:
                raise ValueError(f"{label} must be between {PLOT_SIZE_MIN} and {PLOT_SIZE_MAX}, got {size}")
        default = {"fixed": True, "width": width, "height": height}

    return {"json_schema_extra": {"default": default}}


# A decimal number, optionally in scientific notation, such as "0.0015" or
# "1.5e-3". Surrounding whitespace is allowed, as the frontend trims it.
_SCIENTIFIC_NOTATION_PATTERN = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def is_scientific_notation(value: Any) -> bool:
    """Whether `value` is a string holding a finite number such as "1.5e-3"."""
    if not isinstance(value, str):
        return False
    text = value.strip()
    return _SCIENTIFIC_NOTATION_PATTERN.fullmatch(text) is not None and math.isfinite(float(text))


@field_builder(FieldType.SCIENTIFIC_NOTATION)
@typechecked
def scientific_notation_field(
    default: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a scientific notation field.

    The value is a string holding a finite number, written plainly or in
    scientific notation, such as "0.0015" or "1.5e-3".
    """
    if default is not None and not is_scientific_notation(default):
        raise ValueError(f"default must be a number such as '1.5e-3', got {default!r}")

    result: Dict[str, Any] = {}
    if default is not None:
        result["json_schema_extra"] = {"default": default}
    return result


# The smallest fold change threshold; a fold change of 1 means no change.
FOLD_CHANGE_THRESHOLD_MIN = 1


@field_builder(FieldType.FOLD_CHANGE_THRESHOLD)
@typechecked
def fold_change_threshold_field(
    default: Optional[float] = None,
) -> Dict[str, Any]:
    """Create a fold change threshold field.

    The value is a float of at least 1; an int such as 2 counts, as JSON
    sends 2.0 as 2. The frontend also shows the corresponding log2 ratio.
    """
    if isinstance(default, bool):
        raise TypeError(f"default must be a float, got {default!r}")
    if default is not None and default < FOLD_CHANGE_THRESHOLD_MIN:
        raise ValueError(f"default must be >= {FOLD_CHANGE_THRESHOLD_MIN}, got {default}")

    result: Dict[str, Any] = {}
    if default is not None:
        result["json_schema_extra"] = {"default": default}
    return result
