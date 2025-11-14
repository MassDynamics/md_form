import pytest
from field_utils.field_types import FieldType


class TestFieldType:
    """Test cases for the FieldType enum"""

    def test_field_type_values(self):
        """Test that all field types have the expected string values"""
        assert FieldType.STRING == "String"
        assert FieldType.BOOLEAN == "Boolean"
        assert FieldType.NUMBER == "Number"
        assert FieldType.NUMBER_RANGE == "NumberRange"
        assert FieldType.EXPERIMENT_DESIGN == "SampleMetadataTable"
        assert FieldType.CONDITION_COLUMN == "DatasetSampleMetadata"
        assert FieldType.CONDITION_COLUMN_MULTI_SELECT == "SelectBySampleMetadata"
        assert FieldType.CONDITION_COMPARISONS == "PairwiseConditionComparisons"
        assert FieldType.CONTROL_VARIABLES == "PairwiseControlVariables"
        assert FieldType.INTENSITY_INPUT_DATASET == "Datasets"
        assert FieldType.ENTITY_TYPE == "EntityType"

    def test_field_type_inheritance(self):
        """Test that FieldType inherits from str and Enum"""
        # Check that it's a string enum
        assert isinstance(FieldType.STRING, str)
        assert isinstance(FieldType.STRING, FieldType)
        
        # Check that values are strings
        for field_type in FieldType:
            assert isinstance(field_type.value, str)

    def test_field_type_comparison(self):
        """Test that field types can be compared as strings"""
        assert FieldType.STRING == "String"
        assert FieldType.BOOLEAN == "Boolean"
        assert FieldType.STRING != FieldType.BOOLEAN

    def test_field_type_iteration(self):
        """Test that all field types can be iterated over"""
        field_types = list(FieldType)
        assert len(field_types) == 11
        
        expected_values = [
            "String", "Boolean", "Number", "NumberRange", "SampleMetadataTable",
            "DatasetSampleMetadata", "SelectBySampleMetadata", "PairwiseConditionComparisons",
            "PairwiseControlVariables", "Datasets", "EntityType"
        ]
        
        for field_type in field_types:
            assert field_type.value in expected_values

    def test_field_type_membership(self):
        """Test membership testing for field types"""
        # Test with actual enum members
        assert FieldType.STRING in FieldType
        assert FieldType.BOOLEAN in FieldType
        
        # Test with values
        assert "String" in [ft.value for ft in FieldType]
        assert "Boolean" in [ft.value for ft in FieldType]
        assert "InvalidType" not in [ft.value for ft in FieldType]

    def test_field_type_string_operations(self):
        """Test that field types support string operations"""
        string_type = FieldType.STRING
        assert string_type.upper() == "STRING"
        assert string_type.lower() == "string"
        assert string_type.startswith("Str")
        assert len(string_type) == 6

    def test_field_type_equality(self):
        """Test equality between field types"""
        assert FieldType.STRING == FieldType.STRING
        assert FieldType.STRING != FieldType.BOOLEAN
        assert FieldType.STRING == "String"
        assert FieldType.STRING != "Boolean"

    def test_field_type_hashable(self):
        """Test that field types are hashable and can be used as dict keys"""
        field_dict = {
            FieldType.STRING: "string_value",
            FieldType.BOOLEAN: "boolean_value",
            FieldType.NUMBER: "number_value"
        }
        
        assert field_dict[FieldType.STRING] == "string_value"
        assert field_dict[FieldType.BOOLEAN] == "boolean_value"
        assert field_dict[FieldType.NUMBER] == "number_value"

    def test_field_type_repr(self):
        """Test string representation of field types"""
        assert repr(FieldType.STRING) == "<FieldType.STRING: 'String'>"
        # str() returns the enum name, not the value
        assert str(FieldType.STRING) == "FieldType.STRING"

    def test_field_type_unique_values(self):
        """Test that all field type values are unique"""
        values = [field_type.value for field_type in FieldType]
        assert len(values) == len(set(values)), "All field type values should be unique" 