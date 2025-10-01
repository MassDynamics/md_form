import pytest
import inspect
from field_utils.rules_builder import (
    is_equal_to_value, is_not_equal_to_value,
    is_equal_to_value_from_field, is_not_included_in_values_from_field,
    is_required, has_unique_column_values_in_table, has_unique_in_column,
    is_all_unique_in_column_from_field, has_multiple_column_values_from_field_in_table
)
from field_utils.rules import (
    EqualsToValueRule, EqualsToFieldRule, RequiredRule,
    ColumnValidationRule, ColumnFromFieldValidationRule
)


class TestRulesBuilder:
    """Test cases for the rules builder functions"""

    def test_is_equal_to_value(self):
        """Test is_equal_to_value function"""
        rule = is_equal_to_value("test_value")
        
        assert isinstance(rule, EqualsToValueRule)
        assert rule.rule_name == "is_equal_to_value"
        assert rule.value == "test_value"
        
        result = rule.as_dict()
        expected = {
            "name": "is_equal_to_value",
            "parameters": {
                "value": "test_value"
            }
        }
        assert result == expected

    def test_is_not_equal_to_value(self):
        """Test is_not_equal_to_value function"""
        rule = is_not_equal_to_value("test_value")
        
        assert isinstance(rule, EqualsToValueRule)
        assert rule.rule_name == "is_not_equal_to_value"
        assert rule.value == "test_value"
        
        result = rule.as_dict()
        expected = {
            "name": "is_not_equal_to_value",
            "parameters": {
                "value": "test_value"
            }
        }
        assert result == expected

    def test_is_equal_to_value_from_field(self):
        """Test is_equal_to_value_from_field function"""
        rule = is_equal_to_value_from_field("test_field")
        
        assert isinstance(rule, EqualsToFieldRule)
        assert rule.rule_name == "is_equal_to_value_from_field"
        assert rule.field == "test_field"
        
        result = rule.as_dict()
        expected = {
            "name": "is_equal_to_value_from_field",
            "parameters": {
                "field": "test_field"
            }
        }
        assert result == expected

    def test_is_not_equal_to_value_from_field(self):
        """Test is_not_included_in_values_from_field function"""
        rule = is_not_included_in_values_from_field("test_field")
        
        assert isinstance(rule, EqualsToFieldRule)
        assert rule.rule_name == "is_not_included_in_values_from_field"
        assert rule.field == "test_field"
        
        result = rule.as_dict()
        expected = {
            "name": "is_not_included_in_values_from_field",
            "parameters": {
                "field": "test_field"
            }
        }
        assert result == expected

    def test_is_required(self):
        """Test is_required function"""
        rule = is_required()
        
        assert isinstance(rule, RequiredRule)
        assert rule.rule_name == "is_required"
        
        result = rule.as_dict()
        expected = {
            "name": "is_required"
        }
        assert result == expected

    def test_has_unique_column_values_in_table(self):
        """Test has_unique_column_values_in_table function"""
        rule = has_unique_column_values_in_table("test_column")
        
        assert isinstance(rule, ColumnValidationRule)
        assert rule.rule_name == "has_unique_column_values_in_table"
        assert rule.column == "test_column"
        
        result = rule.as_dict()
        expected = {
            "name": "has_unique_column_values_in_table",
            "parameters": {
                "column": "test_column"
            }
        }
        assert result == expected

    def test_has_unique_in_column(self):
        """Test has_unique_in_column function"""
        rule = has_unique_in_column("test_column")
        
        assert isinstance(rule, ColumnValidationRule)
        assert rule.rule_name == "has_unique_in_column"
        assert rule.column == "test_column"
        
        result = rule.as_dict()
        expected = {
            "name": "has_unique_in_column",
            "parameters": {
                "column": "test_column"
            }
        }
        assert result == expected

    def test_is_all_unique_in_column_from_field(self):
        """Test is_all_unique_in_column_from_field function"""
        rule = is_all_unique_in_column_from_field("test_field")
        
        assert isinstance(rule, ColumnFromFieldValidationRule)
        assert rule.rule_name == "is_all_unique_in_column_from_field"
        assert rule.field == "test_field"
        
        result = rule.as_dict()
        expected = {
            "name": "is_all_unique_in_column_from_field",
            "parameters": {
                "field": "test_field"
            }
        }
        assert result == expected

    def test_has_multiple_column_values_from_field_in_table(self):
        """Test has_multiple_column_values_from_field_in_table function"""
        rule = has_multiple_column_values_from_field_in_table("test_field")
        
        assert isinstance(rule, ColumnFromFieldValidationRule)
        assert rule.rule_name == "has_multiple_column_values_from_field_in_table"
        assert rule.field == "test_field"
        
        result = rule.as_dict()
        expected = {
            "name": "has_multiple_column_values_from_field_in_table",
            "parameters": {
                "field": "test_field"
            }
        }
        assert result == expected


class TestRulesBuilderWithDifferentValues:
    """Test rules builder functions with different value types"""

    def test_is_equal_to_value_with_different_types(self):
        """Test is_equal_to_value with different value types"""
        # String value
        rule_str = is_equal_to_value("string_value")
        assert rule_str.value == "string_value"
        
        # Integer value
        rule_int = is_equal_to_value(42)
        assert rule_int.value == 42
        
        # Boolean value
        rule_bool = is_equal_to_value(True)
        assert rule_bool.value is True
        
        # List value
        rule_list = is_equal_to_value([1, 2, 3])
        assert rule_list.value == [1, 2, 3]
        
        # None value
        rule_none = is_equal_to_value(None)
        assert rule_none.value is None

    def test_is_not_equal_to_value_with_different_types(self):
        """Test is_not_equal_to_value with different value types"""
        # String value
        rule_str = is_not_equal_to_value("string_value")
        assert rule_str.value == "string_value"
        
        # Integer value
        rule_int = is_not_equal_to_value(42)
        assert rule_int.value == 42
        
        # Boolean value
        rule_bool = is_not_equal_to_value(False)
        assert rule_bool.value is False

    def test_column_functions_with_different_column_names(self):
        """Test column functions with different column names"""
        # Simple column name
        rule1 = has_unique_column_values_in_table("simple_column")
        assert rule1.column == "simple_column"
        
        # Column name with spaces
        rule2 = has_unique_in_column("column with spaces")
        assert rule2.column == "column with spaces"
        
        # Column name with special characters
        rule3 = has_unique_column_values_in_table("column_123")
        assert rule3.column == "column_123"

    def test_field_functions_with_different_field_names(self):
        """Test field functions with different field names"""
        # Simple field name
        rule1 = is_equal_to_value_from_field("simple_field")
        assert rule1.field == "simple_field"
        
        # Field name with underscores
        rule2 = is_not_included_in_values_from_field("field_with_underscores")
        assert rule2.field == "field_with_underscores"
        
        # Field name with dashes
        rule3 = is_all_unique_in_column_from_field("field-with-dashes")
        assert rule3.field == "field-with-dashes"


class TestRulesBuilderFunctionNames:
    """Test that function names are correctly captured"""

    def test_function_names_match_expected(self):
        """Test that function names are correctly captured from inspect"""
        # Test that the function names are correctly captured
        rule1 = is_equal_to_value("test")
        assert rule1.rule_name == "is_equal_to_value"
        
        rule2 = is_not_equal_to_value("test")
        assert rule2.rule_name == "is_not_equal_to_value"
        
        rule3 = is_equal_to_value_from_field("test")
        assert rule3.rule_name == "is_equal_to_value_from_field"
        
        rule4 = is_not_included_in_values_from_field("test")
        assert rule4.rule_name == "is_not_included_in_values_from_field"
        
        rule5 = is_required()
        assert rule5.rule_name == "is_required"
        
        rule6 = has_unique_column_values_in_table("test")
        assert rule6.rule_name == "has_unique_column_values_in_table"
        
        rule7 = has_unique_in_column("test")
        assert rule7.rule_name == "has_unique_in_column"
        
        rule8 = is_all_unique_in_column_from_field("test")
        assert rule8.rule_name == "is_all_unique_in_column_from_field"
        
        rule9 = has_multiple_column_values_from_field_in_table("test")
        assert rule9.rule_name == "has_multiple_column_values_from_field_in_table"


class TestRulesBuilderIntegration:
    """Integration tests for rules builder functions"""

    def test_all_functions_return_correct_rule_types(self):
        """Test that all functions return the correct rule types"""
        # Value-based rules
        assert isinstance(is_equal_to_value("test"), EqualsToValueRule)
        assert isinstance(is_not_equal_to_value("test"), EqualsToValueRule)
        
        # Field-based rules
        assert isinstance(is_equal_to_value_from_field("test"), EqualsToFieldRule)
        assert isinstance(is_not_included_in_values_from_field("test"), EqualsToFieldRule)
        
        # Required rule
        assert isinstance(is_required(), RequiredRule)
        
        # Column validation rules
        assert isinstance(has_unique_column_values_in_table("test"), ColumnValidationRule)
        assert isinstance(has_unique_in_column("test"), ColumnValidationRule)
        
        # Column from field validation rules
        assert isinstance(is_all_unique_in_column_from_field("test"), ColumnFromFieldValidationRule)
        assert isinstance(has_multiple_column_values_from_field_in_table("test"), ColumnFromFieldValidationRule)

    def test_all_functions_produce_valid_dicts(self):
        """Test that all functions produce valid dictionary representations"""
        rules = [
            is_equal_to_value("test_value"),
            is_not_equal_to_value("test_value"),
            is_equal_to_value_from_field("test_field"),
            is_not_included_in_values_from_field("test_field"),
            is_required(),
            has_unique_column_values_in_table("test_column"),
            has_unique_in_column("test_column"),
            is_all_unique_in_column_from_field("test_field"),
            has_multiple_column_values_from_field_in_table("test_field")
        ]
        
        for rule in rules:
            result = rule.as_dict()
            assert isinstance(result, dict)
            assert "name" in result
            assert isinstance(result["name"], str)

    def test_function_consistency(self):
        """Test that functions are consistent in their behavior"""
        # Test that equal and not_equal functions work consistently
        equal_rule = is_equal_to_value("test")
        not_equal_rule = is_not_equal_to_value("test")
        
        assert equal_rule.value == not_equal_rule.value
        assert equal_rule.rule_name != not_equal_rule.rule_name
        
        # Test that field-based functions work consistently
        equal_field_rule = is_equal_to_value_from_field("test")
        not_equal_field_rule = is_not_included_in_values_from_field("test")
        
        assert equal_field_rule.field == not_equal_field_rule.field
        assert equal_field_rule.rule_name != not_equal_field_rule.rule_name 