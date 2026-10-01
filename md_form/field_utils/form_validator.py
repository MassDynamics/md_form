"""Validate a data payload against a form-definition dict.

The form definition is the *translated payload* shape produced by
:func:`md_form.translate_payload` (and stored in e.g. ``tutorial/*.json``):

    {
      "properties": {
        "<field_name>": {
          "fieldType": "String" | "Boolean" | "Number" | ...,
          "parameters": {"options": [...], "min": ..., "max": ...},
          "rules": [{"name": "is_required"}, ...],
          "when": {...},
          "default": ...
        },
        ...
      }
    }

This module lets you check a submitted data dict against that definition at
runtime, without needing the original Pydantic model. It enforces:

* required fields (``is_required`` rules, gated by ``when`` conditions),
* ``parameters.options`` membership (static lists and dynamic ``{ref, cases}``),
  with a ``String`` select taking one value and a ``Multiple`` select a list,
* ``parameters.min`` / ``parameters.max`` bounds (a number's value, a string's
  length, a list's item count),
* value types for ``Boolean`` (a bool), ``Number`` / ``NumberRange`` (an
  int or float) and ``DatasetTableValue`` (a list, or a single value when
  ``parameters.multiple`` is false) fields,
* ``parameters.fieldDataType`` on any field (``int``, ``float``, ``boolean``,
  ``string``, ``array`` or ``object``),
* ``PairwiseConditionComparisons`` values: an object whose
  ``condition_comparison_pairs`` is a list of two-condition pairs,
* the value/cross-field ``rules`` (``is_equal_to_value``, etc.),
* dataset-selection fields against a supplied ``datasets`` list (see the
  ``datasets`` argument of :func:`validate_form`), including that each
  selected dataset has the entity type chosen in an ``EntityType`` field
  pointing at it.

Beyond the boolean, number and dataset-table-value fields above, ``fieldType`` is treated as a
frontend widget hint rather than a reliable data type, so it is not used to
type-check other values. Rules that cannot be checked from
the data alone are skipped rather than reported, so the validator stays
forward-compatible with new field/rule kinds.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .field_helpers import FieldDataType
from .field_types import FieldType
from .when import evaluate_when

# fieldType of a dataset-selection field (see field_helpers.datasets_field).
_DATASETS_FIELD_TYPE = FieldType.INTENSITY_INPUT_DATASET.value  # "Datasets"

# fieldType of a boolean (checkbox/toggle) field.
_BOOLEAN_FIELD_TYPE = FieldType.BOOLEAN.value  # "Boolean"

# fieldTypes whose value must be a number (see field_helpers.number_field and
# field_helpers.numberrange_field).
_NUMBER_FIELD_TYPES = (FieldType.NUMBER.value, FieldType.NUMBER_RANGE.value)  # "Number", "NumberRange"

# fieldType whose value must be a list, or a single value when single-select
# (see field_helpers.dataset_table_value_field).
_DATASET_TABLE_VALUE_FIELD_TYPE = FieldType.DATASET_TABLE_VALUE.value  # "DatasetTableValue"

# Checks and error messages for ``parameters.fieldDataType``. ``bool`` is a
# subclass of ``int`` in Python, so it is excluded from int and float.
_FIELD_DATA_TYPE_CHECKS = {
    FieldDataType.INT.value: (
        lambda v: isinstance(v, int) and not isinstance(v, bool), "must be an int"),
    FieldDataType.FLOAT.value: (
        lambda v: isinstance(v, (int, float)) and not isinstance(v, bool), "must be a float"),
    FieldDataType.BOOLEAN.value: (lambda v: isinstance(v, bool), "must be a boolean"),
    FieldDataType.STRING.value: (lambda v: isinstance(v, str), "must be a string"),
    FieldDataType.ARRAY.value: (lambda v: isinstance(v, list), "must be an array"),
    FieldDataType.OBJECT.value: (lambda v: isinstance(v, dict), "must be an object"),
}

# fieldTypes of single- and multiple-choice fields (see field_helpers.select_field
# and field_helpers.multiple_select_field).
_SINGLE_SELECT_FIELD_TYPE = FieldType.STRING.value  # "String"
_MULTIPLE_SELECT_FIELD_TYPE = FieldType.MULTIPLE.value  # "Multiple"

# fieldType of a sample-metadata table (see field_helpers.experiment_design_field).
_SAMPLE_METADATA_TABLE_FIELD_TYPE = FieldType.EXPERIMENT_DESIGN.value  # "SampleMetadataTable"

# fieldType of a condition-comparisons object (see field_helpers.condition_comparisons_field).
_CONDITION_COMPARISONS_FIELD_TYPE = FieldType.CONDITION_COMPARISONS.value  # "PairwiseConditionComparisons"

# fieldType of a control-variables list (see field_helpers.control_variables_field).
_CONTROL_VARIABLES_FIELD_TYPE = FieldType.CONTROL_VARIABLES.value  # "PairwiseControlVariables"

# fieldType of an entity-type field (see field_helpers.entity_type_field).
_ENTITY_TYPE_FIELD_TYPE = FieldType.ENTITY_TYPE.value  # "EntityType"

# Only fully-processed datasets are selectable.
_COMPLETED_STATE = "COMPLETED"


@dataclass(frozen=True)
class FieldError:
    """A single validation failure for one field."""

    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.field}: {self.message}"


@dataclass
class ValidationResult:
    """Outcome of :func:`validate_form`.

    Truthy when the data is valid, so it can be used directly in a condition::

        if validate_form(definition, data):
            ...
    """

    errors: List[FieldError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def __bool__(self) -> bool:
        return self.is_valid

    def raise_if_invalid(self) -> "ValidationResult":
        if self.errors:
            raise FormValidationError(self)
        return self


class FormValidationError(ValueError):
    """Raised when validation fails and errors should propagate as an exception."""

    def __init__(self, result: ValidationResult):
        self.result = result
        joined = "; ".join(str(e) for e in result.errors)
        super().__init__(f"Invalid form data: {joined}")


def is_valid_form(definition: Dict[str, Any], data: Dict[str, Any], **kwargs: Any) -> bool:
    """Convenience wrapper returning just the boolean validity."""
    return validate_form(definition, data, **kwargs).is_valid


def validate_form(
    definition: Dict[str, Any],
    data: Dict[str, Any],
    *,
    datasets: Optional[List[Dict[str, Any]]] = None,
    allow_unknown: bool = True,
    raise_on_error: bool = False,
) -> ValidationResult:
    """Validate ``data`` against a form ``definition`` dict.

    Args:
        definition: A form-definition dict. Either the whole translated payload
            (``{"properties": {...}}``) or the bare properties map.
        data: The submitted values, keyed by field name.
        datasets: The datasets available for selection, each a dict with at
            least an ``id`` (e.g. ``{"id": ..., "name": ..., "type": ...}``).
            Required whenever the definition contains a dataset-selection field
            (``fieldType == "Datasets"``): the selected ids in ``data`` are
            checked against these. If the form has such a field and ``datasets``
            is ``None``, that is reported as an error.
        allow_unknown: When ``False``, keys in ``data`` with no matching field
            in the definition are reported as errors. Defaults to ``True``
            because payloads often carry non-form metadata.
        raise_on_error: When ``True``, raise :class:`FormValidationError`
            instead of returning a result with errors.

    Returns:
        A :class:`ValidationResult`. It is truthy when the data is valid.
    """
    if not isinstance(data, dict):
        result = ValidationResult([FieldError("<root>", "data must be an object")])
        return result.raise_if_invalid() if raise_on_error else result

    fields = _get_field_defs(definition)
    errors: List[FieldError] = []

    for name, spec in fields.items():
        errors.extend(_validate_field(name, spec, data))

    errors.extend(_check_datasets(fields, data, datasets))

    if not allow_unknown:
        for key in data:
            if key not in fields:
                errors.append(FieldError(key, "unknown field not present in the form definition"))

    result = ValidationResult(errors)
    return result.raise_if_invalid() if raise_on_error else result


def _check_datasets(
    fields: Dict[str, Any],
    data: Dict[str, Any],
    datasets: Optional[List[Dict[str, Any]]],
) -> List[FieldError]:
    """Cross-check dataset-selection fields against the available ``datasets``.

    For every field whose ``fieldType`` is ``"Datasets"``:
    * if ``datasets`` is ``None`` the field cannot be validated -> error;
    * otherwise each selected dataset id in ``data`` must appear in ``datasets``,
      match the field's required ``parameters.type`` (when set), be in the
      ``COMPLETED`` state, and list the entity type chosen in any active
      ``EntityType`` field whose ``parameters.datasetsSearch.ref`` names this
      field among its ``entity_types`` (datasets without ``entity_types`` are
      not checked).
    """
    errors: List[FieldError] = []
    dataset_fields = [(n, s) for n, s in fields.items() if s.get("fieldType") == _DATASETS_FIELD_TYPE]
    if not dataset_fields:
        return errors

    if datasets is None:
        return [
            FieldError(name, "a datasets list must be provided to validate this field")
            for name, _ in dataset_fields
        ]

    by_id = {d["id"]: d for d in datasets if isinstance(d, dict) and "id" in d}
    for name, spec in dataset_fields:
        value = data.get(name)
        if value is None:
            continue
        params = spec.get("parameters") or {}
        required_type = params.get("type")
        entity_types = _selected_entity_types(fields, data, name)
        for ds_id in _selected_dataset_ids(value):
            dataset = by_id.get(ds_id)
            if dataset is None:
                errors.append(FieldError(name, f"dataset {ds_id!r} is not in the provided datasets"))
                continue
            if required_type is not None and dataset.get("type") != required_type:
                errors.append(FieldError(
                    name,
                    f"dataset {ds_id!r} must be of type {required_type!r}, not {dataset.get('type')!r}",
                ))
            if dataset.get("state") != _COMPLETED_STATE:
                errors.append(FieldError(
                    name,
                    f"dataset {ds_id!r} must be in state {_COMPLETED_STATE!r}, not {dataset.get('state')!r}",
                ))
            available = dataset.get("entity_types")
            if isinstance(available, list):
                for entity_type in entity_types:
                    if entity_type not in available:
                        errors.append(FieldError(
                            name,
                            f"dataset {dataset.get('name', ds_id)!r} does not have entity type {entity_type!r}",
                        ))
    return errors


def _selected_entity_types(fields: Dict[str, Any], data: Dict[str, Any], dataset_field: str) -> List[str]:
    """Entity types chosen in active ``EntityType`` fields that search ``dataset_field``."""
    entity_types: List[str] = []
    for name, spec in fields.items():
        if spec.get("fieldType") != _ENTITY_TYPE_FIELD_TYPE:
            continue
        search = (spec.get("parameters") or {}).get("datasetsSearch")
        if not isinstance(search, dict) or search.get("ref") != dataset_field:
            continue
        when = spec.get("when")
        if when and not evaluate_when(when, data):
            continue
        value = data.get(name)
        if isinstance(value, str) and value not in entity_types:
            entity_types.append(value)
    return entity_types


def _selected_dataset_ids(value: Any) -> List[Any]:
    """Extract the selected dataset ids from a field value.

    Accepts a single value or a list, where each item is either an id or a
    dict carrying an ``id``.
    """
    items = value if isinstance(value, list) else [value]
    ids: List[Any] = []
    for item in items:
        ids.append(item.get("id") if isinstance(item, dict) else item)
    return ids


def _get_field_defs(definition: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the field specs from a definition, tolerating both shapes.

    Only entries that carry a ``fieldType`` are treated as fields, so
    definition scaffolding like ``$defs`` is ignored.
    """
    if not isinstance(definition, dict):
        return {}
    props = definition.get("properties")
    if not isinstance(props, dict):
        props = definition
    return {
        name: spec
        for name, spec in props.items()
        if isinstance(spec, dict) and "fieldType" in spec
    }


def _is_absent(value: Any) -> bool:
    """Treat ``None`` and "empty all the way down" values as not provided.

    A required field needs at least one concrete scalar somewhere in its value.
    ``None``, empty containers, and containers holding only other empty values
    all count as absent and fail an ``is_required`` check just as a missing key
    would. For example a PairwiseConditionComparisons submitted as ``{}``,
    ``{"condition_comparison_pairs": []}`` or ``{"condition_comparison_pairs":
    [[]]}`` carries no actual comparisons and is absent. Non-container values --
    including falsy ones such as ``False`` and ``0`` -- are real and present.
    """
    if value is None:
        return True
    if isinstance(value, dict):
        return all(_is_absent(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return all(_is_absent(v) for v in value)
    if isinstance(value, str):
        return len(value) == 0
    return False


def _validate_field(name: str, spec: Dict[str, Any], data: Dict[str, Any]) -> List[FieldError]:
    when = spec.get("when")
    # A field gated by an unmet `when` is inactive: skip every check for it.
    if when and not evaluate_when(when, data):
        return []

    # Boolean, number and dataset-table-value fields must carry a value of that type. An
    # empty string (or empty list/object) is the wrong type, not an absent value,
    # so it fails even on an optional field. ``None`` counts as unset for boolean
    # and dataset-table-value fields, and for a number field whose default is
    # ``None``; a number field with a real default must not be sent as ``None``.
    if name in data:
        type_error = _check_value_type(name, spec, data[name])
        if type_error is not None:
            return [type_error]

    rules = _normalize_rules(spec.get("rules"))
    present = name in data and not _is_absent(data.get(name))

    if not present:
        if _has_required_rule(rules):
            return [FieldError(name, "is required")]
        return []

    value = data[name]

    # A sample-metadata table must always be a proper column table once the
    # field is active and filled in, regardless of which rules/parameters the
    # (possibly stale) definition happens to carry. A malformed shape (e.g. a
    # row-oriented array-of-arrays) makes the column/rule checks meaningless, so
    # report just the shape failure and stop.
    if spec.get("fieldType") == _SAMPLE_METADATA_TABLE_FIELD_TYPE:
        shape_error = _check_table_shape(name, value)
        if shape_error is not None:
            return [shape_error]

    # Likewise a control-variables value must always be a flat list of
    # ``{"type": ..., "column": ...}`` objects; a wrapped object such as
    # ``{"control_variables": [...]}`` would silently bypass the
    # ``control_variables[].column`` lookups other fields rely on.
    if spec.get("fieldType") == _CONTROL_VARIABLES_FIELD_TYPE:
        shape_error = _check_control_variables_shape(name, value)
        if shape_error is not None:
            return [shape_error]

    # A condition-comparisons value must be an object holding a list of
    # [condition, condition] pairs. Each malformed comparison is reported.
    if spec.get("fieldType") == _CONDITION_COMPARISONS_FIELD_TYPE:
        shape_errors = _check_condition_comparisons_shape(name, value)
        if shape_errors:
            return shape_errors

    errors: List[FieldError] = []

    errors.extend(_check_options(name, spec, value, data))
    errors.extend(_check_bounds(name, spec, value))
    errors.extend(_check_required_columns(name, spec, value, data))
    if spec.get("fieldType") == _CONTROL_VARIABLES_FIELD_TYPE:
        errors.extend(_check_control_variable_types(name, spec, value))
    for rule in rules:
        # On a control-variables field, value rules apply to each control
        # variable's column rather than to the list as a whole.
        if (
            spec.get("fieldType") == _CONTROL_VARIABLES_FIELD_TYPE
            and rule.get("name") in _COLUMN_VALUE_RULES
        ):
            errors.extend(_check_control_variable_columns(name, rule, value))
            continue
        if rule.get("name") == "has_multiple_column_values_from_field_in_table":
            errors.extend(_check_multiple_column_values(name, rule, value, data))
            continue
        err = _check_rule(name, rule, value, data)
        if err is not None:
            errors.append(err)

    return errors


def _normalize_rules(rules: Any) -> List[Dict[str, Any]]:
    if rules is None:
        return []
    if isinstance(rules, dict):
        return [rules]
    if isinstance(rules, list):
        return [r for r in rules if isinstance(r, dict)]
    return []


def _has_required_rule(rules: List[Dict[str, Any]]) -> bool:
    return any(r.get("name") == "is_required" for r in rules)


def _allowed_option_values(options: Any, data: Dict[str, Any]) -> Optional[List[Any]]:
    """Resolve the set of currently-selectable option values.

    Returns ``None`` when membership cannot be determined statically (e.g. a
    dynamic ``{ref, cases}`` whose controlling field value has no matching case).
    """
    if isinstance(options, list):
        return _values_from_option_list(options, data)
    if isinstance(options, dict):
        ref = options.get("ref")
        cases = options.get("cases")
        if isinstance(cases, dict) and isinstance(ref, str):
            case = cases.get(data.get(ref))
            if isinstance(case, list):
                return _values_from_option_list(case, data)
        return None
    return None


def _values_from_option_list(options: List[Any], data: Dict[str, Any]) -> List[Any]:
    allowed: List[Any] = []
    for opt in options:
        # Translated payloads use {name, value} dicts, but tolerate raw scalars too.
        if not isinstance(opt, dict):
            allowed.append(opt)
            continue
        opt_when = opt.get("when")
        if opt_when and not evaluate_when(opt_when, data):
            continue
        allowed.append(opt.get("value"))
    return allowed


def _check_options(name: str, spec: Dict[str, Any], value: Any, data: Dict[str, Any]) -> List[FieldError]:
    params = spec.get("parameters")
    if not isinstance(params, dict) or "options" not in params:
        return []
    # A single select takes one value and a multiple select a list, even when
    # every submitted item is itself a valid option.
    field_type = spec.get("fieldType")
    if field_type in (_SINGLE_SELECT_FIELD_TYPE, _ENTITY_TYPE_FIELD_TYPE) and isinstance(value, list):
        return [FieldError(name, "must be a single option, not a list")]
    if field_type == _MULTIPLE_SELECT_FIELD_TYPE and not isinstance(value, list):
        return [FieldError(name, "must be a list of options")]

    allowed = _allowed_option_values(params["options"], data)
    if allowed is None:
        return []

    selected = value if isinstance(value, list) else [value]
    errors: List[FieldError] = []
    for item in selected:
        if item not in allowed:
            errors.append(
                FieldError(name, f"{item!r} is not one of the allowed options {allowed}")
            )
    return errors


def _is_bound(bound: Any) -> bool:
    return isinstance(bound, (int, float)) and not isinstance(bound, bool)


def _check_bounds(name: str, spec: Dict[str, Any], value: Any) -> List[FieldError]:
    """Apply inclusive ``parameters.min`` / ``parameters.max`` bounds.

    What is bounded depends on the submitted value, not the ``fieldType``, so
    any field carrying ``min``/``max`` is checked the same way:

    * a number is bounded by its value;
    * a string by its length in characters;
    * a list by its number of items.

    Other values (booleans, objects, ...) are not bounded.
    """
    params = spec.get("parameters")
    if not isinstance(params, dict):
        return []
    minimum = params.get("min")
    maximum = params.get("max")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        measured = value
        too_small = f"must be >= {minimum}"
        too_large = f"must be <= {maximum}"
    elif isinstance(value, str):
        measured = len(value)
        too_small = f"must be at least {minimum} characters"
        too_large = f"must be at most {maximum} characters"
    elif isinstance(value, (list, tuple)):
        measured = len(value)
        too_small = f"must have at least {minimum} items"
        too_large = f"must have at most {maximum} items"
    else:
        return []

    errors: List[FieldError] = []
    if _is_bound(minimum) and measured < minimum:
        errors.append(FieldError(name, too_small))
    if _is_bound(maximum) and measured > maximum:
        errors.append(FieldError(name, too_large))
    return errors


def _resolve_column_ref(path: str, data: Dict[str, Any]) -> List[Any]:
    """Resolve one ``columnNames`` ref path against the submitted ``data``.

    A plain path (``"condition_column"``) yields that field's value; a scalar
    becomes a one-element list, a list is returned as-is. An array-projection
    path (``"control_variables[].column"``) collects the ``column`` value from
    each item of the referenced list. ``None``/absent values are dropped, so a
    field the user has not filled in contributes no expected column.
    """
    if "[]." in path:
        field_name, sub_key = path.split("[].", 1)
        items = data.get(field_name)
        if not isinstance(items, list):
            return []
        return [
            item.get(sub_key)
            for item in items
            if isinstance(item, dict) and item.get(sub_key) is not None
        ]

    value = data.get(path)
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v is not None]
    return [value]


def _check_multiple_column_values(
    name: str, rule: Dict[str, Any], value: Any, data: Dict[str, Any]
) -> List[FieldError]:
    """Ensure each referenced column holds at least two different values.

    ``parameters.values`` names the columns, resolved from ``data`` like a
    ``columnNames`` ref: a field holding a column name (``"condition_column"``)
    or an array projection (``"control_variables[].column"``). ``None`` and
    ``""`` cells don't count as values. Columns missing from the table, and a
    value that is not a table, are left to the other checks.
    """
    path = _rule_params(rule).get("values")
    if not isinstance(path, str) or not isinstance(value, dict):
        return []
    errors: List[FieldError] = []
    seen: set = set()
    for column in _resolve_column_ref(path, data):
        cells = value.get(column)
        if column in seen or not isinstance(cells, list):
            continue
        seen.add(column)
        distinct: List[Any] = []
        for cell in cells:
            if cell is not None and cell != "" and cell not in distinct:
                distinct.append(cell)
        if len(distinct) < 2:
            found = f"only {distinct[0]!r}" if distinct else "none"
            errors.append(FieldError(name, f"column {column!r} must have at least 2 different values, got {found}"))
    return errors


def _check_required_columns(name: str, spec: Dict[str, Any], value: Any, data: Dict[str, Any]) -> List[FieldError]:
    """Ensure a table carries the columns named by ``parameters.columnNames``.

    ``columnNames.ref`` lists the fields (or array projections) that hold the
    column names this table must contain — e.g. the selected condition column
    and each control variable's column. The referenced values are resolved
    from ``data`` and every one must appear as a key in the submitted table.
    Refs that resolve to nothing (unfilled fields) impose no requirement, and a
    value that is not a table is left to the shape checks.
    """
    params = spec.get("parameters")
    if not isinstance(params, dict):
        return []
    column_names = params.get("columnNames")
    if not isinstance(column_names, dict):
        return []
    refs = column_names.get("ref")
    if isinstance(refs, str):
        refs = [refs]
    if not isinstance(refs, list):
        return []
    if not isinstance(value, dict):
        return []

    missing: List[Any] = []
    seen: set = set()
    for ref in refs:
        if not isinstance(ref, str):
            continue
        for column in _resolve_column_ref(ref, data):
            if column not in value and column not in seen:
                seen.add(column)
                missing.append(column)

    if not missing:
        return []
    joined = ", ".join(repr(column) for column in missing)
    return [FieldError(name, f"table columns missing columns: {joined}")]


def _check_value_type(name: str, spec: Dict[str, Any], value: Any) -> Optional[FieldError]:
    """Ensure a Boolean field holds a bool, a Number/NumberRange field a number
    and a DatasetTableValue field a list (or, when ``parameters.multiple`` is
    false, a single value rather than a list or object).

    Then, on any field, a ``parameters.fieldDataType`` fixes the value's type
    (see ``_FIELD_DATA_TYPE_CHECKS``). A ``float`` accepts ints too, since JSON
    sends ``1.0`` as ``1``. Unrecognised data types are ignored.

    ``bool`` is a subclass of ``int`` in Python, so it is explicitly rejected as
    a number. ``None`` is rejected for a number field that has a non-``None``
    default, and otherwise left to the presence checks.
    """
    field_type = spec.get("fieldType")
    if value is None and (field_type not in _NUMBER_FIELD_TYPES or spec.get("default") is None):
        return None
    if field_type == _BOOLEAN_FIELD_TYPE and not isinstance(value, bool):
        return FieldError(name, "must be a boolean")
    if field_type in _NUMBER_FIELD_TYPES and (
        not isinstance(value, (int, float)) or isinstance(value, bool)
    ):
        return FieldError(name, "must be a number")
    if field_type == _DATASET_TABLE_VALUE_FIELD_TYPE:
        params = spec.get("parameters")
        single = isinstance(params, dict) and params.get("multiple") is False
        if single and isinstance(value, (list, tuple, dict)):
            return FieldError(name, "must be a single value")
        if not single and not isinstance(value, list):
            return FieldError(name, "must be a list")
    params = spec.get("parameters")
    data_type = params.get("fieldDataType") if isinstance(params, dict) else None
    check = _FIELD_DATA_TYPE_CHECKS.get(data_type)
    if value is not None and check is not None and not check[0](value):
        return FieldError(name, check[1])
    return None


def _check_table_shape(name: str, value: Any) -> Optional[FieldError]:
    """Ensure a value is a table: an object mapping columns to equal-length lists."""
    if not isinstance(value, dict):
        return FieldError(name, "must be a table (an object mapping column names to lists)")
    columns = [col for col in value.values() if isinstance(col, list)]
    if len(columns) != len(value):
        return FieldError(name, "table columns must be lists")
    if len({len(col) for col in columns}) > 1:
        return FieldError(name, "table columns must all have the same length")
    return None


def _check_control_variables_shape(name: str, value: Any) -> Optional[FieldError]:
    """Ensure a value is a list of objects each carrying ``type`` and ``column``."""
    if not isinstance(value, list) or not all(
        isinstance(item, dict) and "type" in item and "column" in item for item in value
    ):
        return FieldError(
            name, "must be a list of control variables (objects with 'type' and 'column')"
        )
    return None


# Value rules that, on a control-variables field, are checked against each
# control variable's ``column``.
_COLUMN_VALUE_RULES = ("is_equal_to_value", "is_not_equal_to_value")


def _check_control_variable_columns(name: str, rule: Dict[str, Any], value: List[Any]) -> List[FieldError]:
    """Apply ``is_equal_to_value`` / ``is_not_equal_to_value`` to each column.

    E.g. ``is_not_equal_to_value("sample_name")`` forbids any control variable
    from using the ``sample_name`` column. Control variables are numbered
    from 1 in the messages, as a user would count them.
    """
    expected = _rule_params(rule).get("value")
    must_equal = rule.get("name") == "is_equal_to_value"
    errors: List[FieldError] = []
    for number, item in enumerate(value, start=1):
        column = item["column"]
        if must_equal and column != expected:
            errors.append(FieldError(name, f"control variable {number} must use column {expected!r}, not {column!r}"))
        elif not must_equal and column == expected:
            errors.append(FieldError(name, f"control variable {number} must not use column {expected!r}"))
    return errors


def _check_control_variable_types(name: str, spec: Dict[str, Any], value: List[Any]) -> List[FieldError]:
    """Ensure each control variable's ``type`` is one of ``parameters.radioOptions``.

    Control variables are numbered from 1 in the messages, as a user would
    count them. A definition without ``radioOptions`` imposes no restriction.
    """
    params = spec.get("parameters")
    allowed = params.get("radioOptions") if isinstance(params, dict) else None
    if not isinstance(allowed, list):
        return []
    choices = ", ".join(repr(option) for option in allowed)
    return [
        FieldError(
            name,
            f"control variable {number} ({item['column']!r}) has type {item['type']!r}; "
            f"must be one of {choices}",
        )
        for number, item in enumerate(value, start=1)
        if item["type"] not in allowed
    ]


def _check_condition_comparisons_shape(name: str, value: Any) -> List[FieldError]:
    """Ensure a value is ``{"condition_comparison_pairs": [[a, b], ...]}``.

    Every comparison must be a list of exactly two different conditions. Comparisons are
    numbered from 1 in the messages, as a user would count them.
    """
    pairs = value.get("condition_comparison_pairs") if isinstance(value, dict) else None
    if not isinstance(pairs, list):
        return [FieldError(
            name, "must be an object with a 'condition_comparison_pairs' list of [condition, condition] pairs"
        )]
    errors: List[FieldError] = []
    for number, pair in enumerate(pairs, start=1):
        if not isinstance(pair, list):
            errors.append(FieldError(name, f"comparison {number} must be a [condition, condition] pair, got {pair!r}"))
        elif len(pair) != 2:
            errors.append(FieldError(
                name, f"comparison {number} must compare exactly 2 conditions, got {len(pair)}: {pair!r}"
            ))
        elif pair[0] == pair[1]:
            errors.append(FieldError(
                name, f"comparison {number} must compare two different conditions, got {pair!r}"
            ))
    return errors


def _rule_params(rule: Dict[str, Any]) -> Dict[str, Any]:
    params = rule.get("parameters")
    return params if isinstance(params, dict) else {}


def _referenced_values(data: Dict[str, Any], field_name: Any, values_key: Any) -> List[Any]:
    """Collect the comparable values held by a referenced field.

    ``values_key`` is either a plain item key (``"column"``) or an
    array-projection path (``"control_variables[].column"``), whose part after
    ``[].`` is the item key.
    """
    if isinstance(values_key, str) and "[]." in values_key:
        values_key = values_key.split("[].", 1)[1]
    referenced = data.get(field_name)
    if isinstance(referenced, list):
        if values_key is not None:
            return [
                item.get(values_key)
                for item in referenced
                if isinstance(item, dict) and values_key in item
            ]
        return list(referenced)
    if isinstance(referenced, dict) and values_key is not None and values_key in referenced:
        col = referenced[values_key]
        return list(col) if isinstance(col, list) else [col]
    return []


def _check_rule(name: str, rule: Dict[str, Any], value: Any, data: Dict[str, Any]) -> Optional[FieldError]:
    rule_name = rule.get("name")
    params = _rule_params(rule)

    if rule_name == "is_equal_to_value":
        if value != params.get("value"):
            return FieldError(name, f"must equal {params.get('value')!r}")
        return None

    if rule_name == "is_not_equal_to_value":
        if value == params.get("value"):
            return FieldError(name, f"must not equal {params.get('value')!r}")
        return None

    if rule_name == "is_equal_to_value_from_field":
        other = params.get("field")
        if value != data.get(other):
            return FieldError(name, f"must equal the value of {other!r}")
        return None

    if rule_name == "is_not_included_in_values_from_field":
        other = params.get("field")
        candidates = _referenced_values(data, other, params.get("values"))
        if value in candidates:
            return FieldError(name, f"must not be one of the values in {other!r}")
        return None

    if rule_name in ("has_unique_in_column", "has_unique_column_values_in_table"):
        column = params.get("column")
        # These rules operate on a table: an object mapping column names to
        # equal-length value lists. A value that isn't that shape can't satisfy
        # the rule, so report the shape failure.
        shape_error = _check_table_shape(name, value)
        if shape_error is not None:
            return shape_error
        col = value.get(column)
        if isinstance(col, list) and len(col) != len(set(col)):
            return FieldError(name, f"column {column!r} must contain unique values")
        return None

    # is_required is handled by presence logic; unknown/opaque rules are skipped.
    return None
