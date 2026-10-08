import json
import os
from typing import List, Optional, Literal

import pytest

from field_utils.form_validator import (
    FormValidationError,
    is_valid_form,
    validate_form,
)
from pydantic import BaseModel

from field_utils import (
    MdDatasetBaseModel,
    boolean_field,
    condition_column_field,
    condition_comparisons_field,
    control_variables_field,
    dataset_table_value_field,
    experiment_design_field,
    intensity_input_dataset_field,
    intensity_input_datasets_field,
    has_multiple_column_values_from_field_in_table,
    has_unique_column_values_in_table,
    is_not_included_in_values_from_field,
    is_required,
    multiple_select_field,
    number_field,
    numberrange_field,
    plot_size_field,
    radio_selection_field,
    select_field,
    is_equal_to_value,
    is_not_equal_to_value,
)
from field_utils.field_helpers import EntityType, FieldDataType, entity_type_field
from field_utils.when import When
from translate_payload import translate_payload

TUTORIAL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "tutorial",
)


def _errors(result):
    return {(e.field, e.message) for e in result.errors}


class TestRequired:
    definition = {
        "properties": {
            "name": {"fieldType": "String", "rules": [{"name": "is_required"}]},
            "notes": {"fieldType": "String"},
        }
    }

    def test_valid_when_required_present(self):
        assert validate_form(self.definition, {"name": "x"}).is_valid

    def test_invalid_when_required_missing(self):
        result = validate_form(self.definition, {})
        assert not result.is_valid
        assert ("name", "is required") in _errors(result)

    def test_invalid_when_required_none(self):
        result = validate_form(self.definition, {"name": None})
        assert not result.is_valid

    def test_optional_field_absent_is_fine(self):
        assert validate_form(self.definition, {"name": "x"}).is_valid


class TestRequiredOnlyByRule:
    """Only an ``is_required`` rule makes a field required, whatever its default."""

    class _Form(MdDatasetBaseModel):
        filter_method: Optional[str] = select_field(
            default=None,
            when=When.is_present("input_datasets"),
            parameters={
                "options": [
                    {"name": "None", "value": None},
                    {"name": "filter samples and entities", "value": "goodSamplesGenes"},
                ],
            },
        )
        network_type: str = select_field(default="signed", options=["signed", "unsigned"])
        log_transform: bool = boolean_field(default=True)
        flag: Optional[bool] = boolean_field()

    definition = translate_payload(_Form.model_json_schema())

    def test_null_option_with_null_default_is_valid(self):
        # Regression: "default": null plus options was treated as required, so
        # choosing the "None" option failed with "filter_method: is required".
        data = {"input_datasets": ["ds"], "filter_method": None}
        assert validate_form(self.definition, data).is_valid

    def test_fields_with_defaults_may_be_left_out(self):
        assert validate_form(self.definition, {"input_datasets": ["ds"]}).is_valid

    def test_null_boolean_without_rule_is_valid(self):
        assert validate_form(self.definition, {"log_transform": None, "flag": None}).is_valid

    def test_is_required_rule_still_enforced(self):
        definition = {
            "properties": {
                "mode": {
                    "fieldType": "String",
                    "default": "a",
                    "parameters": {"options": [{"name": "a", "value": "a"}]},
                    "rules": [{"name": "is_required"}],
                },
            }
        }
        assert _errors(validate_form(definition, {})) == {("mode", "is required")}


class TestConditionalRequired:
    definition = {
        "properties": {
            "mode": {
                "fieldType": "String",
                "parameters": {"options": [{"name": "skip", "value": "skip"},
                                           {"name": "batch", "value": "batch"}]},
            },
            "batch_variables": {
                "fieldType": "PairwiseControlVariables",
                "rules": [{"name": "is_required"}],
                "when": {"property": "mode", "equals": "batch"},
            },
        }
    }

    def test_not_required_when_condition_unmet(self):
        assert validate_form(self.definition, {"mode": "skip"}).is_valid

    def test_required_when_condition_met(self):
        result = validate_form(self.definition, {"mode": "batch"})
        assert ("batch_variables", "is required") in _errors(result)

    def test_provided_when_condition_met(self):
        assert validate_form(
            self.definition,
            {"mode": "batch", "batch_variables": [{"type": "categorical", "column": "v1"}]},
        ).is_valid

    def test_inactive_field_is_skipped(self):
        # batch_variables carries a disallowed option, but its `when` is unmet
        # so it is inactive and every check on it is skipped.
        definition = {
            "properties": {
                "mode": {"fieldType": "String"},
                "batch_variables": {
                    "fieldType": "String",
                    "parameters": {"options": [{"name": "a", "value": "a"}]},
                    "when": {"property": "mode", "equals": "batch"},
                },
            }
        }
        assert validate_form(definition, {"mode": "skip", "batch_variables": "nope"}).is_valid
        assert not validate_form(definition, {"mode": "batch", "batch_variables": "nope"}).is_valid


class TestBounds:
    definition = {
        "properties": {
            "p": {"fieldType": "Number", "parameters": {"min": 0.0, "max": 1.0}},
        }
    }

    def test_within(self):
        assert validate_form(self.definition, {"p": 0.5}).is_valid

    def test_below(self):
        result = validate_form(self.definition, {"p": -1})
        assert ("p", "must be >= 0.0") in _errors(result)

    def test_above(self):
        result = validate_form(self.definition, {"p": 2})
        assert ("p", "must be <= 1.0") in _errors(result)


class TestNumberBounds:
    """For a number, ``min``/``max`` bound the value itself (inclusive)."""

    definition = {
        "properties": {
            "n": {"fieldType": "Number", "parameters": {"min": 4, "max": 10}},
        }
    }

    @pytest.mark.parametrize("value", [4, 4.5, 7, 10])
    def test_within_bounds_is_valid(self, value):
        assert validate_form(self.definition, {"n": value}).is_valid

    @pytest.mark.parametrize("value", [3, 3.99, -5, 0])
    def test_below_min_is_invalid(self, value):
        result = validate_form(self.definition, {"n": value})
        assert _errors(result) == {("n", "must be >= 4")}

    @pytest.mark.parametrize("value", [11, 10.01, 1000])
    def test_above_max_is_invalid(self, value):
        result = validate_form(self.definition, {"n": value})
        assert _errors(result) == {("n", "must be <= 10")}

    def test_min_only(self):
        definition = {"properties": {"n": {"fieldType": "Number", "parameters": {"min": 4}}}}
        assert validate_form(definition, {"n": 1_000_000}).is_valid
        assert _errors(validate_form(definition, {"n": 3})) == {("n", "must be >= 4")}

    def test_max_only(self):
        definition = {"properties": {"n": {"fieldType": "Number", "parameters": {"max": 10}}}}
        assert validate_form(definition, {"n": -1_000_000}).is_valid
        assert _errors(validate_form(definition, {"n": 11})) == {("n", "must be <= 10")}

    def test_boolean_is_not_bounded_as_a_number(self):
        definition = {"properties": {"b": {"fieldType": "Boolean", "parameters": {"min": 4, "max": 10}}}}
        assert validate_form(definition, {"b": True}).is_valid
        assert validate_form(definition, {"b": False}).is_valid


class TestBooleanType:
    """A Boolean field's value must be a bool; ``None`` only fails when required."""

    definition = {
        "properties": {
            "flag": {"fieldType": "Boolean"},
            "required_flag": {"fieldType": "Boolean", "rules": [{"name": "is_required"}]},
        }
    }

    @pytest.mark.parametrize("value", [True, False])
    def test_bool_is_valid(self, value):
        assert validate_form(self.definition, {"flag": value, "required_flag": value}).is_valid

    @pytest.mark.parametrize("value", [1, 0, 1.0, "true", "false", "yes", "", [], {}, [True], {"value": True}])
    def test_non_bool_is_invalid(self, value):
        result = validate_form(self.definition, {"flag": value, "required_flag": True})
        assert _errors(result) == {("flag", "must be a boolean")}

    def test_none_is_valid_when_optional(self):
        assert validate_form(self.definition, {"flag": None, "required_flag": True}).is_valid

    def test_missing_is_valid_when_optional(self):
        assert validate_form(self.definition, {"required_flag": True}).is_valid

    def test_none_is_invalid_when_required(self):
        result = validate_form(self.definition, {"required_flag": None})
        assert _errors(result) == {("required_flag", "is required")}

    def test_non_bool_is_invalid_when_required(self):
        result = validate_form(self.definition, {"required_flag": "true"})
        assert _errors(result) == {("required_flag", "must be a boolean")}

    def test_empty_string_is_invalid_when_required(self):
        result = validate_form(self.definition, {"required_flag": ""})
        assert _errors(result) == {("required_flag", "must be a boolean")}

    def test_non_bool_ignored_when_inactive(self):
        definition = {
            "properties": {
                "mode": {"fieldType": "String"},
                "flag": {"fieldType": "Boolean", "when": {"property": "mode", "equals": "on"}},
            }
        }
        assert validate_form(definition, {"mode": "off", "flag": "nope"}).is_valid
        assert _errors(validate_form(definition, {"mode": "on", "flag": "nope"})) == {
            ("flag", "must be a boolean")
        }

    def test_helper_built_field(self):
        class _Form(MdDatasetBaseModel):
            flag: bool = boolean_field(rules=[is_required()])

        definition = translate_payload(_Form.model_json_schema())
        assert validate_form(definition, {"flag": False}).is_valid
        assert _errors(validate_form(definition, {"flag": "false"})) == {("flag", "must be a boolean")}
        assert _errors(validate_form(definition, {"flag": None})) == {("flag", "is required")}


class TestNumberType:
    """Number and NumberRange fields accept an int or a float, nothing else.

    ``None`` means unset only when the field's default is ``None`` (or it has
    no default); a field with a real default rejects ``None``.
    """

    @pytest.fixture(params=["Number", "NumberRange"])
    def definition(self, request):
        return {
            "properties": {
                "n": {"fieldType": request.param},
                "required_n": {"fieldType": request.param, "rules": [{"name": "is_required"}]},
            }
        }

    @pytest.mark.parametrize("value", [0, 1, -3, 0.0, 0.5, -2.25, 1e10])
    def test_int_or_float_is_valid(self, definition, value):
        assert validate_form(definition, {"n": value, "required_n": value}).is_valid

    @pytest.mark.parametrize("value", ["1", "0.5", "", True, False, [], {}, [1], {"value": 1}])
    def test_non_number_is_invalid(self, definition, value):
        result = validate_form(definition, {"n": value, "required_n": 1})
        assert _errors(result) == {("n", "must be a number")}

    def test_out_of_bounds(self):
        class _Form(MdDatasetBaseModel):
            out_side: Optional[float] = numberrange_field(default=0.05,
                                                   ge=0.0,
                                                   le=1.0,
                                                   interval=0.01, field_data_type=FieldDataType.FLOAT)
        definition = translate_payload(_Form.model_json_schema())
        result = validate_form(definition, {"out_side": -1})
        assert _errors(result) == {("out_side", "must be >= 0.0")}

    class _BoundsForm(MdDatasetBaseModel):
        """The same bounded field, typed with and without ``Optional``."""

        range_plain: float = numberrange_field(
            default=0.05, ge=0.0, le=1.0, interval=0.01, field_data_type=FieldDataType.FLOAT)
        range_optional: Optional[float] = numberrange_field(
            default=0.05, ge=0.0, le=1.0, interval=0.01, field_data_type=FieldDataType.FLOAT)
        number_plain: float = number_field(default=0.05, ge=0.0, le=1.0, field_data_type=FieldDataType.FLOAT)
        number_optional: Optional[float] = number_field(
            default=0.05, ge=0.0, le=1.0, field_data_type=FieldDataType.FLOAT)

    @pytest.mark.parametrize("field", ["range_plain", "range_optional", "number_plain", "number_optional"])
    def test_ge_le_become_min_max_in_translated_payload(self, field):
        # Pydantic nests ge/le inside anyOf for an Optional type, so translate_payload
        # must still lift them out to parameters.min / parameters.max.
        definition = translate_payload(self._BoundsForm.model_json_schema())
        params = definition[field]["parameters"]
        assert params.get("min") == 0.0
        assert params.get("max") == 1.0

    @pytest.mark.parametrize("field", ["range_plain", "range_optional", "number_plain", "number_optional"])
    @pytest.mark.parametrize("value, message", [(-1, "must be >= 0.0"), (1.5, "must be <= 1.0")])
    def test_ge_le_enforced_by_validator(self, field, value, message):
        definition = translate_payload(self._BoundsForm.model_json_schema())
        assert _errors(validate_form(definition, {field: value})) == {(field, message)}

    def test_empty_string_is_invalid_when_required(self, definition):
        assert _errors(validate_form(definition, {"required_n": ""})) == {("required_n", "must be a number")}

    def test_none_is_valid_when_optional_without_default(self, definition):
        assert validate_form(definition, {"n": None, "required_n": 1}).is_valid

    def test_none_is_valid_when_default_is_none(self, definition):
        definition["properties"]["n"]["default"] = None
        assert validate_form(definition, {"n": None, "required_n": 1}).is_valid

    def test_none_is_invalid_when_default_is_set(self, definition):
        definition["properties"]["n"]["default"] = 0.25
        assert _errors(validate_form(definition, {"n": None, "required_n": 1})) == {("n", "must be a number")}

    def test_none_is_required_error_when_required_without_default(self, definition):
        assert _errors(validate_form(definition, {"required_n": None})) == {("required_n", "is required")}

    def test_none_is_invalid_when_required_with_default(self, definition):
        definition["properties"]["required_n"]["default"] = 5
        assert _errors(validate_form(definition, {"required_n": None})) == {("required_n", "must be a number")}

    def test_helper_built_none_default(self):
        # Regression: an unset soft_power sent by the UI as null failed with
        # "must be a number".
        class _Form(MdDatasetBaseModel):
            soft_power: Optional[int] = number_field(default=None, ge=1, le=30, field_data_type=FieldDataType.INT)
            top_variance_fraction: Optional[float] = numberrange_field(default=0.25, ge=0.0, le=1.0, field_data_type=FieldDataType.FLOAT)

        definition = translate_payload(_Form.model_json_schema())
        assert validate_form(definition, {"soft_power": None, "top_variance_fraction": 0.25}).is_valid
        assert _errors(validate_form(definition, {"top_variance_fraction": None})) == {
            ("top_variance_fraction", "must be a number")
        }

    def test_missing_is_valid_when_optional(self, definition):
        assert validate_form(definition, {"required_n": 1}).is_valid

    def test_missing_is_invalid_when_required(self, definition):
        assert _errors(validate_form(definition, {})) == {("required_n", "is required")}

    def test_non_number_is_invalid_when_required(self, definition):
        assert _errors(validate_form(definition, {"required_n": "5"})) == {("required_n", "must be a number")}

    def test_non_number_skips_bounds(self):
        definition = {"properties": {"n": {"fieldType": "Number", "parameters": {"min": 4, "max": 10}}}}
        # A string would otherwise be length-bounded; only the type error is reported.
        assert _errors(validate_form(definition, {"n": "7"})) == {("n", "must be a number")}

    def test_helper_built_fields(self):
        class _Form(MdDatasetBaseModel):
            n: float = number_field(ge=0, le=1, field_data_type=FieldDataType.FLOAT)
            r: float = numberrange_field(default=0.5, ge=0.0, le=1.0, interval=0.1, field_data_type=FieldDataType.FLOAT)

        definition = translate_payload(_Form.model_json_schema())
        assert validate_form(definition, {"n": 1, "r": 0.5}).is_valid
        assert validate_form(definition, {"n": 0.25, "r": 1}).is_valid
        assert _errors(validate_form(definition, {"n": "1", "r": "0.5"})) == {
            ("n", "must be a number"),
            ("r", "must be a number"),
        }


class TestFieldDataType:
    """``parameters.fieldDataType``, when present, fixes the value's type.

    * ``"int"``: an int (not a float, even a whole one like ``5.0``).
    * ``"float"``: an int or a float (JSON sends ``1.0`` as ``1``).
    * ``"boolean"``: a bool.
    * ``"string"``: a str.
    * ``"array"``: a list (items are not checked).
    * ``"object"``: a dict (values are not checked).

    It applies whatever the ``fieldType``. ``None`` follows the usual presence
    rules, and an unrecognised ``fieldDataType`` is ignored.
    """

    @staticmethod
    def _definition(data_type, field_type="Number", **extra):
        return {
            "properties": {
                "v": {"fieldType": field_type, "parameters": {"fieldDataType": data_type}, **extra},
            }
        }

    @pytest.mark.parametrize("value", [0, 5, -3, 10**12])
    def test_int_accepts_int(self, value):
        assert validate_form(self._definition("int"), {"v": value}).is_valid

    @pytest.mark.parametrize("value", [5.5, 5.0, -0.1])
    def test_int_rejects_float(self, value):
        assert _errors(validate_form(self._definition("int"), {"v": value})) == {("v", "must be an int")}

    @pytest.mark.parametrize("value", [0.5, 5.0, 5, -3])
    def test_float_accepts_int_or_float(self, value):
        assert validate_form(self._definition("float"), {"v": value}).is_valid

    @pytest.mark.parametrize("data_type", ["int", "float"])
    @pytest.mark.parametrize("value", ["5", True, [5]])
    def test_non_number_on_number_field_reports_number_error(self, data_type, value):
        # The Number fieldType check runs first, so the error is the same as
        # without fieldDataType.
        assert _errors(validate_form(self._definition(data_type), {"v": value})) == {("v", "must be a number")}

    @pytest.mark.parametrize("value", ["5", True, 5.5])
    def test_int_on_string_field(self, value):
        result = validate_form(self._definition("int", field_type="String"), {"v": value})
        assert _errors(result) == {("v", "must be an int")}

    @pytest.mark.parametrize("value", ["0.5", False])
    def test_float_on_string_field(self, value):
        result = validate_form(self._definition("float", field_type="String"), {"v": value})
        assert _errors(result) == {("v", "must be a float")}

    def test_boolean(self):
        definition = self._definition("boolean", field_type="String")
        assert validate_form(definition, {"v": True}).is_valid
        assert _errors(validate_form(definition, {"v": "true"})) == {("v", "must be a boolean")}
        assert _errors(validate_form(definition, {"v": 1})) == {("v", "must be a boolean")}

    def test_string(self):
        definition = self._definition("string", field_type="Number")
        assert validate_form(self._definition("string", field_type="String"), {"v": "x"}).is_valid
        # A Number field declared as a string still fails the Number check first.
        assert _errors(validate_form(definition, {"v": "x"})) == {("v", "must be a number")}
        assert _errors(validate_form(self._definition("string", field_type="String"), {"v": 5})) == {
            ("v", "must be a string")
        }

    @pytest.mark.parametrize("value", [["a"], [1, 2], [{"a": 1}], [None, "x"], [[1], [2]]])
    def test_array_accepts_list(self, value):
        assert validate_form(self._definition("array", field_type="Multiple"), {"v": value}).is_valid

    @pytest.mark.parametrize("value", ["a", "", 1, 0.5, True, {"a": 1}, {}, ("a",)])
    def test_array_rejects_non_list(self, value):
        result = validate_form(self._definition("array", field_type="Multiple"), {"v": value})
        assert _errors(result) == {("v", "must be an array")}

    def test_empty_array_follows_presence_rules(self):
        # [] is the right type but carries no value, so it only fails when required.
        assert validate_form(self._definition("array", field_type="Multiple"), {"v": []}).is_valid
        required = self._definition("array", field_type="Multiple", rules=[{"name": "is_required"}])
        assert _errors(validate_form(required, {"v": []})) == {("v", "is required")}

    def test_array_bounds_still_apply(self):
        definition = self._definition("array", field_type="Multiple")
        definition["properties"]["v"]["parameters"].update({"min": 2, "max": 3})
        assert validate_form(definition, {"v": ["a", "b"]}).is_valid
        assert _errors(validate_form(definition, {"v": ["a"]})) == {("v", "must have at least 2 items")}
        assert _errors(validate_form(definition, {"v": "ab"})) == {("v", "must be an array")}

    @pytest.mark.parametrize("value", [{"a": 1}, {"sample_name": ["s1"]}, {"nested": {"x": [1]}}])
    def test_object_accepts_dict(self, value):
        assert validate_form(self._definition("object", field_type="String"), {"v": value}).is_valid

    @pytest.mark.parametrize("value", ["a", "", "{}", 1, 0.5, False, ["a"], [], [{"a": 1}]])
    def test_object_rejects_non_dict(self, value):
        result = validate_form(self._definition("object", field_type="String"), {"v": value})
        assert _errors(result) == {("v", "must be an object")}

    def test_empty_object_follows_presence_rules(self):
        assert validate_form(self._definition("object", field_type="String"), {"v": {}}).is_valid
        required = self._definition("object", field_type="String", rules=[{"name": "is_required"}])
        assert _errors(validate_form(required, {"v": {}})) == {("v", "is required")}

    def test_object_with_only_empty_values_is_absent(self):
        # Matches the existing presence rule: {"a": []} carries no value.
        required = self._definition("object", field_type="String", rules=[{"name": "is_required"}])
        assert _errors(validate_form(required, {"v": {"a": []}})) == {("v", "is required")}

    @pytest.mark.parametrize("data_type", ["array", "object"])
    def test_array_and_object_none_follows_presence_rules(self, data_type):
        assert validate_form(self._definition(data_type, field_type="String"), {"v": None}).is_valid
        required = self._definition(data_type, field_type="String", rules=[{"name": "is_required"}])
        assert _errors(validate_form(required, {"v": None})) == {("v", "is required")}

    def test_array_on_number_field_reports_number_error(self):
        # The Number fieldType check still runs first.
        assert _errors(validate_form(self._definition("array"), {"v": [1]})) == {("v", "must be a number")}

    def test_object_on_sample_metadata_table(self):
        definition = self._definition("object", field_type="SampleMetadataTable")
        assert validate_form(definition, {"v": {"sample_name": ["s1", "s2"]}}).is_valid
        assert _errors(validate_form(definition, {"v": [["s1"], ["s2"]]})) == {("v", "must be an object")}

    def test_array_on_control_variables(self):
        definition = self._definition("array", field_type="PairwiseControlVariables")
        assert validate_form(definition, {"v": [{"type": "categorical", "column": "batch"}]}).is_valid
        assert _errors(validate_form(definition, {"v": {"control_variables": []}})) == {
            ("v", "must be an array")
        }

    def test_none_follows_presence_rules(self):
        assert validate_form(self._definition("int"), {"v": None}).is_valid
        assert validate_form(self._definition("int"), {}).is_valid
        required = self._definition("int", rules=[{"name": "is_required"}])
        assert _errors(validate_form(required, {"v": None})) == {("v", "is required")}

    def test_none_rejected_when_number_has_default(self):
        definition = self._definition("int", default=4)
        assert _errors(validate_form(definition, {"v": None})) == {("v", "must be a number")}

    def test_unknown_data_type_is_ignored(self):
        assert validate_form(self._definition("decimal"), {"v": 5.5}).is_valid

    def test_inactive_field_is_skipped(self):
        definition = self._definition("int", when={"property": "mode", "equals": "on"})
        assert validate_form(definition, {"mode": "off", "v": 5.5}).is_valid
        assert _errors(validate_form(definition, {"mode": "on", "v": 5.5})) == {("v", "must be an int")}

    def test_type_error_skips_bounds(self):
        definition = self._definition("int")
        definition["properties"]["v"]["parameters"].update({"min": 10})
        assert _errors(validate_form(definition, {"v": 5.5})) == {("v", "must be an int")}

    def test_helper_built_fields(self):
        class _Form(MdDatasetBaseModel):
            min_module_size: int = number_field(default=30, ge=2, field_data_type=FieldDataType.INT)
            tol: Optional[float] = number_field(field_data_type=FieldDataType.FLOAT)
            untyped: Optional[float] = number_field(field_data_type=None)

        definition = translate_payload(_Form.model_json_schema())
        assert validate_form(definition, {"min_module_size": 30, "tol": 1e-10}).is_valid
        assert validate_form(definition, {"min_module_size": 30, "tol": 1}).is_valid
        assert _errors(validate_form(definition, {"min_module_size": 30.5})) == {
            ("min_module_size", "must be an int")
        }
        # Without field_data_type, any number is accepted.
        assert validate_form(definition, {"min_module_size": 30, "untyped": 0.5}).is_valid
        assert validate_form(definition, {"min_module_size": 30, "untyped": 5}).is_valid


class TestDatasetTableValueType:
    """A DatasetTableValue field's value must be a list, so a bare string is rejected."""

    definition = {
        "properties": {
            "v": {"fieldType": "DatasetTableValue"},
            "required_v": {"fieldType": "DatasetTableValue", "rules": [{"name": "is_required"}]},
        }
    }

    @pytest.mark.parametrize("value", [["Phospho"], ["Phospho", "Acetyl"]])
    def test_list_is_valid(self, value):
        assert validate_form(self.definition, {"v": value, "required_v": value}).is_valid

    @pytest.mark.parametrize("value", ["Phospho", "", 1, True, {}, {"value": "Phospho"}, ("Phospho",)])
    def test_non_list_is_invalid(self, value):
        result = validate_form(self.definition, {"v": value, "required_v": ["Phospho"]})
        assert _errors(result) == {("v", "must be a list")}

    def test_string_is_invalid_when_required(self):
        result = validate_form(self.definition, {"required_v": "Phospho"})
        assert _errors(result) == {("required_v", "must be a list")}

    def test_none_is_valid_when_optional(self):
        assert validate_form(self.definition, {"v": None, "required_v": ["Phospho"]}).is_valid

    def test_none_is_invalid_when_required(self):
        assert _errors(validate_form(self.definition, {"required_v": None})) == {("required_v", "is required")}

    def test_helper_built_field(self):
        class _Form(MdDatasetBaseModel):
            v: list = dataset_table_value_field(
                table_name="PTM_Metadata", column_name="PTMName", multiple=True, rules=[is_required()]
            )

        definition = translate_payload(_Form.model_json_schema())
        assert validate_form(definition, {"v": ["Phospho"]}).is_valid
        assert _errors(validate_form(definition, {"v": "Phospho"})) == {("v", "must be a list")}

    def test_multiple_true_requires_list(self):
        definition = {"properties": {"v": {"fieldType": "DatasetTableValue", "parameters": {"multiple": True}}}}
        assert validate_form(definition, {"v": ["Phospho"]}).is_valid
        assert _errors(validate_form(definition, {"v": "Phospho"})) == {("v", "must be a list")}


class TestSingleDatasetTableValueType:
    """With ``parameters.multiple`` false, a DatasetTableValue holds one value, not a list."""

    definition = {
        "properties": {
            "v": {"fieldType": "DatasetTableValue", "parameters": {"multiple": False}},
            "required_v": {
                "fieldType": "DatasetTableValue",
                "parameters": {"multiple": False},
                "rules": [{"name": "is_required"}],
            },
        }
    }

    @pytest.mark.parametrize("value", ["Phospho", 1, 2.5])
    def test_single_value_is_valid(self, value):
        assert validate_form(self.definition, {"v": value, "required_v": value}).is_valid

    @pytest.mark.parametrize("value", [["Phospho"], [], {}, {"value": "Phospho"}, ("Phospho",)])
    def test_list_or_object_is_invalid(self, value):
        result = validate_form(self.definition, {"v": value, "required_v": "Phospho"})
        assert _errors(result) == {("v", "must be a single value")}

    def test_none_is_valid_when_optional(self):
        assert validate_form(self.definition, {"v": None, "required_v": "Phospho"}).is_valid

    def test_none_is_invalid_when_required(self):
        assert _errors(validate_form(self.definition, {"required_v": None})) == {("required_v", "is required")}

    def test_empty_string_is_invalid_when_required(self):
        assert _errors(validate_form(self.definition, {"required_v": ""})) == {("required_v", "is required")}

    def test_helper_built_field(self):
        class _Form(MdDatasetBaseModel):
            v: str = dataset_table_value_field(
                table_name="PTM_Metadata", column_name="PTMName", multiple=False, rules=[is_required()]
            )

        definition = translate_payload(_Form.model_json_schema())
        assert validate_form(definition, {"v": "Phospho"}).is_valid
        assert _errors(validate_form(definition, {"v": ["Phospho"]})) == {("v", "must be a single value")}


class TestStringBounds:
    """For a string, ``min``/``max`` bound its length (inclusive)."""

    definition = {
        "properties": {
            "s": {"fieldType": "String", "parameters": {"min": 2, "max": 5}},
        }
    }

    @pytest.mark.parametrize("value", ["ab", "abc", "abcde"])
    def test_within_bounds_is_valid(self, value):
        assert validate_form(self.definition, {"s": value}).is_valid

    def test_too_short_is_invalid(self):
        result = validate_form(self.definition, {"s": "a"})
        assert _errors(result) == {("s", "must be at least 2 characters")}

    def test_too_long_is_invalid(self):
        result = validate_form(self.definition, {"s": "abcdef"})
        assert _errors(result) == {("s", "must be at most 5 characters")}

    def test_numeric_string_is_bounded_by_length_not_value(self):
        # "100" is 3 characters long: within 2..5 even though 100 > 5.
        assert validate_form(self.definition, {"s": "100"}).is_valid
        # "1" is 1 character long: too short even though 1 is a small number.
        result = validate_form(self.definition, {"s": "1"})
        assert _errors(result) == {("s", "must be at least 2 characters")}

    def test_empty_string_is_absent_not_too_short(self):
        # An empty string counts as not provided, so an optional field passes...
        assert validate_form(self.definition, {"s": ""}).is_valid
        # ...and a required one reports "is required", not a length error.
        required = {"properties": {"s": {
            "fieldType": "String",
            "rules": [{"name": "is_required"}],
            "parameters": {"min": 2, "max": 5},
        }}}
        assert _errors(validate_form(required, {"s": ""})) == {("s", "is required")}


class TestListBounds:
    """For a list, ``min``/``max`` bound the number of items (inclusive)."""

    definition = {
        "properties": {
            "l": {"fieldType": "Multiple", "parameters": {"min": 2, "max": 4}},
        }
    }

    @pytest.mark.parametrize("value", [["a", "b"], ["a", "b", "c"], ["a", "b", "c", "d"]])
    def test_within_bounds_is_valid(self, value):
        assert validate_form(self.definition, {"l": value}).is_valid

    def test_too_few_items_is_invalid(self):
        result = validate_form(self.definition, {"l": ["a"]})
        assert _errors(result) == {("l", "must have at least 2 items")}

    def test_too_many_items_is_invalid(self):
        result = validate_form(self.definition, {"l": ["a", "b", "c", "d", "e"]})
        assert _errors(result) == {("l", "must have at most 4 items")}

    def test_numeric_items_are_bounded_by_count_not_value(self):
        # Two items: within 2..4 even though 100 > 4.
        assert validate_form(self.definition, {"l": [100, 200]}).is_valid
        # Five small numbers: too many items even though each is within 2..4.
        result = validate_form(self.definition, {"l": [2, 3, 3, 3, 4]})
        assert _errors(result) == {("l", "must have at most 4 items")}

    def test_empty_list_is_absent_not_too_short(self):
        assert validate_form(self.definition, {"l": []}).is_valid
        required = {"properties": {"l": {
            "fieldType": "Multiple",
            "rules": [{"name": "is_required"}],
            "parameters": {"min": 2, "max": 4},
        }}}
        assert _errors(validate_form(required, {"l": []})) == {("l", "is required")}

    def test_dataset_selection_is_bounded_by_count(self):
        # A multi-dataset picker (intensity_input_datasets_field) carries its
        # selection limits as parameters.min/max.
        definition = {"properties": {"input_datasets": {
            "fieldType": "Datasets",
            "parameters": {"type": "INTENSITY", "multiple": True, "min": 2, "max": 4},
        }}}
        datasets = [{"id": i, "type": "INTENSITY", "state": "COMPLETED"} for i in "abcde"]

        assert validate_form(definition, {"input_datasets": ["a", "b"]}, datasets=datasets).is_valid
        result = validate_form(definition, {"input_datasets": ["a"]}, datasets=datasets)
        assert _errors(result) == {("input_datasets", "must have at least 2 items")}
        result = validate_form(definition, {"input_datasets": list("abcde")}, datasets=datasets)
        assert _errors(result) == {("input_datasets", "must have at most 4 items")}


class TestOptions:
    definition = {
        "properties": {
            "entity_type": {
                "fieldType": "String",
                "parameters": {"options": [
                    {"name": "peptide", "value": "peptide"},
                    {"name": "protein", "value": "protein"},
                ]},
            },
            "method": {
                "fieldType": "String",
                "parameters": {"options": [
                    {"name": "none", "value": "none"},
                    {"name": "ptm", "value": "ptm",
                     "when": {"property": "entity_type", "equals": "peptide"}},
                ]},
            },
        }
    }

    def test_valid_option(self):
        assert validate_form(self.definition, {"entity_type": "protein"}).is_valid

    def test_invalid_option(self):
        result = validate_form(self.definition, {"entity_type": "mouse"})
        assert not result.is_valid

    def test_option_gated_by_when_available(self):
        assert validate_form(
            self.definition, {"entity_type": "peptide", "method": "ptm"}
        ).is_valid

    def test_option_gated_by_when_unavailable(self):
        result = validate_form(
            self.definition, {"entity_type": "protein", "method": "ptm"}
        )
        assert not result.is_valid


class TestMultipleOptions:
    definition = {
        "properties": {
            "tags": {
                "fieldType": "Multiple",
                "parameters": {"options": [
                    {"name": "a", "value": "a"},
                    {"name": "b", "value": "b"},
                ]},
            },
        }
    }

    def test_all_valid(self):
        assert validate_form(self.definition, {"tags": ["a", "b"]}).is_valid

    def test_one_invalid(self):
        result = validate_form(self.definition, {"tags": ["a", "z"]})
        assert not result.is_valid


class TestSelectField:
    """A single-choice field built with ``select_field``."""

    class _Form(MdDatasetBaseModel):
        entity_type: str = select_field(options=["protein", "peptide"], default="protein")
        required_method: str = select_field(options=["none", "ptm"], rules=[is_required()])
        database: Optional[str] = select_field(
            options={"ref": "entity_type", "cases": {"protein": ["reactome"], "peptide": ["phosphosite"]}},
        )
        filter_method: Optional[str] = select_field(
            default=None,
            parameters={"options": [
                {"name": "None", "value": None},
                {"name": "filter samples and entities", "value": "goodSamplesGenes"},
            ]},
        )
        ptm_threshold_mode: Optional[str] = select_field(
            options=["strict", "loose"],
            when=When.equals("entity_type", "peptide"),
        )

    definition = translate_payload(_Form.model_json_schema())
    base = {"required_method": "none"}

    @pytest.mark.parametrize("value", ["protein", "peptide"])
    def test_valid_option(self, value):
        assert validate_form(self.definition, {**self.base, "entity_type": value}).is_valid

    def test_invalid_option(self):
        result = validate_form(self.definition, {**self.base, "entity_type": "mouse"})
        assert _errors(result) == {("entity_type", "'mouse' is not one of the allowed options ['protein', 'peptide']")}

    def test_options_are_case_sensitive(self):
        result = validate_form(self.definition, {**self.base, "entity_type": "Protein"})
        assert _errors(result) == {("entity_type", "'Protein' is not one of the allowed options ['protein', 'peptide']")}

    def test_optional_field_with_default_may_be_left_out(self):
        assert validate_form(self.definition, self.base).is_valid

    def test_required_field_missing(self):
        assert _errors(validate_form(self.definition, {})) == {("required_method", "is required")}

    @pytest.mark.parametrize("value", [None, ""])
    def test_required_field_empty(self, value):
        assert _errors(validate_form(self.definition, {"required_method": value})) == {
            ("required_method", "is required")
        }

    def test_required_field_invalid_option(self):
        result = validate_form(self.definition, {"required_method": "all"})
        assert _errors(result) == {("required_method", "'all' is not one of the allowed options ['none', 'ptm']")}

    def test_none_option_is_selectable(self):
        assert validate_form(self.definition, {**self.base, "filter_method": None}).is_valid
        assert validate_form(self.definition, {**self.base, "filter_method": "goodSamplesGenes"}).is_valid

    def test_dynamic_options_follow_ref(self):
        assert validate_form(self.definition, {**self.base, "entity_type": "protein", "database": "reactome"}).is_valid
        assert validate_form(
            self.definition, {**self.base, "entity_type": "peptide", "database": "phosphosite"}
        ).is_valid

    def test_dynamic_option_from_other_case_is_invalid(self):
        result = validate_form(self.definition, {**self.base, "entity_type": "protein", "database": "phosphosite"})
        assert _errors(result) == {("database", "'phosphosite' is not one of the allowed options ['reactome']")}

    def test_when_gated_field_skipped_when_inactive(self):
        data = {**self.base, "entity_type": "protein", "ptm_threshold_mode": "anything"}
        assert validate_form(self.definition, data).is_valid

    def test_when_gated_field_checked_when_active(self):
        data = {**self.base, "entity_type": "peptide", "ptm_threshold_mode": "anything"}
        assert _errors(validate_form(self.definition, data)) == {
            ("ptm_threshold_mode", "'anything' is not one of the allowed options ['strict', 'loose']")
        }

    def test_list_is_not_a_single_option(self):
        # A single select takes one value, even if every item is a valid option.
        result = validate_form(self.definition, {**self.base, "entity_type": ["protein"]})
        assert _errors(result) == {("entity_type", "must be a single option, not a list")}


class TestMultipleSelectField:
    """A multiple-choice field built with ``multiple_select_field``."""

    class _Form(MdDatasetBaseModel):
        tags: Optional[List[str]] = multiple_select_field(options=["a", "b", "c"])
        required_tags: List[str] = multiple_select_field(options=["x", "y"], rules=[is_required()])
        defaulted_tags: List[str] = multiple_select_field(options=["a", "b"], default=["a"])
        databases: Optional[List[str]] = multiple_select_field(
            options={"ref": "entity", "cases": {"protein": ["reactome", "go"], "gene": ["kegg"]}},
        )

    definition = translate_payload(_Form.model_json_schema())
    base = {"required_tags": ["x"]}

    @pytest.mark.parametrize("value", [["a"], ["a", "b"], ["c", "a", "b"]])
    def test_valid_selection(self, value):
        assert validate_form(self.definition, {**self.base, "tags": value}).is_valid

    def test_one_invalid_item(self):
        result = validate_form(self.definition, {**self.base, "tags": ["a", "z"]})
        assert _errors(result) == {("tags", "'z' is not one of the allowed options ['a', 'b', 'c']")}

    def test_each_invalid_item_is_reported(self):
        result = validate_form(self.definition, {**self.base, "tags": ["z", "a", "q"]})
        assert _errors(result) == {
            ("tags", "'z' is not one of the allowed options ['a', 'b', 'c']"),
            ("tags", "'q' is not one of the allowed options ['a', 'b', 'c']"),
        }

    @pytest.mark.parametrize("value", [None, []])
    def test_optional_empty_selection_is_valid(self, value):
        assert validate_form(self.definition, {**self.base, "tags": value}).is_valid

    def test_optional_field_may_be_left_out(self):
        assert validate_form(self.definition, self.base).is_valid

    @pytest.mark.parametrize("data", [{}, {"required_tags": None}, {"required_tags": []}])
    def test_required_field_empty(self, data):
        assert _errors(validate_form(self.definition, data)) == {("required_tags", "is required")}

    def test_required_field_invalid_item(self):
        result = validate_form(self.definition, {"required_tags": ["x", "nope"]})
        assert _errors(result) == {("required_tags", "'nope' is not one of the allowed options ['x', 'y']")}

    def test_defaulted_field_checks_submitted_items(self):
        assert validate_form(self.definition, {**self.base, "defaulted_tags": ["a", "b"]}).is_valid
        result = validate_form(self.definition, {**self.base, "defaulted_tags": ["c"]})
        assert _errors(result) == {("defaulted_tags", "'c' is not one of the allowed options ['a', 'b']")}

    def test_dynamic_options_follow_ref(self):
        data = {**self.base, "entity": "protein", "databases": ["reactome", "go"]}
        assert validate_form(self.definition, data).is_valid

    def test_dynamic_option_from_other_case_is_invalid(self):
        data = {**self.base, "entity": "gene", "databases": ["kegg", "go"]}
        assert _errors(validate_form(self.definition, data)) == {
            ("databases", "'go' is not one of the allowed options ['kegg']")
        }

    def test_string_is_not_a_selection(self):
        # A multiple select takes a list, even when the string is a valid option.
        result = validate_form(self.definition, {**self.base, "tags": "a"})
        assert _errors(result) == {("tags", "must be a list of options")}


class TestDynamicOptions:
    definition = {
        "properties": {
            "entity_type": {"fieldType": "String"},
            "db": {
                "fieldType": "String",
                "parameters": {"options": {
                    "ref": "entity_type",
                    "cases": {
                        "protein": [{"name": "reactome", "value": "reactome"}],
                        "gene": [{"name": "go", "value": "go"}],
                    },
                }},
            },
        }
    }

    def test_matches_case(self):
        assert validate_form(
            self.definition, {"entity_type": "protein", "db": "reactome"}
        ).is_valid

    def test_wrong_case(self):
        result = validate_form(
            self.definition, {"entity_type": "protein", "db": "go"}
        )
        assert not result.is_valid

    def test_unknown_case_is_skipped(self):
        # No case for "mouse" -> cannot validate membership, so it passes
        assert validate_form(
            self.definition, {"entity_type": "mouse", "db": "anything"}
        ).is_valid


class TestValueRules:
    def test_is_equal_to_value(self):
        d = {"properties": {"x": {"fieldType": "String",
                                  "rules": [{"name": "is_equal_to_value",
                                             "parameters": {"value": "yes"}}]}}}
        assert validate_form(d, {"x": "yes"}).is_valid
        assert not validate_form(d, {"x": "no"}).is_valid

    def test_is_not_equal_to_value(self):
        d = {"properties": {"x": {"fieldType": "String",
                                  "rules": [{"name": "is_not_equal_to_value",
                                             "parameters": {"value": "sample_name"}}]}}}
        assert validate_form(d, {"x": "condition"}).is_valid
        assert not validate_form(d, {"x": "sample_name"}).is_valid

    def test_is_equal_to_value_from_field(self):
        d = {"properties": {
            "a": {"fieldType": "String"},
            "b": {"fieldType": "String",
                  "rules": [{"name": "is_equal_to_value_from_field",
                             "parameters": {"field": "a"}}]},
        }}
        assert validate_form(d, {"a": "x", "b": "x"}).is_valid
        assert not validate_form(d, {"a": "x", "b": "y"}).is_valid

    def test_is_not_included_in_values_from_field(self):
        d = {"properties": {
            "control_variables": {"fieldType": "PairwiseControlVariables"},
            "condition_column": {"fieldType": "DatasetSampleMetadata",
                                 "rules": [{"name": "is_not_included_in_values_from_field",
                                            "parameters": {"field": "control_variables",
                                                           "values": "control_variables[].column"}}]},
        }}
        assert validate_form(
            d, {"control_variables": [{"type": "categorical", "column": "batch"}],
                "condition_column": "condition"}
        ).is_valid
        assert not validate_form(
            d, {"control_variables": [{"type": "categorical", "column": "condition"}],
                "condition_column": "condition"}
        ).is_valid


class TestUnknownFields:
    definition = {"properties": {"name": {"fieldType": "String"}}}

    def test_allowed_by_default(self):
        assert validate_form(self.definition, {"name": "x", "extra": 1}).is_valid

    def test_rejected_when_strict(self):
        result = validate_form(
            self.definition, {"name": "x", "extra": 1}, allow_unknown=False
        )
        assert not result.is_valid
        assert result.errors[0].__str__() == "extra: unknown field not present in the form definition"
        assert ("extra", "unknown field not present in the form definition") in _errors(result)


class TestApiSurface:
    definition = {"properties": {"name": {"fieldType": "String",
                                           "rules": [{"name": "is_required"}]}}}

    def test_is_valid_form(self):
        assert is_valid_form(self.definition, {"name": "x"}) is True
        assert is_valid_form(self.definition, {}) is False

    def test_raise_on_error(self):
        with pytest.raises(FormValidationError):
            validate_form(self.definition, {}, raise_on_error=True)

    def test_result_is_truthy(self):
        assert validate_form(self.definition, {"name": "x"})
        assert not validate_form(self.definition, {})

    def test_bare_properties_map_accepted(self):
        bare = {"name": {"fieldType": "String", "rules": [{"name": "is_required"}]}}
        assert not validate_form(bare, {}).is_valid
        assert validate_form(bare, {"name": "x"}).is_valid

    def test_non_field_entries_ignored(self):
        d = {"properties": {"name": {"fieldType": "String"}, "$defs": {}}}
        assert validate_form(d, {"name": "x"}).is_valid


class TestTutorialForms:
    def _load(self, filename):
        with open(os.path.join(TUTORIAL_DIR, filename)) as f:
            return json.load(f)

    def test_entity_filtration_valid(self):
        definition = self._load("entity_filtration_form.json")
        data = {"entity_type": "peptide", "filtration_methods": "ptm_localization_probability"}
        assert validate_form(definition, data).is_valid

    def test_entity_filtration_missing_required(self):
        definition = self._load("entity_filtration_form.json")
        result = validate_form(definition, {"entity_type": "protein"})
        assert ("filtration_methods", "is required") in _errors(result)

    def test_entity_filtration_ptm_option_requires_peptide(self):
        definition = self._load("entity_filtration_form.json")
        # ptm_localization_probability is only available when entity_type == peptide
        result = validate_form(
            definition,
            {"entity_type": "protein", "filtration_methods": "ptm_localization_probability"},
        )
        assert not result.is_valid

    datasets = [{"id": "ds1", "name": "Dataset 1", "type": "INTENSITY", "state": "COMPLETED"}]

    def test_transform_intensities_conditional_fields(self):
        definition = self._load("transform_intensities_form.json")
        # input_datasets absent -> the `when: is_present input_datasets` fields are inactive,
        # but input_datasets itself is required.
        result = validate_form(definition, {}, datasets=self.datasets)
        assert ("input_datasets", "is required") in _errors(result)

    def test_transform_intensities_valid(self):
        definition = self._load("transform_intensities_form.json")
        data = {
            "input_datasets": ["ds1"],
            "normalisation_method": "quantile",
            "p_value_threshold": 0.05,
            "apply_log_transform": True,
            "intensity_range": 0.5,
        }
        assert validate_form(definition, data, datasets=self.datasets).is_valid


class TestDifferentialExpressionExample:
    """The payload shape from the feature request."""

    definition = {
        "properties": {
            "input_datasets": {
                "md-field-order": 0,
                "parameters": {
                    "type": "INTENSITY",
                    "width": "large",
                    "multiple": False
                },
                "name": "Select Intensity dataset",
                "group": "Details",
                "rules": [
                    {
                        "name": "is_required"
                    }
                ],
                "fieldType": "Datasets"
            },
            "entity_type": {
                "name": "Entity Type",
                "when": {
                    "property": "input_datasets",
                    "is_present": True
                },
                "group": "Details",
                "rules": [
                    {
                        "name": "is_required"
                    }
                ],
                "default": "protein",
                "fieldType": "EntityType",
                "parameters": {
                    "width": "large",
                    "datasetsSearch": {
                        "ref": "input_datasets"
                    },
                    "options": [
                        {
                            "name": "gene",
                            "value": "gene"
                        },
                        {
                            "name": "peptide",
                            "value": "peptide"
                        },
                        {
                            "name": "protein",
                            "value": "protein"
                        },
                        {
                            "name": "metabolite",
                            "value": "metabolite"
                        },
                        {
                            "name": "ptm",
                            "value": "ptm"
                        }
                    ]
                },
                "description": "Entity type of the intensity dataset",
                "md-field-order": 1
            },
            "condition_column": {
                "name": "Condition Column",
                "when": {
                    "property": "input_datasets",
                    "is_present": True
                },
                "group": "Details",
                "rules": [
                    {
                        "name": "is_not_equal_to_value",
                        "parameters": {
                            "value": "sample_name"
                        }
                    },
                    {
                        "name": "is_not_equal_to_value",
                        "parameters": {
                            "value": None
                        }
                    },
                    {
                        "name": "is_not_included_in_values_from_field",
                        "parameters": {
                            "field": "control_variables",
                            "values": "control_variables[].column"
                        }
                    },
                    {
                        "name": "is_required"
                    }
                ],
                "default": None,
                "fieldType": "DatasetSampleMetadata",
                "parameters": {
                    "width": "large",
                    "datasetsSearch": {
                        "ref": "input_datasets"
                    }
                },
                "md-field-order": 2
            },
            "condition_comparisons": {
                "name": "Condition Comparisons",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "experiment_design",
                            "is_present": True
                        },
                        {
                            "property": "condition_column",
                            "is_present": True
                        }
                    ]
                },
                "group": "Details",
                "rules": [
                    {
                        "name": "is_required"
                    }
                ],
                "default": None,
                "fieldType": "PairwiseConditionComparisons",
                "parameters": {
                    "conditionColumn": {
                        "ref": "condition_column"
                    },
                    "experimentDesign": {
                        "ref": "experiment_design"
                    }
                },
                "description": "The condition comparisons to be performed. The condition levels used to build the contrasts below are taken from the required \"Condition\" column in the samples metadata. The limma model will fit contrasts of the form: \"Condition 1\" vs \"Condition 2\"",
                "md-field-order": 3
            },
            "control_variables": {
                "name": "Control Variables",
                "when": {
                    "property": "input_datasets",
                    "is_present": True
                },
                "group": "Control Variables",
                "rules": [
                    {
                        "name": "is_not_equal_to_value",
                        "parameters": {
                            "value": "sample_name"
                        }
                    }
                ],
                "default": None,
                "fieldType": "PairwiseControlVariables",
                "parameters": {
                    "radioOptions": [
                        "categorical",
                        "numerical"
                    ],
                    "datasetsSearch": {
                        "ref": "input_datasets"
                    }
                },
                "description": "Optional control variables to include in the model. These can be either categorical (e.g., known batches, subject IDs) or numerical (e.g., continuous measurements like age, weight, etc.). Control variables help account for known sources of variation in your data, improving the accuracy of differential abundance analysis. Warning: samples with any missing values in the variables are removed from the analysis. Empty entries are considered as missing values.",
                "md-field-order": 4
            },
            "de_method_gene": {
                "name": "DE Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "gene",
                            "property": "entity_type"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "limma",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "limma",
                            "value": "limma"
                        },
                        {
                            "name": "edgeR",
                            "value": "edgeR"
                        },
                        {
                            "name": "DESeq2",
                            "value": "DESeq2"
                        }
                    ]
                },
                "description": "Differential expression method. limma: Best for pre-normalised data (CPM, TPM, FPKM) or log-transformed intensities. Works well with small sample sizes. edgeR: Designed for raw integer counts. Uses quasi-likelihood F-tests. Requires raw, unnormalised counts. DESeq2: Designed for raw integer counts. Uses Wald tests with shrinkage estimation. Requires raw unnormalised counts.<br><br><b>Note (limma + gene path):</b> limma-trend assumes library sizes vary by less than ~3-fold across samples. If your raw library sizes are more variable than this, limma-trend is not recommended for your data.<br><br>Reference: <a href=\"https://doi.org/10.1186/gb-2014-15-2-r29\">Law, Chen, Shi & Smyth 2014, Genome Biology</a>.",
                "md-field-order": 5
            },
            "de_method_peptide": {
                "name": "DE Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "peptide",
                            "property": "entity_type"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "limma",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "limma",
                            "value": "limma"
                        }
                    ]
                },
                "description": "Differential expression method. For peptide data the limma framework is used.",
                "md-field-order": 6
            },
            "de_method_protein": {
                "name": "DE Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "protein",
                            "property": "entity_type"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "limma",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "limma",
                            "value": "limma"
                        }
                    ]
                },
                "description": "Differential expression method. For protein data the limma framework is used.",
                "md-field-order": 7
            },
            "de_method_metabolite": {
                "name": "DE Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "metabolite",
                            "property": "entity_type"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "limma",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "limma",
                            "value": "limma"
                        }
                    ]
                },
                "description": "Differential expression method. For metabolite data the limma framework is used.",
                "md-field-order": 8
            },
            "de_method_ptm": {
                "name": "DE Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "ptm",
                            "property": "entity_type"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "limma",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "limma",
                            "value": "limma"
                        }
                    ]
                },
                "description": "Differential expression method. For PTM data the limma framework is used.",
                "md-field-order": 9
            },
            "limma_trend": {
                "name": "Limma Trend",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "operator": "or",
                            "conditions": [
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "peptide",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_peptide"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "protein",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_protein"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "metabolite",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_metabolite"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "ptm",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_ptm"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": True,
                "fieldType": "Boolean",
                "parameters": {
                    "label": "Limma Trend"
                },
                "description": "Argument passed to the limma function ebayes(). When TRUE, an intensity-dependent trend is allowed for the prior variances, known as the limma-trend method (Law et al, 2014; Phipson et al, 2016). If FALSE, a costant prior variance is assumed.",
                "md-field-order": 10
            },
            "robust_empirical_bayes": {
                "name": "Robust Empirical Bayes",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "operator": "or",
                            "conditions": [
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "gene",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_gene"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "peptide",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_peptide"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "protein",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_protein"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "metabolite",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_metabolite"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "ptm",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_ptm"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": True,
                "fieldType": "Boolean",
                "parameters": {
                    "label": "Robust Empirical Bayes"
                },
                "description": "Argument passed to the limma function ebayes(). When TRUE, the robust empirical Bayes procedure of Phipson et al (2016) is used. This method is adopted to protect the estimation procedure against hyper or hypo variable genes.",
                "md-field-order": 11
            },
            "fit_separate_models": {
                "name": "Fit Separate Models",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "operator": "or",
                            "conditions": [
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "peptide",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_peptide"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "protein",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_protein"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "metabolite",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_metabolite"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "ptm",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_ptm"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": True,
                "fieldType": "Boolean",
                "parameters": {
                    "label": "Fit Separate Models"
                },
                "description": "When TRUE fits separate limma models for each pairwise comparisons instead of a single model. This approach filters proteins individually for each comparison, reducing the impact of conditions with a high number of missing or imputed values.",
                "md-field-order": 12
            },
            "edger_norm_method": {
                "name": "edgeR Normalisation Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "edgeR",
                            "property": "de_method_gene"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "TMM",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "TMM",
                            "value": "TMM"
                        },
                        {
                            "name": "RLE",
                            "value": "RLE"
                        },
                        {
                            "name": "upperquartile",
                            "value": "upperquartile"
                        },
                        {
                            "name": "none",
                            "value": "none"
                        }
                    ]
                },
                "description": "Library size normalisation method for edgeR. TMM (trimmed mean of M-values) is the default and recommended method. RLE (relative log expression) is an alternative. 'upperquartile' normalises to the 75th percentile. 'none' skips normalisation (use when data is already normalised).",
                "md-field-order": 13
            },
            "deseq2_lfc_shrinkage": {
                "name": "DESeq2 LFC Shrinkage",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "DESeq2",
                            "property": "de_method_gene"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "none",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "none",
                            "value": "none"
                        },
                        {
                            "name": "apeglm",
                            "value": "apeglm"
                        },
                        {
                            "name": "ashr",
                            "value": "ashr"
                        },
                        {
                            "name": "normal",
                            "value": "normal"
                        }
                    ]
                },
                "description": "Log-fold-change shrinkage method for DESeq2. 'none' uses raw maximum-likelihood estimates (default). 'apeglm' (recommended) produces shrunken fold changes that are more reliable for ranking genes. 'ashr' uses adaptive shrinkage. 'normal' uses a normal prior.",
                "md-field-order": 14
            },
            "deseq2_alpha": {
                "name": "DESeq2 FDR Threshold (alpha)",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "DESeq2",
                            "property": "de_method_gene"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": 0.05,
                "fieldType": "NumberRange",
                "parameters": {
                    "width": "large",
                    "interval": 0.01,
                    "min": 0,
                    "max": 1
                },
                "description": "Significance threshold for DESeq2 independent filtering. <b>Set this equal to the FDR threshold you intend to apply downstream</b> (i.e., the AdjPValue cutoff at which you will declare significance). DESeq2's independent filtering optimises the gene rejection set under this alpha; mismatched values silently lose power. A user who keeps the default 0.05 but applies a different downstream FDR threshold (e.g., 0.10) will lose statistical power because the IF cutoff was tuned for the wrong target.<br><br>Reference: <a href=\"https://doi.org/10.1073/pnas.0914005107\">Bourgon, Gentleman & Huber 2010, PNAS</a>.",
                "md-field-order": 15
            },
            "apeglm_seed": {
                "name": "apeglm RNG Seed",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "DESeq2",
                            "property": "de_method_gene"
                        },
                        {
                            "equals": "apeglm",
                            "property": "deseq2_lfc_shrinkage"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": 1,
                "fieldType": "NumberRange",
                "parameters": {
                    "width": "large",
                    "min": 0,
                    "max": 2147483647
                },
                "description": "RNG seed for apeglm shrinkage reproducibility. apeglm's posterior optimisation uses random initialisation for some genes; fixing this seed ensures bit-identical results across runs. Default 1; change only if you want to assess sensitivity of borderline genes to the initialisation.",
                "md-field-order": 16
            },
            "filter_values_criteria": {
                "name": "Filter Values Criteria",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "property": "entity_type",
                            "not_equals": "gene"
                        }
                    ]
                },
                "group": "Filtering Parameters",
                "default": "percentage",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "percentage",
                            "value": "percentage"
                        },
                        {
                            "name": "count",
                            "value": "count"
                        }
                    ]
                },
                "description": "Options: 'percentage' or 'count' of valid values.",
                "md-field-order": 17
            },
            "filter_threshold_percentage": {
                "name": "Filter Threshold Percentage",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "equals": "percentage",
                            "property": "filter_values_criteria"
                        },
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "property": "entity_type",
                            "not_equals": "gene"
                        }
                    ]
                },
                "group": "Filtering Parameters",
                "rules": [
                    {
                        "name": "is_required"
                    }
                ],
                "default": 0.5,
                "fieldType": "NumberRange",
                "parameters": {
                    "width": "large",
                    "interval": 0.01,
                    "min": 0,
                    "max": 1
                },
                "description": "Percentage threshold for filtering. Must be between 0 and 1, inclusive. Only entities with a percentage of valid values larger or equal than the threshold are kept in the analysis. The filtering threshold is evaluated with respect to the 'Filter Valid Values Logic', e.g. by default entities with more than 50% valid values in 'at least one condition' are kept.",
                "md-field-order": 18
            },
            "filter_threshold_count": {
                "name": "Filter Threshold Count",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "equals": "count",
                            "property": "filter_values_criteria"
                        },
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "property": "entity_type",
                            "not_equals": "gene"
                        }
                    ]
                },
                "group": "Filtering Parameters",
                "rules": [
                    {
                        "name": "is_required"
                    }
                ],
                "default": 3,
                "fieldType": "Number",
                "parameters": {
                    "width": "xsmall",
                    "min": 1
                },
                "description": "Minimum count threshold for filtering. Must be greater than or equal to 1. Only entities with a number of valid values larger or equal than the threshold are kept in the analysis. The filtering threshold is evaluated with respect to the 'Filter Valid Values Logic', e.g. by default entities with at least 3 valid values in 'at least one condition' are kept.",
                "md-field-order": 19
            },
            "filter_valid_values_logic": {
                "name": "Filter Valid Values Logic",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "property": "entity_type",
                            "not_equals": "gene"
                        }
                    ]
                },
                "group": "Filtering Parameters",
                "default": "at least one condition",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "all conditions",
                            "value": "all conditions"
                        },
                        {
                            "name": "at least one condition",
                            "value": "at least one condition"
                        },
                        {
                            "name": "full experiment",
                            "value": "full experiment"
                        }
                    ]
                },
                "description": "Logic for filtering. Options: 'all conditions': the count/percentage of valid values must exceed the threshold in all conditions; 'at least one condition' (Default): the count/percentage of valid values must exceed the threshold in at least one condition; 'full experiment': the count/percentage of valid values must exceed the threshold across the whole experiment.",
                "md-field-order": 20
            },
            "experiment_design": {
                "name": "Sample Metadata",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "property": "condition_column",
                            "is_present": True
                        }
                    ]
                },
                "group": "Sample Metadata used for Dataset",
                "rules": [
                    {
                        "name": "has_unique_column_values_in_table",
                        "parameters": {
                            "column": "sample_name"
                        }
                    },
                    {
                        "name": "has_multiple_column_values_from_field_in_table",
                        "parameters": {
                            "values": "condition_column"
                        }
                    },
                    {
                        "name": "has_multiple_column_values_from_field_in_table",
                        "parameters": {
                            "field": "control_variables",
                            "values": "control_variables[].column"
                        }
                    }
                ],
                "default": None,
                "fieldType": "SampleMetadataTable",
                "parameters": {
                    "columnNames": {
                        "ref": [
                            "condition_column",
                            "control_variables[].column"
                        ]
                    },
                    "datasetsSearch": {
                        "ref": "input_datasets"
                    }
                },
                "md-field-order": 21
            }
        } 
    }

    # A valid submission for the real definition above. Note the flat shape the
    # translated form expects: `input_datasets` gates the whole form, and the
    # filter criteria is a plain string alongside a separate threshold field
    # (not the nested dict of some hand-written payloads).
    payload = {
        "input_datasets": ["intensity_dataset_id"],
        "entity_type": "protein",
        "condition_column": "condition",
        "condition_comparisons": {"condition_comparison_pairs": [["Heart", "Brain_1ug"]]},
        "de_method_protein": "limma",
        "limma_trend": True,
        "robust_empirical_bayes": True,
        "fit_separate_models": True,
        "filter_values_criteria": "percentage",
        "filter_threshold_percentage": 0.5,
        "filter_valid_values_logic": "at least one condition",
        "experiment_design": {
            "sample_name": ["Heart_1", "Brain_1ug_1"],
            "condition": ["Heart", "Brain_1ug"],
        },
    }

    # The definition has an input_datasets field (fieldType "Datasets"), so a
    # datasets list must be supplied to validate it.
    datasets = [
        {
            "id": "intensity_dataset_id",
            "name": "Denis uPhos tissue - pg_matrix (condition)",
            "type": "INTENSITY",
            "state": "COMPLETED",
        }
    ]

    def test_example_payload_is_valid(self):
        assert validate_form(self.definition, self.payload, datasets=self.datasets).is_valid

    def test_missing_required_input_datasets(self):
        bad = dict(self.payload)
        del bad["input_datasets"]
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert ("input_datasets", "is required") in _errors(result)

    def test_datasets_required_when_omitted(self):
        # The form has a Datasets field but no datasets list is supplied.
        result = validate_form(self.definition, self.payload)
        assert ("input_datasets", "a datasets list must be provided to validate this field") in _errors(result)

    def test_selected_dataset_not_in_provided_list(self):
        bad = dict(self.payload)
        bad["input_datasets"] = ["some_other_id"]
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert ("input_datasets", "dataset 'some_other_id' is not in the provided datasets") in _errors(result)

    def test_selected_dataset_as_dicts(self):
        # A selection expressed as dataset dicts (with an id) is matched by id.
        ok = dict(self.payload)
        ok["input_datasets"] = [{"id": "intensity_dataset_id", "name": "whatever"}]
        assert validate_form(self.definition, ok, datasets=self.datasets).is_valid

    def test_dataset_wrong_type(self):
        # input_datasets declares parameters.type == "INTENSITY".
        datasets = [{"id": "intensity_dataset_id", "name": "x", "type": "PAIRWISE", "state": "COMPLETED"}]
        result = validate_form(self.definition, self.payload, datasets=datasets)
        assert (
            "input_datasets",
            "dataset 'intensity_dataset_id' must be of type 'INTENSITY', not 'PAIRWISE'",
        ) in _errors(result)

    def test_missing_options_field_without_rule_is_valid(self):
        # A default does not make a field required; only an is_required rule does.
        bad = dict(self.payload)
        del bad['filter_values_criteria']
        assert validate_form(self.definition, bad, datasets=self.datasets).is_valid

    def test_missing_boolean_without_rule_is_valid(self):
        bad = dict(self.payload)
        del bad['limma_trend']
        assert validate_form(self.definition, bad, datasets=self.datasets).is_valid

    def test_dataset_not_completed(self):
        datasets = [{"id": "intensity_dataset_id", "name": "x", "type": "INTENSITY", "state": "PROCESSING"}]
        result = validate_form(self.definition, self.payload, datasets=datasets)
        assert (
            "input_datasets",
            "dataset 'intensity_dataset_id' must be in state 'COMPLETED', not 'PROCESSING'",
        ) in _errors(result)

    def test_bad_de_method_option(self):
        bad = dict(self.payload)
        bad["de_method_protein"] = "not-a-method"
        assert not validate_form(self.definition, bad, datasets=self.datasets).is_valid

    def test_bad_filter_logic_option(self):
        bad = dict(self.payload)
        bad["filter_valid_values_logic"] = "sometimes"
        assert not validate_form(self.definition, bad, datasets=self.datasets).is_valid

    def test_missing_conditional_required(self):
        # filter_threshold_percentage is required only while
        # filter_values_criteria == "percentage" (and the form is active).
        bad = dict(self.payload)
        del bad["filter_threshold_percentage"]
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert ("filter_threshold_percentage", "is required") in _errors(result)

    def test_number_bound_enforced(self):
        # filter_threshold_percentage is a NumberRange with min 0 / max 1.
        bad = dict(self.payload)
        bad["filter_threshold_percentage"] = 5
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert ("filter_threshold_percentage", "must be <= 1") in _errors(result)

    def test_experiment_design_shape(self):
        # experiment_design must be a table (object of column -> list). A
        # list-of-lists is the wrong shape and is rejected via its table rule.
        bad = dict(self.payload)
        bad["experiment_design"] = [
            ["sample_name", "condition"],
            ["Heart_1", "Heart_2"],
            ["Heart", "Heart"],
        ]
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert not result.is_valid
        assert (
            "experiment_design",
            "must be a table (an object mapping column names to lists)",
        ) in _errors(result)

    def test_experiment_design_uneven_columns(self):
        bad = dict(self.payload)
        bad["experiment_design"] = {
            "sample_name": ["Heart_1", "Heart_2"],
            "condition": ["Heart"],
        }
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert ("experiment_design", "table columns must all have the same length") in _errors(result)

    def test_experiment_design_duplicate_sample_names(self):
        # experiment_design declares has_unique_column_values_in_table on the
        # sample_name column, so duplicate sample names are rejected.
        bad = dict(self.payload)
        bad["experiment_design"] = {
            "sample_name": ["Heart_1", "Heart_1"],
            "condition": ["Heart", "Heart"],
        }
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert not result.is_valid
        assert (
            "experiment_design",
            "column 'sample_name' must contain unique values",
        ) in _errors(result)

class TestExperimentDesign:
    """Build the experiment_design field with the real helpers, translate it to a
    form definition, then validate submitted sample-metadata tables against it.
    """

    class _DesignForm(MdDatasetBaseModel):
        condition_column: str = condition_column_field()
        control_variables: dict = control_variables_field()
        experiment_design: dict = experiment_design_field(
            rules=[has_unique_column_values_in_table("sample_name")],
        )

    definition = translate_payload(_DesignForm.model_json_schema())

    def test_valid_experiment_design(self):
        # A well-formed sample-metadata table: every column is an equal-length
        # list and the sample_name column holds unique values.
        data = {
            "condition_column": "condition",
            "experiment_design": {
                "sample_name": ["Heart_1", "Heart_2"],
                "condition": ["Heart", "Brain"],
            },
        }
        assert validate_form(self.definition, data).is_valid

    def test_invalid_experiment_design_uneven_columns(self):
        data = {
            "condition_column": "condition",
            "experiment_design": {
                "sample_name": ["Heart_1", "Heart_2"],
                "condition": ["Heart"],
            },
        }
        result = validate_form(self.definition, data)
        assert not result.is_valid
        assert (
            "experiment_design",
            "table columns must all have the same length",
        ) in _errors(result)

    def test_invalid_missing_cols(self):
        data = {
            "condition_column": "condition",
            "experiment_design": {
                "sample_name": ["Heart_1", "Heart_2"]
            },
        }
        result = validate_form(self.definition, data)
        assert not result.is_valid
        assert (
                   "experiment_design",
                   "table columns missing columns: 'condition'",
               ) in _errors(result)

    def test_row_oriented_array_is_invalid(self):
        # A row-oriented array-of-arrays (header row + data rows) is not a
        # column table and must be rejected outright.
        data = {
            "condition_column": "condition",
            "experiment_design": [
                ["sample_name", "condition"],
                ["Heart_1", "Heart"],
                ["Heart_2", "Brain"],
            ],
        }
        result = validate_form(self.definition, data)
        assert not result.is_valid
        assert (
            "experiment_design",
            "must be a table (an object mapping column names to lists)",
        ) in _errors(result)


class TestSampleMetadataTableShape:
    """The SampleMetadataTable shape is enforced whenever the field is active
    and filled in, even for a stale definition carrying no rules/parameters --
    matching the empty-``rules``/empty-``parameters`` shape seen in prod.
    """

    definition = {
        "properties": {
            "experiment_design": {
                "when": {},
                "rules": [],
                "default": None,
                "fieldType": "SampleMetadataTable",
                "parameters": {},
            }
        }
    }

    def test_array_of_arrays_rejected_without_rules(self):
        data = {
            "experiment_design": [
                ["sample_name", "condition"],
                ["Heart_1", "Heart"],
            ]
        }
        result = validate_form(self.definition, data)
        assert not result.is_valid
        assert (
            "experiment_design",
            "must be a table (an object mapping column names to lists)",
        ) in _errors(result)

    def test_column_dict_valid_without_rules(self):
        data = {
            "experiment_design": {
                "sample_name": ["Heart_1", "Heart_2"],
                "condition": ["Heart", "Brain"],
            }
        }
        assert validate_form(self.definition, data).is_valid

    def test_inactive_field_skips_shape_check(self):
        # A field gated off by an unmet `when` is inactive: its (malformed)
        # value must not be shape-checked.
        gated = {
            "properties": {
                "mode": {"fieldType": "String", "parameters": {}},
                "experiment_design": {
                    "when": {"property": "mode", "equals": "advanced"},
                    "rules": [],
                    "default": None,
                    "fieldType": "SampleMetadataTable",
                    "parameters": {},
                },
            }
        }
        data = {
            "mode": "basic",
            "experiment_design": [["sample_name"], ["Heart_1"]],
        }
        assert validate_form(gated, data).is_valid


class TestConditionComparisonsRequired:
    """A required PairwiseConditionComparisons field built with the real helper.

    An empty ``{}`` submission carries no comparisons, so it counts as absent
    and must fail the ``is_required`` check.
    """

    class _Form(MdDatasetBaseModel):
        condition_comparisons: dict = condition_comparisons_field(rules=[is_required()])

    definition = translate_payload(_Form.model_json_schema())

    def test_empty_dict_is_invalid(self):
        result = validate_form(self.definition, {"condition_comparisons": {}})
        assert not result.is_valid
        assert ("condition_comparisons", "is required") in _errors(result)

    def test_no_pairs_given(self):
        result = validate_form(self.definition, {"condition_comparisons": {"condition_comparison_pairs": []}})
        assert not result.is_valid
        assert ("condition_comparisons", "is required") in _errors(result)
        result = validate_form(self.definition, {"condition_comparisons": {"condition_comparison_pairs": [[]]}})
        assert not result.is_valid
        assert ("condition_comparisons", "is required") in _errors(result)

    SHAPE_ERROR = "must be an object with a 'condition_comparison_pairs' list of [condition, condition] pairs"

    def test_too_many_items(self):
        data = {
            "condition_comparisons": {
                "condition_comparison_pairs": [["Heart", "Brain", "somethingElse"]],
            }
        }
        result = validate_form(self.definition, data)
        assert not result.is_valid
        assert _errors(result) == {(
            "condition_comparisons",
            "comparison 1 must compare exactly 2 conditions, got 3: ['Heart', 'Brain', 'somethingElse']",
        )}

    def test_too_few_items(self):
        data = {
            "condition_comparisons": {
                "condition_comparison_pairs": [["Heart"]],
            }
        }
        result = validate_form(self.definition, data)
        assert not result.is_valid
        assert _errors(result) == {
            ("condition_comparisons", "comparison 1 must compare exactly 2 conditions, got 1: ['Heart']"),
        }

    def test_duplicate_items(self):
        data = {
            "condition_comparisons": {
                "condition_comparison_pairs": [["Heart", "Heart"]],
            }
        }
        result = validate_form(self.definition, data)
        assert not result.is_valid
        assert _errors(result) == {
            ("condition_comparisons", "comparison 1 must compare two different conditions, got ['Heart', 'Heart']"),
        }

    def test_each_bad_comparison_is_reported_by_number(self):
        data = {
            "condition_comparisons": {
                "condition_comparison_pairs": [["Heart", "Brain"], ["Liver"], [], ["A", "B", "C"]],
            }
        }
        assert _errors(validate_form(self.definition, data)) == {
            ("condition_comparisons", "comparison 2 must compare exactly 2 conditions, got 1: ['Liver']"),
            ("condition_comparisons", "comparison 3 must compare exactly 2 conditions, got 0: []"),
            ("condition_comparisons", "comparison 4 must compare exactly 2 conditions, got 3: ['A', 'B', 'C']"),
        }

    def test_comparison_that_is_not_a_list(self):
        data = {"condition_comparisons": {"condition_comparison_pairs": [["Heart", "Brain"], "Heart vs Brain"]}}
        assert _errors(validate_form(self.definition, data)) == {
            ("condition_comparisons", "comparison 2 must be a [condition, condition] pair, got 'Heart vs Brain'"),
        }

    @pytest.mark.parametrize(
        "value",
        [
            [["Heart", "Brain"]],
            {"pairs": [["Heart", "Brain"]]},
            {"condition_comparison_pairs": "Heart vs Brain"},
            {"condition_comparison_pairs": {"Heart": "Brain"}},
            "Heart vs Brain",
        ],
    )
    def test_wrong_shape(self, value):
        assert _errors(validate_form(self.definition, {"condition_comparisons": value})) == {
            ("condition_comparisons", self.SHAPE_ERROR),
        }

    def test_several_valid_pairs(self):
        data = {"condition_comparisons": {"condition_comparison_pairs": [["Heart", "Brain"], ["Liver", "Brain"]]}}
        assert validate_form(self.definition, data).is_valid

    def test_optional_field_is_also_shape_checked(self):
        class _Form(MdDatasetBaseModel):
            condition_comparisons: Optional[dict] = condition_comparisons_field()

        definition = translate_payload(_Form.model_json_schema())
        assert validate_form(definition, {}).is_valid
        assert validate_form(definition, {"condition_comparisons": {"condition_comparison_pairs": [[]]}}).is_valid
        assert _errors(validate_form(definition, {"condition_comparisons": {"condition_comparison_pairs": [["A"]]}})) == {
            ("condition_comparisons", "comparison 1 must compare exactly 2 conditions, got 1: ['A']"),
        }

    def test_populated_is_valid(self):
            data = {
                "condition_comparisons": {
                    "condition_comparison_pairs": [["Heart", "Brain"]],
                }
            }
            assert validate_form(self.definition, data).is_valid


class TestControlVariables:
    """PairwiseControlVariables built with the real helpers.

    A control-variables value is a flat list of objects:
    ``[{"type": "categorical", "column": "batch"}]``. A wrapped object such as
    ``{"control_variables": [...]}`` is rejected. Each entry's ``column`` must
    appear in the sample-metadata table and must not be the selected condition
    column.
    """

    SHAPE_ERROR = "must be a list of control variables (objects with 'type' and 'column')"

    class _Form(MdDatasetBaseModel):
        condition_column: str = condition_column_field(
            rules=[
                is_not_included_in_values_from_field("control_variables", "control_variables[].column")
            ],
        )
        control_variables: list = control_variables_field(
            rules=[
                is_not_equal_to_value("sample_name"),
            ],
        )
        experiment_design: dict = experiment_design_field()

    class _RequiredForm(MdDatasetBaseModel):
        control_variables: list = control_variables_field(rules=[is_required()])

    definition = translate_payload(_Form.model_json_schema())
    required_definition = translate_payload(_RequiredForm.model_json_schema())

    def test_populated_is_valid(self):
        data = {
            "condition_column": "condition",
            "control_variables": [{"type": "categorical", "column": "batch"}],
            "experiment_design": {
                "sample_name": ["Heart_1", "Heart_2"],
                "condition": ["Heart", "Brain"],
                "batch": ["b1", "b2"],
            },
        }
        assert validate_form(self.definition, data).is_valid

    def test_cannot_be_sample_name(self):
        data = {
            "control_variables": [{"type": "categorical", "column": "sample_name"}],
        }
        form = validate_form(self.definition, data)
        assert not form.is_valid
        assert _errors(form) == {("control_variables", "control variable 1 must not use column 'sample_name'")}

    def test_each_sample_name_column_is_reported_by_number(self):
        data = {"control_variables": [
            {"type": "categorical", "column": "batch"},
            {"type": "numerical", "column": "sample_name"},
        ]}
        assert _errors(validate_form(self.definition, data)) == {
            ("control_variables", "control variable 2 must not use column 'sample_name'"),
        }

    def test_other_columns_are_allowed(self):
        data = {"control_variables": [{"type": "categorical", "column": "batch"}]}
        assert validate_form(self.definition, data).is_valid

    def test_is_equal_to_value_checks_each_column(self):
        class _Form(MdDatasetBaseModel):
            control_variables: list = control_variables_field(rules=[is_equal_to_value("batch")])

        definition = translate_payload(_Form.model_json_schema())
        data = {"control_variables": [
            {"type": "categorical", "column": "batch"},
            {"type": "categorical", "column": "sex"},
        ]}
        assert _errors(validate_form(definition, data)) == {
            ("control_variables", "control variable 2 must use column 'batch', not 'sex'"),
        }

    def test_categorical_and_numerical_is_valid(self):
        data = {
            "condition_column": "condition",
            "control_variables": [
                {"type": "categorical", "column": "batch"},
                {"type": "numerical", "column": "age"},
            ],
            "experiment_design": {
                "sample_name": ["Heart_1", "Heart_2"],
                "condition": ["Heart", "Brain"],
                "batch": ["b1", "b2"],
                "age": [34, 51],
            },
        }
        assert validate_form(self.definition, data).is_valid

    def test_optional_when_absent_or_empty(self):
        table = {"sample_name": ["Heart_1"], "condition": ["Heart"]}
        for control_variables in (None, []):
            data = {
                "condition_column": "condition",
                "control_variables": control_variables,
                "experiment_design": table,
            }
            assert validate_form(self.definition, data).is_valid, control_variables

    def test_required_empty_is_invalid(self):
        for control_variables in (None, [], [{}]):
            result = validate_form(self.required_definition, {"control_variables": control_variables})
            assert not result.is_valid, control_variables
            assert ("control_variables", "is required") in _errors(result)

    def test_required_populated_is_valid(self):
        data = {"control_variables": [{"type": "categorical", "column": "batch"}]}
        assert validate_form(self.required_definition, data).is_valid

    def test_when_incorrect_option_given(self):
        data = {"control_variables": [{"type": "something_else", "column": "batch"}]}
        result = validate_form(self.required_definition, data)
        assert not result.is_valid
        assert _errors(result) == {(
            "control_variables",
            "control variable 1 ('batch') has type 'something_else'; must be one of 'categorical', 'numerical'",
        )}

    def test_each_incorrect_type_is_reported_by_number(self):
        data = {"control_variables": [
            {"type": "categorical", "column": "batch"},
            {"type": "Categorical", "column": "sex"},
            {"type": None, "column": "age"},
        ]}
        assert _errors(validate_form(self.required_definition, data)) == {
            ("control_variables",
             "control variable 2 ('sex') has type 'Categorical'; must be one of 'categorical', 'numerical'"),
            ("control_variables",
             "control variable 3 ('age') has type None; must be one of 'categorical', 'numerical'"),
        }

    def test_numerical_type_is_valid(self):
        data = {"control_variables": [{"type": "numerical", "column": "age"}]}
        assert validate_form(self.required_definition, data).is_valid

    def test_types_come_from_radio_options(self):
        class _Form(MdDatasetBaseModel):
            control_variables: list = control_variables_field(radioOptions=["categorical"])

        definition = translate_payload(_Form.model_json_schema())
        data = {"control_variables": [{"type": "numerical", "column": "age"}]}
        assert _errors(validate_form(definition, data)) == {
            ("control_variables", "control variable 1 ('age') has type 'numerical'; must be one of 'categorical'"),
        }

    def test_no_radio_options_means_any_type(self):
        definition = {"properties": {"control_variables": {"fieldType": "PairwiseControlVariables"}}}
        data = {"control_variables": [{"type": "something_else", "column": "batch"}]}
        assert validate_form(definition, data).is_valid

    def test_nested_object_is_invalid(self):
        data = {
            "control_variables": {
                "control_variables": [{"type": "categorical", "column": "batch"}],
            }
        }
        for definition in (self.definition, self.required_definition):
            result = validate_form(definition, data)
            assert not result.is_valid
            assert ("control_variables", self.SHAPE_ERROR) in _errors(result)

    def test_items_missing_type_or_column_are_invalid(self):
        for control_variables in (
            [{"column": "batch"}],
            [{"type": "categorical"}],
            ["batch"],
        ):
            result = validate_form(self.required_definition, {"control_variables": control_variables})
            assert not result.is_valid, control_variables
            assert ("control_variables", self.SHAPE_ERROR) in _errors(result)

    def test_experiment_design_missing_control_variable_column(self):
        data = {
            "condition_column": "condition",
            "control_variables": [{"type": "categorical", "column": "batch"}],
            "experiment_design": {
                "sample_name": ["Heart_1", "Heart_2"],
                "condition": ["Heart", "Brain"],
            },
        }
        result = validate_form(self.definition, data)
        assert not result.is_valid
        assert (
            "experiment_design",
            "table columns missing columns: 'batch'",
        ) in _errors(result)

    def test_condition_column_cannot_be_a_control_variable(self):
        data = {
            "condition_column": "condition",
            "control_variables": [{"type": "categorical", "column": "condition"}],
            "experiment_design": {
                "sample_name": ["Heart_1", "Heart_2"],
                "condition": ["Heart", "Brain"],
            },
        }
        result = validate_form(self.definition, data)
        assert not result.is_valid
        assert (
            "condition_column",
            "must not be one of the values in 'control_variables'",
        ) in _errors(result)

class TestConditionColumnField:

    class _Form(MdDatasetBaseModel):
        control_variables: list = control_variables_field()
        condition_column: str = condition_column_field(
            name="Condition Column",
            rules=[
                is_not_equal_to_value("sample_name"),
                is_not_included_in_values_from_field(field="control_variables", values="control_variables[].column"),
                is_required(),
            ],
            parameters={"width": "large"},
            group="Details",
        )
    def test_condition_column_field_is_valid(self):
        data = {"condition_column": "condition"}
        assert validate_form(self._Form.model_json_schema(), data).is_valid

    @pytest.mark.parametrize("value", [123, [], -1, True, "sample_name"])
    def test_condition_column_field_is_invalid(self, value):
        data = {"condition_column": value}
        assert not validate_form(self._Form.model_json_schema(), data).is_valid

    def test_condition_column_field_is_invalid_when_value_is_in_control_variables(self):
        data = {"condition_column": "condition", "control_variables": [{"type": "categorical", "column": "condition"}]}
        result = validate_form(self._Form.model_json_schema(), data)
        assert not result.is_valid
        assert (
            "condition_column",
            "must not be one of the values in 'control_variables'",
        ) in _errors(result)


class TestHasMultipleColumnValuesFromFieldInTable:
    """Each control variable's column must have at least 2 different values in the table."""

    class _Form(MdDatasetBaseModel):
        control_variables: list = control_variables_field()
        experiment_design: dict = experiment_design_field(
            rules=[
                has_multiple_column_values_from_field_in_table(
                    field="control_variables", values="control_variables[].column"
                ),
            ],
        )

    definition = translate_payload(_Form.model_json_schema())

    @staticmethod
    def _data(**columns):
        return {
            "control_variables": [{"type": "categorical", "column": column} for column in columns],
            "experiment_design": {"sample_name": ["s1", "s2", "s3", "s4"], **columns},
        }

    def test_columns_with_several_values_are_valid(self):
        data = self._data(batch=["b1", "b2", "b1", "b2"], sex=["F", "F", "M", "M"])
        assert validate_form(self.definition, data).is_valid

    def test_column_with_one_value_is_invalid(self):
        data = self._data(batch=["b1", "b1", "b1", "b1"])
        assert _errors(validate_form(self.definition, data)) == {
            ("experiment_design", "column 'batch' must have at least 2 different values, got only 'b1'"),
        }

    def test_each_single_valued_column_is_reported(self):
        data = self._data(batch=["b1", "b2", "b1", "b2"], sex=["F", "F", "F", "F"], site=["A", "A", "A", "A"])
        assert _errors(validate_form(self.definition, data)) == {
            ("experiment_design", "column 'sex' must have at least 2 different values, got only 'F'"),
            ("experiment_design", "column 'site' must have at least 2 different values, got only 'A'"),
        }

    def test_no_control_variables_is_valid(self):
        assert validate_form(self.definition, self._data()).is_valid

    def test_missing_column_is_left_to_column_names_check(self):
        data = self._data()
        data["control_variables"] = [{"type": "categorical", "column": "batch"}]
        assert _errors(validate_form(self.definition, data)) == {
            ("experiment_design", "table columns missing columns: 'batch'"),
        }


class TestDatasets:
    """Every dataset selected in a dataset field must be in the provided datasets."""

    class _Form(MdDatasetBaseModel):
        entity_type: EntityType = entity_type_field()
        input_datasets: list = intensity_input_dataset_field()


    @pytest.fixture()
    def definition(self):
        return translate_payload(self._Form.model_json_schema())

    datasets = [
        {"id": "ds1", "name": "Dataset 1", "type": "INTENSITY", "state": "COMPLETED"},
        {"id": "ds2", "name": "Dataset 2", "type": "INTENSITY", "state": "COMPLETED"},
    ]

    def test_selected_dataset_present_is_valid(self, definition):
        assert validate_form(definition, {"input_datasets": ["ds1"]}, datasets=self.datasets).is_valid

    def test_selected_dataset_dict_present_is_valid(self, definition):
        data = {"input_datasets": [{"id": "ds2", "name": "Dataset 2"}]}
        assert validate_form(definition, data, datasets=self.datasets).is_valid

    def test_selected_dataset_missing_is_invalid(self, definition):
        result = validate_form(definition, {"input_datasets": ["missing"]}, datasets=self.datasets)
        assert _errors(result) == {
            ("input_datasets", "dataset 'missing' is not in the provided datasets"),
        }

    def test_selected_dataset_dict_missing_is_invalid(self, definition):
        data = {"input_datasets": [{"id": "missing", "name": "Dataset 1"}]}
        assert _errors(validate_form(definition, data, datasets=self.datasets)) == {
            ("input_datasets", "dataset 'missing' is not in the provided datasets"),
        }

    def test_selected_dataset_missing_from_empty_datasets_is_invalid(self, definition):
        result = validate_form(definition, {"input_datasets": ["ds1"]}, datasets=[])
        assert _errors(result) == {
            ("input_datasets", "dataset 'ds1' is not in the provided datasets"),
        }

    def test_datasets_without_ids_are_ignored(self, definition):
        datasets = [{"name": "Dataset 1", "type": "INTENSITY", "state": "COMPLETED"}, "ds1"]
        result = validate_form(definition, {"input_datasets": ["ds1"]}, datasets=datasets)
        assert _errors(result) == {
            ("input_datasets", "dataset 'ds1' is not in the provided datasets"),
        }

    def test_datasets_list_must_be_provided(self, definition):
        result = validate_form(definition, {"input_datasets": ["ds1"]})
        assert _errors(result) == {
            ("input_datasets", "a datasets list must be provided to validate this field"),
        }

    class TestValidatesEntityTypeMatchesInputDatasets:
        """A dataset selected in the field an EntityType field searches must have that entity type."""

        @staticmethod
        def _dataset(ds_id="ds1", name="Dataset 1", **extra):
            return {"id": ds_id, "name": name, "type": "INTENSITY", "state": "COMPLETED", **extra}

        def test_valid(self, definition):
            datasets = [self._dataset(entity_types=["protein"])]
            result = validate_form(definition, {"input_datasets": ["ds1"], "entity_type": "protein"}, datasets=datasets)
            assert result.is_valid

        def test_missing_entity_type(self, definition):
            datasets = [self._dataset(entity_types=["gene"])]
            result = validate_form(definition, {"input_datasets": ["ds1"], "entity_type": "protein"}, datasets=datasets)
            assert _errors(result) == {
                ("input_datasets", "dataset 'Dataset 1' does not have entity type 'protein'"),
            }

        def test_one_of_several_entity_types_is_valid(self, definition):
            datasets = [self._dataset(entity_types=["protein", "peptide", "ptm"])]
            data = {"input_datasets": ["ds1"], "entity_type": "peptide"}
            assert validate_form(definition, data, datasets=datasets).is_valid

        def test_empty_entity_types_is_invalid(self, definition):
            datasets = [self._dataset(entity_types=[])]
            result = validate_form(definition, {"input_datasets": ["ds1"], "entity_type": "gene"}, datasets=datasets)
            assert _errors(result) == {
                ("input_datasets", "dataset 'Dataset 1' does not have entity type 'gene'"),
            }

        def test_entity_type_comparison_is_case_sensitive(self, definition):
            datasets = [self._dataset(entity_types=["Protein"])]
            result = validate_form(definition, {"input_datasets": ["ds1"], "entity_type": "protein"}, datasets=datasets)
            assert _errors(result) == {
                ("input_datasets", "dataset 'Dataset 1' does not have entity type 'protein'"),
            }

        def test_dict_selection_is_checked(self, definition):
            datasets = [self._dataset(entity_types=["gene"])]
            data = {"input_datasets": [{"id": "ds1", "name": "Dataset 1"}], "entity_type": "protein"}
            assert _errors(validate_form(definition, data, datasets=datasets)) == {
                ("input_datasets", "dataset 'Dataset 1' does not have entity type 'protein'"),
            }

        def test_error_names_dataset_by_id_when_it_has_no_name(self, definition):
            datasets = [{"id": "ds1", "type": "INTENSITY", "state": "COMPLETED", "entity_types": ["gene"]}]
            result = validate_form(definition, {"input_datasets": ["ds1"], "entity_type": "protein"}, datasets=datasets)
            assert _errors(result) == {
                ("input_datasets", "dataset 'ds1' does not have entity type 'protein'"),
            }

        def test_dataset_without_entity_types_is_not_checked(self, definition):
            datasets = [self._dataset()]
            data = {"input_datasets": ["ds1"], "entity_type": "protein"}
            assert validate_form(definition, data, datasets=datasets).is_valid

        def test_no_entity_type_selected_is_not_checked(self, definition):
            datasets = [self._dataset(entity_types=["gene"])]
            assert validate_form(definition, {"input_datasets": ["ds1"]}, datasets=datasets).is_valid

        def test_null_entity_type_is_not_checked(self, definition):
            datasets = [self._dataset(entity_types=["gene"])]
            data = {"input_datasets": ["ds1"], "entity_type": None}
            assert validate_form(definition, data, datasets=datasets).is_valid

        def test_missing_dataset_reports_only_missing(self, definition):
            result = validate_form(
                definition, {"input_datasets": ["missing"], "entity_type": "protein"}, datasets=[],
            )
            assert _errors(result) == {
                ("input_datasets", "dataset 'missing' is not in the provided datasets"),
            }

        def test_reported_alongside_type_and_state_errors(self, definition):
            datasets = [self._dataset(type="PAIRWISE", state="RUNNING", entity_types=["gene"])]
            result = validate_form(definition, {"input_datasets": ["ds1"], "entity_type": "protein"}, datasets=datasets)
            assert _errors(result) == {
                ("input_datasets", "dataset 'ds1' must be of type 'INTENSITY', not 'PAIRWISE'"),
                ("input_datasets", "dataset 'ds1' must be in state 'COMPLETED', not 'RUNNING'"),
                ("input_datasets", "dataset 'Dataset 1' does not have entity type 'protein'"),
            }

        def test_each_selected_dataset_is_checked(self):
            class _Form(MdDatasetBaseModel):
                entity_type: EntityType = entity_type_field()
                input_datasets: list = intensity_input_datasets_field()

            definition = translate_payload(_Form.model_json_schema())
            datasets = [
                self._dataset("ds1", "Dataset 1", entity_types=["protein", "gene"]),
                self._dataset("ds2", "Dataset 2", entity_types=["gene"]),
                self._dataset("ds3", "Dataset 3", entity_types=["peptide"]),
            ]
            data = {"input_datasets": ["ds1", "ds2", "ds3"], "entity_type": "protein"}
            assert _errors(validate_form(definition, data, datasets=datasets)) == {
                ("input_datasets", "dataset 'Dataset 2' does not have entity type 'protein'"),
                ("input_datasets", "dataset 'Dataset 3' does not have entity type 'protein'"),
            }

        def test_only_the_referenced_dataset_field_is_checked(self):
            class _Form(MdDatasetBaseModel):
                entity_type: EntityType = entity_type_field()
                input_datasets: list = intensity_input_dataset_field()
                other_datasets: list = intensity_input_dataset_field()

            definition = translate_payload(_Form.model_json_schema())
            datasets = [
                self._dataset("ds1", "Dataset 1", entity_types=["protein"]),
                self._dataset("ds2", "Dataset 2", entity_types=["gene"]),
            ]
            data = {"input_datasets": ["ds1"], "other_datasets": ["ds2"], "entity_type": "protein"}
            assert validate_form(definition, data, datasets=datasets).is_valid

        def test_inactive_entity_type_field_is_not_checked(self):
            definition = {
                "properties": {
                    "input_datasets": {"fieldType": "Datasets", "parameters": {"type": "INTENSITY"}},
                    "use_entity_type": {"fieldType": "Boolean"},
                    "entity_type": {
                        "fieldType": "EntityType",
                        "parameters": {"datasetsSearch": {"ref": "input_datasets"}},
                        "when": {"property": "use_entity_type", "equals": True},
                    },
                }
            }
            datasets = [self._dataset(entity_types=["gene"])]
            data = {"input_datasets": ["ds1"], "entity_type": "protein"}
            assert validate_form(definition, {**data, "use_entity_type": False}, datasets=datasets).is_valid
            assert _errors(validate_form(definition, {**data, "use_entity_type": True}, datasets=datasets)) == {
                ("input_datasets", "dataset 'Dataset 1' does not have entity type 'protein'"),
            }


class TestValidatesEntityTypeField():

    class _Form(MdDatasetBaseModel):
        entity_type: EntityType = entity_type_field()

    @pytest.fixture()
    def definition(self):
        return translate_payload(self._Form.model_json_schema())

    _allowed = "['protein', 'peptide', 'gene', 'metabolite', 'ptm', 'precursor']"

    @pytest.mark.parametrize("value", ["protein", "peptide", "gene", "metabolite", "ptm"])
    def test_it_accepts_each_entity_type(self, definition, value):
        assert validate_form(definition, {"entity_type": value}).is_valid

    @pytest.mark.parametrize("value", ["Protein", "proteins", "mouse"])
    def test_it_must_be_a_valid_entity_type(self, definition, value):
        result = validate_form(definition, {"entity_type": value})
        assert _errors(result) == {
            ("entity_type", f"{value!r} is not one of the allowed options {self._allowed}"),
        }

    def test_it_must_not_be_a_list(self, definition):
        result = validate_form(definition, {"entity_type": ["protein"]})
        assert _errors(result) == {("entity_type", "must be a single option, not a list")}

    def test_it_must_not_be_a_number(self, definition):
        result = validate_form(definition, {"entity_type": 1})
        assert _errors(result) == {
            ("entity_type", f"1 is not one of the allowed options {self._allowed}"),
        }

    @pytest.mark.parametrize("data", [{}, {"entity_type": None}, {"entity_type": ""}])
    def test_it_is_optional(self, definition, data):
        assert validate_form(definition, data).is_valid


class Test_is_not_included_in_values_from_field():

    class _Form(MdDatasetBaseModel):
        design_variables: Optional[list] = control_variables_field(
            name="Design Variables",
            radioOptions = ["categorical"],
        )

        batch_variables: Optional[list] = control_variables_field(
            name="Batch Variables",
            rules= [
                is_not_included_in_values_from_field(field="design_variables", values="design_variables[].column"),
            ],
            radioOptions = ["categorical"],
        )

    @pytest.fixture()
    def definition(self):
        return translate_payload(self._Form.model_json_schema())

    def test_is_not_included_in_values_from_field_invalid(self, definition):
        values = {
            "batch_variables": [
            {
                "type": "categorical",
                "column": "batch"
            }
        ],
            "design_variables": [
                {
                    "type": "categorical",
                    "column": "batch"
                }
            ]}

        result = validate_form(definition, values)
        assert _errors(result) == {
            ("batch_variables", "control variable 1 must not use column 'batch', already used in 'design_variables'"),
        }

    def test_is_not_included_in_values_from_field_valid(self, definition):
        values = {
            "batch_variables": [
                {
                    "type": "categorical",
                    "column": "batch"
                }
            ],
            "design_variables": [
                {
                    "type": "categorical",
                    "column": "a_desgin"
                }
            ]}

        result = validate_form(definition, values)
        assert result.is_valid


class TestPlotSize:
    """A PlotSize value is {"fixed": false} or {"fixed": true} with a width and height in pixels."""

    class _Form(MdDatasetBaseModel):
        plot_size: dict = plot_size_field(name="Plot Size", group="Layout", rules=[is_required()])

    @pytest.fixture()
    def definition(self):
        return translate_payload(self._Form.model_json_schema())

    @pytest.mark.parametrize("value", [
        {"fixed": False},
        {"fixed": True, "width": 400, "height": 300},
        {"fixed": True, "width": 1, "height": 1000},
        # Sizes left over from a previous fixed choice are ignored.
        {"fixed": False, "width": "abc", "height": 0},
    ])
    def test_valid(self, definition, value):
        assert validate_form(definition, {"plot_size": value}).is_valid

    @pytest.mark.parametrize("data", [{}, {"plot_size": None}, {"plot_size": {}}])
    def test_it_is_required(self, definition, data):
        assert _errors(validate_form(definition, data)) == {("plot_size", "is required")}

    @pytest.mark.parametrize("value", ["large", [{"fixed": False}], True, 300])
    def test_it_must_be_an_object(self, definition, value):
        assert _errors(validate_form(definition, {"plot_size": value})) == {
            ("plot_size", "must be an object with a boolean 'fixed'"),
        }

    @pytest.mark.parametrize("value, got", [
        ({"width": 400, "height": 300}, "None"),
        ({"fixed": "true"}, "'true'"),
        ({"fixed": 1}, "1"),
    ])
    def test_fixed_must_be_a_boolean(self, definition, value, got):
        assert _errors(validate_form(definition, {"plot_size": value})) == {
            ("plot_size", f"'fixed' must be a boolean, got {got}"),
        }

    def test_fixed_requires_width_and_height(self, definition):
        assert _errors(validate_form(definition, {"plot_size": {"fixed": True}})) == {
            ("plot_size", "'width' is required when 'fixed' is true"),
            ("plot_size", "'height' is required when 'fixed' is true"),
        }

    def test_fixed_requires_height(self, definition):
        result = validate_form(definition, {"plot_size": {"fixed": True, "width": 400}})
        assert _errors(result) == {("plot_size", "'height' is required when 'fixed' is true")}

    @pytest.mark.parametrize("width", ["400", 400.0, None, True])
    def test_width_must_be_an_int(self, definition, width):
        result = validate_form(definition, {"plot_size": {"fixed": True, "width": width, "height": 300}})
        assert _errors(result) == {("plot_size", f"'width' must be an int, got {width!r}")}

    @pytest.mark.parametrize("height", [0, -1, 1001])
    def test_height_must_be_in_range(self, definition, height):
        result = validate_form(definition, {"plot_size": {"fixed": True, "width": 400, "height": height}})
        assert _errors(result) == {("plot_size", f"'height' must be between 1 and 1000, got {height}")}

    def test_each_bad_size_is_reported(self, definition):
        result = validate_form(definition, {"plot_size": {"fixed": True, "width": 0, "height": "big"}})
        assert _errors(result) == {
            ("plot_size", "'width' must be between 1 and 1000, got 0"),
            ("plot_size", "'height' must be an int, got 'big'"),
        }


class TestRadioSelectionField:
    """A single-choice field built with ``radio_selection_field``."""

    class _Form(MdDatasetBaseModel):
        source: str = radio_selection_field(
            options=["all", "selection", "list"], default="all", rules=[is_required()],
        )
        entity_type: Optional[str] = radio_selection_field(options=["protein", "peptide"], inline=True)
        database: Optional[str] = radio_selection_field(
            options={"ref": "entity_type", "cases": {"protein": ["reactome"], "peptide": ["phosphosite"]}},
        )

    @pytest.fixture()
    def definition(self):
        return translate_payload(self._Form.model_json_schema())

    @pytest.mark.parametrize("value", ["all", "selection", "list"])
    def test_valid_option(self, definition, value):
        assert validate_form(definition, {"source": value}).is_valid

    @pytest.mark.parametrize("value", ["mouse", "All", 1, True])
    def test_invalid_option(self, definition, value):
        assert _errors(validate_form(definition, {"source": value})) == {
            ("source", f"{value!r} is not one of the allowed options ['all', 'selection', 'list']"),
        }

    def test_must_not_be_a_list(self, definition):
        assert _errors(validate_form(definition, {"source": ["all"]})) == {
            ("source", "must be a single option, not a list"),
        }

    @pytest.mark.parametrize("data", [{}, {"source": None}, {"source": ""}])
    def test_required_field_missing(self, definition, data):
        assert _errors(validate_form(definition, data)) == {("source", "is required")}

    def test_optional_field_may_be_left_out(self, definition):
        assert validate_form(definition, {"source": "all", "entity_type": None}).is_valid

    def test_dynamic_options_follow_the_referenced_field(self, definition):
        data = {"source": "all", "entity_type": "protein"}
        assert validate_form(definition, {**data, "database": "reactome"}).is_valid
        assert _errors(validate_form(definition, {**data, "database": "phosphosite"})) == {
            ("database", "'phosphosite' is not one of the allowed options ['reactome']"),
        }
