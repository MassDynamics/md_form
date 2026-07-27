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
* numeric ``parameters.min`` / ``parameters.max`` bounds,
* the value/cross-field ``rules`` (``is_equal_to_value``, etc.),
* dataset-selection fields against a supplied ``datasets`` list (see the
  ``datasets`` argument of :func:`validate_form`).

``fieldType`` is a frontend widget hint rather than a reliable data type, so it
is deliberately not used to type-check values. Rules that cannot be checked from
the data alone are skipped rather than reported, so the validator stays
forward-compatible with new field/rule kinds.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .field_types import FieldType
from .when import evaluate_when

# fieldType of a dataset-selection field (see field_helpers.datasets_field).
_DATASETS_FIELD_TYPE = FieldType.INTENSITY_INPUT_DATASET.value  # "Datasets"

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
      match the field's required ``parameters.type`` (when set), and be in the
      ``COMPLETED`` state.
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
    return errors


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
    return value is None


def _validate_field(name: str, spec: Dict[str, Any], data: Dict[str, Any]) -> List[FieldError]:
    when = spec.get("when")
    # A field gated by an unmet `when` is inactive: skip every check for it.
    if when and not evaluate_when(when, data):
        return []

    rules = _normalize_rules(spec.get("rules"))
    present = name in data and not _is_absent(data.get(name))

    if not present:
        if _has_required_rule(rules):
            return [FieldError(name, "is required")]
        return []

    value = data[name]
    errors: List[FieldError] = []

    errors.extend(_check_options(name, spec, value, data))
    errors.extend(_check_bounds(name, spec, value))
    for rule in rules:
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


def _check_bounds(name: str, spec: Dict[str, Any], value: Any) -> List[FieldError]:
    params = spec.get("parameters")
    if not isinstance(params, dict):
        return []
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return []
    errors: List[FieldError] = []
    minimum = params.get("min")
    maximum = params.get("max")
    if isinstance(minimum, (int, float)) and value < minimum:
        errors.append(FieldError(name, f"must be >= {minimum}"))
    if isinstance(maximum, (int, float)) and value > maximum:
        errors.append(FieldError(name, f"must be <= {maximum}"))
    return errors


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


def _rule_params(rule: Dict[str, Any]) -> Dict[str, Any]:
    params = rule.get("parameters")
    return params if isinstance(params, dict) else {}


def _referenced_values(data: Dict[str, Any], field_name: Any, values_key: Any) -> List[Any]:
    """Collect the comparable values held by a referenced field."""
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
