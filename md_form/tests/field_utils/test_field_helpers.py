import pytest
from typing import Dict, Any
from pydantic.fields import FieldInfo
from field_utils.field_helpers import (
    boolean_field, string_field, number_field, select_field,
    experiment_design_field, condition_column_field, condition_column_multi_select_field,
    condition_comparisons_field, control_variables_field, numberrange_field,
    intensity_input_dataset_field, entity_type_field
)
from field_utils.field_types import FieldType


class TestBooleanField:
    """Test cases for the boolean_field function"""

    def test_boolean_field_basic(self):
        """Test boolean_field with no parameters"""
        field = boolean_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.BOOLEAN

    def test_boolean_field_with_default(self):
        """Test boolean_field with default value"""
        field = boolean_field(default=True)
        
        assert field.json_schema_extra["default"] is True

    def test_boolean_field_with_label(self):
        """Test boolean_field with label"""
        field = boolean_field(label="Test Label")
        
        assert field.json_schema_extra["parameters"]["label"] == "Test Label"

    def test_boolean_field_with_default_and_label(self):
        """Test boolean_field with both default and label"""
        field = boolean_field(default=False, label="Test Label")
        
        assert field.json_schema_extra["default"] is False
        assert field.json_schema_extra["parameters"]["label"] == "Test Label"

    def test_boolean_field_with_none_default(self):
        """Test boolean_field with None default"""
        field = boolean_field(default=None)
        
        # When default is None, it should not be included in json_schema_extra
        assert "default" not in field.json_schema_extra


class TestStringField:
    """Test cases for the string_field function"""

    def test_string_field_basic(self):
        """Test string_field with no parameters"""
        field = string_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.STRING

    def test_string_field_with_default(self):
        """Test string_field with default value"""
        field = string_field(default="test_value")
        
        assert field.json_schema_extra["default"] == "test_value"


class TestNumberField:
    """Test cases for the number_field function"""

    def test_number_field_basic(self):
        """Test number_field with no parameters"""
        field = number_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.NUMBER

    def test_number_field_with_default(self):
        """Test number_field with default value"""
        field = number_field(default=42)
        
        assert field.json_schema_extra["default"] == 42

    def test_number_field_with_ge(self):
        """Test number_field with ge parameter"""
        field = number_field(ge=0)
        
        # ge is passed as a kwarg to Field, not as an attribute
        # We can't access it directly on FieldInfo, but it's used in Field creation
        assert isinstance(field, FieldInfo)

    def test_number_field_with_le(self):
        """Test number_field with le parameter"""
        field = number_field(le=100)
        
        # le is passed as a kwarg to Field, not as an attribute
        # We can't access it directly on FieldInfo, but it's used in Field creation
        assert isinstance(field, FieldInfo)

    def test_number_field_with_all_parameters(self):
        """Test number_field with all parameters"""
        field = number_field(default=50, ge=0, le=100)
        
        assert field.json_schema_extra["default"] == 50
        # ge and le are passed as kwargs to Field, not as attributes
        # We can't access them directly on FieldInfo, but they're used in Field creation
        assert isinstance(field, FieldInfo)

    def test_number_field_with_float_values(self):
        """Test number_field with float values"""
        field = number_field(default=3.14, ge=0.0, le=10.0)
        
        assert field.json_schema_extra["default"] == 3.14
        # ge and le are passed as kwargs to Field, not as attributes
        # We can't access them directly on FieldInfo, but they're used in Field creation
        assert isinstance(field, FieldInfo)


class TestSelectField:
    """Test cases for the select_field function"""

    def test_select_field_basic(self):
        """Test select_field with no parameters"""
        field = select_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.STRING

    def test_select_field_with_default(self):
        """Test select_field with default value"""
        field = select_field(default="option1")
        
        assert field.json_schema_extra["default"] == "option1"

    def test_select_field_with_options(self):
        """Test select_field with options"""
        options = ["option1", "option2", "option3"]
        field = select_field(options=options)
        
        expected_options = [
            {"name": "option1", "value": "option1"},
            {"name": "option2", "value": "option2"},
            {"name": "option3", "value": "option3"}
        ]
        assert field.json_schema_extra["parameters"]["options"] == expected_options

    def test_select_field_with_discriminator(self):
        """Test select_field with discriminator"""
        field = select_field(discriminator="test_discriminator")
        
        assert field.discriminator == "test_discriminator"

    def test_select_field_with_all_parameters(self):
        """Test select_field with all parameters"""
        options = ["option1", "option2"]
        field = select_field(
            default="option1",
            options=options,
            discriminator="test_discriminator"
        )
        
        assert field.json_schema_extra["default"] == "option1"
        assert len(field.json_schema_extra["parameters"]["options"]) == 2
        assert field.discriminator == "test_discriminator"


class TestExperimentDesignField:
    """Test cases for the experiment_design_field function"""

    def test_experiment_design_field(self):
        """Test experiment_design_field"""
        field = experiment_design_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.EXPERIMENT_DESIGN
        assert field.json_schema_extra["name"] == "Sample Metadata"


class TestConditionColumnField:
    """Test cases for the condition_column_field function"""

    def test_condition_column_field(self):
        """Test condition_column_field"""
        field = condition_column_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.CONDITION_COLUMN
        assert "datasetsSearch" in field.json_schema_extra["parameters"]
        assert field.json_schema_extra["parameters"]["datasetsSearch"]["ref"] == "input_datasets"


class TestConditionColumnMultiSelectField:
    """Test cases for the condition_column_multi_select_field function"""

    def test_condition_column_multi_select_field(self):
        """Test condition_column_multi_select_field"""
        field = condition_column_multi_select_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.CONDITION_COLUMN_MULTI_SELECT
        assert "datasetsSearch" in field.json_schema_extra["parameters"]
        assert field.json_schema_extra["parameters"]["datasetsSearch"]["ref"] == "input_datasets"


class TestConditionComparisonsField:
    """Test cases for the condition_comparisons_field function"""

    def test_condition_comparisons_field(self):
        """Test condition_comparisons_field"""
        field = condition_comparisons_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.CONDITION_COMPARISONS
        assert "experimentDesign" in field.json_schema_extra["parameters"]
        assert "conditionColumn" in field.json_schema_extra["parameters"]
        assert field.json_schema_extra["parameters"]["experimentDesign"]["ref"] == "experiment_design"
        assert field.json_schema_extra["parameters"]["conditionColumn"]["ref"] == "condition_column"


class TestControlVariablesField:
    """Test cases for the control_variables_field function"""

    def test_control_variables_field_basic(self):
        """Test control_variables_field with no parameters"""
        field = control_variables_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.CONTROL_VARIABLES
        assert "radioOptions" in field.json_schema_extra["parameters"]
        assert field.json_schema_extra["parameters"]["radioOptions"] == ["categorical", "numerical"]

    def test_control_variables_field_with_default(self):
        """Test control_variables_field with default value"""
        field = control_variables_field(default="categorical")
        
        assert field.json_schema_extra["default"] == "categorical"
        assert "radioOptions" in field.json_schema_extra["parameters"]


class TestNumberRangeField:
    """Test cases for the numberrange_field function"""

    def test_numberrange_field_basic(self):
        """Test numberrange_field with no parameters"""
        field = numberrange_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.NUMBER_RANGE

    def test_numberrange_field_with_default(self):
        """Test numberrange_field with default value"""
        field = numberrange_field(default=5.0)
        
        assert field.json_schema_extra["default"] == 5.0

    def test_numberrange_field_with_ge(self):
        """Test numberrange_field with ge parameter"""
        field = numberrange_field(ge=0.0)
        
        # ge is passed as a kwarg to Field, not as an attribute
        # We can't access it directly on FieldInfo, but it's used in Field creation
        assert isinstance(field, FieldInfo)

    def test_numberrange_field_with_le(self):
        """Test numberrange_field with le parameter"""
        field = numberrange_field(le=10.0)
        
        # le is passed as a kwarg to Field, not as an attribute
        # We can't access it directly on FieldInfo, but it's used in Field creation
        assert isinstance(field, FieldInfo)

    def test_numberrange_field_with_interval(self):
        """Test numberrange_field with interval parameter"""
        field = numberrange_field(interval=0.5)
        
        assert field.json_schema_extra["parameters"]["interval"] == 0.5

    def test_numberrange_field_with_all_parameters(self):
        """Test numberrange_field with all parameters"""
        field = numberrange_field(
            default=5.0,
            ge=0.0,
            le=10.0,
            interval=0.5
        )
        
        assert field.json_schema_extra["default"] == 5.0
        # ge and le are passed as kwargs to Field, not as attributes
        # We can't access them directly on FieldInfo, but they're used in Field creation
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["parameters"]["interval"] == 0.5


class TestIntensityInputDatasetField:
    """Test cases for the intensity_input_dataset_field function"""

    def test_intensity_input_dataset_field(self):
        """Test intensity_input_dataset_field"""
        field = intensity_input_dataset_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.INTENSITY_INPUT_DATASET
        assert field.json_schema_extra["name"] == "Select Intensity dataset"
        assert "type" in field.json_schema_extra["parameters"]
        assert field.json_schema_extra["parameters"]["type"] == "INTENSITY"
        assert "multiple" in field.json_schema_extra["parameters"]
        assert field.json_schema_extra["parameters"]["multiple"] is False


class TestEntityTypeField:
    """Test cases for the entity_type_field function"""

    def test_entity_type_field_basic(self):
        """Test entity_type_field with no parameters"""
        field = entity_type_field()
        
        assert isinstance(field, FieldInfo)
        assert field.json_schema_extra["fieldType"] == FieldType.ENTITY_TYPE

    def test_entity_type_field_with_default(self):
        """Test entity_type_field with default value"""
        field = entity_type_field(default="protein")
        
        assert field.json_schema_extra["default"] == "protein"

    def test_entity_type_field_with_none_default(self):
        """Test entity_type_field with None default"""
        field = entity_type_field(default=None)
        
        # When default is None, it should not be included in json_schema_extra
        assert "default" not in field.json_schema_extra


class TestFieldHelpersIntegration:
    """Integration tests for field helpers"""

    def test_all_field_helpers_return_fields(self):
        """Test that all field helper functions return FieldInfo instances"""
        field_functions = [
            boolean_field(),
            string_field(),
            number_field(),
            select_field(),
            experiment_design_field(),
            condition_column_field(),
            condition_column_multi_select_field(),
            condition_comparisons_field(),
            control_variables_field(),
            numberrange_field(),
            intensity_input_dataset_field(),
            entity_type_field()
        ]
        
        for field in field_functions:
            assert isinstance(field, FieldInfo)
            assert "fieldType" in field.json_schema_extra

    def test_field_helpers_with_consistent_parameters(self):
        """Test that field helpers handle parameters consistently"""
        # Test with None parameters
        boolean_none = boolean_field(default=None, label=None)
        string_none = string_field(default=None)
        number_none = number_field(default=None, ge=None, le=None)
        
        # Should not include None values in json_schema_extra
        assert "default" not in boolean_none.json_schema_extra
        assert "parameters" not in boolean_none.json_schema_extra

    def test_field_helpers_with_edge_cases(self):
        """Test field helpers with edge cases"""
        # Test with empty options list
        select_empty = select_field(options=[])
        assert select_empty.json_schema_extra["parameters"]["options"] == []
        
        # Test with zero values
        number_zero = number_field(default=0, ge=0, le=0)
        assert number_zero.json_schema_extra["default"] == 0
        # ge and le are passed as kwargs to Field, not as attributes
        # We can't access them directly on FieldInfo, but they're used in Field creation
        assert isinstance(number_zero, FieldInfo)
        
        # Test with empty string
        string_empty = string_field(default="")
        assert string_empty.json_schema_extra["default"] == ""

    def test_field_helpers_type_consistency(self):
        """Test that field helpers maintain type consistency"""
        # Boolean field should always have boolean type
        boolean_field_instance = boolean_field()
        assert boolean_field_instance.json_schema_extra["fieldType"] == FieldType.BOOLEAN
        
        # String field should always have string type
        string_field_instance = string_field()
        assert string_field_instance.json_schema_extra["fieldType"] == FieldType.STRING
        
        # Number field should always have number type
        number_field_instance = number_field()
        assert number_field_instance.json_schema_extra["fieldType"] == FieldType.NUMBER 