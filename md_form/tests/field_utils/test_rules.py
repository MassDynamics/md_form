import pytest
from field_utils.rules import (
    Rule, EqualsToValueRule, EqualsToFieldRule, RequiredRule,
    ColumnValidationRule, ColumnFromFieldValidationRule
)


class TestRule:
    """Test cases for the base Rule class"""

    def test_rule_base_class(self):
        """Test that Rule is an abstract base class"""
        rule = Rule()
        
        # Test that as_dict raises NotImplementedError
        with pytest.raises(NotImplementedError):
            rule.as_dict()


class TestEqualsToValueRule:
    """Test cases for the EqualsToValueRule class"""

    @pytest.fixture
    def equals_rule(self):
        """Fixture for an EqualsToValueRule instance"""
        return EqualsToValueRule("test_rule", "test_value")

    def test_equals_to_value_rule_initialization(self):
        """Test EqualsToValueRule initialization"""
        rule = EqualsToValueRule("rule_name", "rule_value")
        
        assert rule.rule_name == "rule_name"
        assert rule.value == "rule_value"

    def test_equals_to_value_rule_as_dict(self, equals_rule):
        """Test as_dict method for EqualsToValueRule"""
        result = equals_rule.as_dict()
        
        expected = {
            "name": "test_rule",
            "parameters": {
                "value": "test_value"
            }
        }
        assert result == expected

    def test_equals_to_value_rule_with_different_value_types(self):
        """Test EqualsToValueRule with different value types"""
        # String value
        rule_str = EqualsToValueRule("rule", "string_value")
        result = rule_str.as_dict()
        assert result["parameters"]["value"] == "string_value"
        
        # Integer value
        rule_int = EqualsToValueRule("rule", 42)
        result = rule_int.as_dict()
        assert result["parameters"]["value"] == 42
        
        # Boolean value
        rule_bool = EqualsToValueRule("rule", True)
        result = rule_bool.as_dict()
        assert result["parameters"]["value"] is True
        
        # List value
        rule_list = EqualsToValueRule("rule", [1, 2, 3])
        result = rule_list.as_dict()
        assert result["parameters"]["value"] == [1, 2, 3]

    def test_equals_to_value_rule_with_none_value(self):
        """Test EqualsToValueRule with None value"""
        rule = EqualsToValueRule("rule", None)
        result = rule.as_dict()
        
        expected = {
            "name": "rule",
            "parameters": {
                "value": None
            }
        }
        assert result == expected


class TestEqualsToFieldRule:
    """Test cases for the EqualsToFieldRule class"""

    @pytest.fixture
    def equals_field_rule(self):
        """Fixture for an EqualsToFieldRule instance"""
        return EqualsToFieldRule("test_rule", "test_field")

    def test_equals_to_field_rule_initialization(self):
        """Test EqualsToFieldRule initialization"""
        rule = EqualsToFieldRule("rule_name", "field_name")
        
        assert rule.rule_name == "rule_name"
        assert rule.field == "field_name"

    def test_equals_to_field_rule_as_dict(self, equals_field_rule):
        """Test as_dict method for EqualsToFieldRule"""
        result = equals_field_rule.as_dict()
        
        expected = {
            "name": "test_rule",
            "parameters": {
                "field": "test_field"
            }
        }
        assert result == expected

    def test_equals_to_field_rule_with_different_field_names(self):
        """Test EqualsToFieldRule with different field names"""
        # Simple field name
        rule1 = EqualsToFieldRule("rule", "simple_field")
        result = rule1.as_dict()
        assert result["parameters"]["field"] == "simple_field"
        
        # Field name with underscores
        rule2 = EqualsToFieldRule("rule", "field_with_underscores")
        result = rule2.as_dict()
        assert result["parameters"]["field"] == "field_with_underscores"
        
        # Field name with dashes
        rule3 = EqualsToFieldRule("rule", "field-with-dashes")
        result = rule3.as_dict()
        assert result["parameters"]["field"] == "field-with-dashes"


class TestRequiredRule:
    """Test cases for the RequiredRule class"""

    @pytest.fixture
    def required_rule(self):
        """Fixture for a RequiredRule instance"""
        return RequiredRule("test_rule")

    def test_required_rule_initialization(self):
        """Test RequiredRule initialization"""
        rule = RequiredRule("rule_name")
        
        assert rule.rule_name == "rule_name"

    def test_required_rule_as_dict(self, required_rule):
        """Test as_dict method for RequiredRule"""
        result = required_rule.as_dict()
        
        expected = {
            "name": "test_rule"
        }
        assert result == expected

    def test_required_rule_no_parameters(self):
        """Test that RequiredRule has no parameters in the dict"""
        rule = RequiredRule("test_rule")
        result = rule.as_dict()
        
        assert "parameters" not in result
        assert "name" in result


class TestColumnValidationRule:
    """Test cases for the ColumnValidationRule class"""

    @pytest.fixture
    def column_rule(self):
        """Fixture for a ColumnValidationRule instance"""
        return ColumnValidationRule("test_rule", "test_column")

    def test_column_validation_rule_initialization(self):
        """Test ColumnValidationRule initialization"""
        rule = ColumnValidationRule("rule_name", "column_name")
        
        assert rule.rule_name == "rule_name"
        assert rule.column == "column_name"

    def test_column_validation_rule_as_dict(self, column_rule):
        """Test as_dict method for ColumnValidationRule"""
        result = column_rule.as_dict()
        
        expected = {
            "name": "test_rule",
            "parameters": {
                "column": "test_column"
            }
        }
        assert result == expected

    def test_column_validation_rule_with_different_column_names(self):
        """Test ColumnValidationRule with different column names"""
        # Simple column name
        rule1 = ColumnValidationRule("rule", "simple_column")
        result = rule1.as_dict()
        assert result["parameters"]["column"] == "simple_column"
        
        # Column name with spaces
        rule2 = ColumnValidationRule("rule", "column with spaces")
        result = rule2.as_dict()
        assert result["parameters"]["column"] == "column with spaces"
        
        # Column name with special characters
        rule3 = ColumnValidationRule("rule", "column_123")
        result = rule3.as_dict()
        assert result["parameters"]["column"] == "column_123"


class TestColumnFromFieldValidationRule:
    """Test cases for the ColumnFromFieldValidationRule class"""

    @pytest.fixture
    def column_from_field_rule(self):
        """Fixture for a ColumnFromFieldValidationRule instance"""
        return ColumnFromFieldValidationRule("test_rule", "test_field")

    def test_column_from_field_validation_rule_initialization(self):
        """Test ColumnFromFieldValidationRule initialization"""
        rule = ColumnFromFieldValidationRule("rule_name", "field_name")
        
        assert rule.rule_name == "rule_name"
        assert rule.field == "field_name"

    def test_column_from_field_validation_rule_as_dict(self, column_from_field_rule):
        """Test as_dict method for ColumnFromFieldValidationRule"""
        result = column_from_field_rule.as_dict()
        
        expected = {
            "name": "test_rule",
            "parameters": {
                "field": "test_field"
            }
        }
        assert result == expected

    def test_column_from_field_validation_rule_with_different_field_names(self):
        """Test ColumnFromFieldValidationRule with different field names"""
        # Simple field name
        rule1 = ColumnFromFieldValidationRule("rule", "simple_field")
        result = rule1.as_dict()
        assert result["parameters"]["field"] == "simple_field"
        
        # Field name with underscores
        rule2 = ColumnFromFieldValidationRule("rule", "field_with_underscores")
        result = rule2.as_dict()
        assert result["parameters"]["field"] == "field_with_underscores"


class TestRulesIntegration:
    """Integration tests for all rule types"""

    def test_all_rule_types_have_as_dict_method(self):
        """Test that all rule types implement as_dict method"""
        rules = [
            EqualsToValueRule("test", "value"),
            EqualsToFieldRule("test", "field"),
            RequiredRule("test"),
            ColumnValidationRule("test", "column"),
            ColumnFromFieldValidationRule("test", "field")
        ]
        
        for rule in rules:
            result = rule.as_dict()
            assert isinstance(result, dict)
            assert "name" in result

    def test_rule_types_different_parameters(self):
        """Test that different rule types have different parameter structures"""
        # EqualsToValueRule has "value" parameter
        value_rule = EqualsToValueRule("test", "value")
        value_dict = value_rule.as_dict()
        assert "value" in value_dict["parameters"]
        
        # EqualsToFieldRule has "field" parameter
        field_rule = EqualsToFieldRule("test", "field")
        field_dict = field_rule.as_dict()
        assert "field" in field_dict["parameters"]
        
        # RequiredRule has no parameters
        required_rule = RequiredRule("test")
        required_dict = required_rule.as_dict()
        assert "parameters" not in required_dict
        
        # ColumnValidationRule has "column" parameter
        column_rule = ColumnValidationRule("test", "column")
        column_dict = column_rule.as_dict()
        assert "column" in column_dict["parameters"]
        
        # ColumnFromFieldValidationRule has "field" parameter
        column_field_rule = ColumnFromFieldValidationRule("test", "field")
        column_field_dict = column_field_rule.as_dict()
        assert "field" in column_field_dict["parameters"]

    def test_rule_inheritance(self):
        """Test that all rule classes inherit from Rule"""
        rules = [
            EqualsToValueRule("test", "value"),
            EqualsToFieldRule("test", "field"),
            RequiredRule("test"),
            ColumnValidationRule("test", "column"),
            ColumnFromFieldValidationRule("test", "field")
        ]
        
        for rule in rules:
            assert isinstance(rule, Rule) 