import pytest
from md_form.field_utils.when import When


class TestWhen:
    """Test cases for the When class"""

    @pytest.fixture
    def when_equals(self):
        """Fixture for a When instance with equals condition"""
        return When.equals("test_property", "test_value")

    @pytest.fixture
    def when_not_equals(self):
        """Fixture for a When instance with not_equals condition"""
        return When.not_equals("test_property", "test_value")

    @pytest.fixture
    def when_custom(self):
        """Fixture for a When instance with custom condition"""
        return When("test_property", "custom_condition", "custom_value")

    def test_when_initialization(self):
        """Test When class initialization"""
        when = When("property_name", "condition_type", "condition_value")
        
        assert when.property == "property_name"
        assert when.condition_type == "condition_type"
        assert when.value == "condition_value"

    def test_when_equals_class_method(self):
        """Test the equals class method"""
        when = When.equals("property_name", "value")
        
        assert when.property == "property_name"
        assert when.condition_type == "equals"
        assert when.value == "value"

    def test_when_not_equals_class_method(self):
        """Test the not_equals class method"""
        when = When.not_equals("property_name", "value")
        
        assert when.property == "property_name"
        assert when.condition_type == "not_equals"
        assert when.value == "value"

    def test_when_as_dict_equals(self, when_equals):
        """Test as_dict method for equals condition"""
        result = when_equals.as_dict()
        
        expected = {
            "property": "test_property",
            "equals": "test_value"
        }
        assert result == expected

    def test_when_as_dict_not_equals(self, when_not_equals):
        """Test as_dict method for not_equals condition"""
        result = when_not_equals.as_dict()
        
        expected = {
            "property": "test_property",
            "not_equals": "test_value"
        }
        assert result == expected

    def test_when_as_dict_custom_condition(self, when_custom):
        """Test as_dict method for custom condition"""
        result = when_custom.as_dict()
        
        expected = {
            "property": "test_property",
            "custom_condition": "custom_value"
        }
        assert result == expected

    def test_when_with_different_value_types(self):
        """Test When with different value types"""
        # String value
        when_str = When.equals("property", "string_value")
        assert when_str.value == "string_value"
        
        # Integer value
        when_int = When.equals("property", 42)
        assert when_int.value == 42
        
        # Boolean value
        when_bool = When.equals("property", True)
        assert when_bool.value is True
        
        # List value
        when_list = When.equals("property", [1, 2, 3])
        assert when_list.value == [1, 2, 3]

    def test_when_with_special_characters(self):
        """Test When with special characters in property names"""
        when = When.equals("property_with_underscores", "value")
        assert when.property == "property_with_underscores"
        
        when = When.equals("property-with-dashes", "value")
        assert when.property == "property-with-dashes"

    def test_when_equality(self):
        """Test When object equality"""
        when1 = When.equals("property", "value")
        when2 = When.equals("property", "value")
        when3 = When.equals("different_property", "value")
        when4 = When.not_equals("property", "value")
        
        assert when1.property == when2.property
        assert when1.condition_type == when2.condition_type
        assert when1.value == when2.value
        
        assert when1.property != when3.property
        assert when1.condition_type != when4.condition_type

    def test_when_repr(self):
        """Test string representation of When objects"""
        when = When.equals("test_property", "test_value")
        repr_str = repr(when)
        
        assert "When" in repr_str
        # The default repr doesn't include the property names, just the object address
        assert "When object" in repr_str or "When" in repr_str

    def test_when_with_none_value(self):
        """Test When with None value"""
        when = When.equals("property", None)
        result = when.as_dict()
        
        expected = {
            "property": "property",
            "equals": None
        }
        assert result == expected

    def test_when_with_empty_string(self):
        """Test When with empty string value"""
        when = When.equals("property", "")
        result = when.as_dict()
        
        expected = {
            "property": "property",
            "equals": ""
        }
        assert result == expected

    def test_when_with_complex_objects(self):
        """Test When with complex object values"""
        complex_obj = {"key": "value", "nested": {"data": 123}}
        when = When.equals("property", complex_obj)
        result = when.as_dict()
        
        expected = {
            "property": "property",
            "equals": complex_obj
        }
        assert result == expected

    def test_when_multiple_instances(self):
        """Test creating multiple When instances"""
        when1 = When.equals("prop1", "value1")
        when2 = When.not_equals("prop2", "value2")
        when3 = When("prop3", "custom", "value3")
        
        assert when1.property == "prop1"
        assert when2.property == "prop2"
        assert when3.property == "prop3"
        
        assert when1.condition_type == "equals"
        assert when2.condition_type == "not_equals"
        assert when3.condition_type == "custom"

    def test_when_all_of_simple(self):
        """Test When.all_of with simple conditions"""
        when = When.all_of(
            When.is_present("input_datasets"),
            When.equals("entity_type", "protein")
        )
        
        assert when.operator == "and"
        assert len(when.conditions) == 2
        assert when.conditions[0].property == "input_datasets"
        assert when.conditions[0].condition_type == "is_present"
        assert when.conditions[1].property == "entity_type"
        assert when.conditions[1].condition_type == "equals"
        assert when.conditions[1].value == "protein"

    def test_when_any_of_simple(self):
        """Test When.any_of with simple conditions"""
        when = When.any_of(
            When.equals("filter_values_criteria", "count"),
            When.equals("filter_values_criteria", "percentage")
        )
        
        assert when.operator == "or"
        assert len(when.conditions) == 2
        assert when.conditions[0].property == "filter_values_criteria"
        assert when.conditions[0].value == "count"
        assert when.conditions[1].property == "filter_values_criteria"
        assert when.conditions[1].value == "percentage"

    def test_when_all_of_as_dict(self):
        """Test as_dict for When.all_of"""
        when = When.all_of(
            When.is_present("experiment_design"),
            When.is_present("condition_column")
        )
        
        result = when.as_dict()
        expected = {
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
        }
        assert result == expected

    def test_when_any_of_as_dict(self):
        """Test as_dict for When.any_of"""
        when = When.any_of(
            When.equals("filter_values_criteria", "count"),
            When.equals("filter_values_criteria", "percentage")
        )
        
        result = when.as_dict()
        expected = {
            "operator": "or",
            "conditions": [
                {
                    "property": "filter_values_criteria",
                    "equals": "count"
                },
                {
                    "property": "filter_values_criteria",
                    "equals": "percentage"
                }
            ]
        }
        assert result == expected

    def test_when_nested_conditions(self):
        """Test nested When conditions"""
        when = When.all_of(
            When.is_present("input_datasets"),
            When.any_of(
                When.equals("entity_type", "protein"),
                When.equals("entity_type", "gene")
            )
        )
        
        result = when.as_dict()
        expected = {
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
                            "property": "entity_type",
                            "equals": "protein"
                        },
                        {
                            "property": "entity_type",
                            "equals": "gene"
                        }
                    ]
                }
            ]
        }
        assert result == expected

    def test_when_single_condition_all_of(self):
        """Test When.all_of with single condition"""
        when = When.all_of(When.equals("property", "value"))
        
        assert when.operator == "and"
        assert len(when.conditions) == 1
        assert when.conditions[0].property == "property"
        assert when.conditions[0].value == "value"

    def test_when_single_condition_any_of(self):
        """Test When.any_of with single condition"""
        when = When.any_of(When.is_present("property"))
        
        assert when.operator == "or"
        assert len(when.conditions) == 1
        assert when.conditions[0].property == "property"
        assert when.conditions[0].condition_type == "is_present"

    def test_when_empty_conditions(self):
        """Test When with empty conditions list"""
        when = When(operator="and", conditions=[])
        
        assert when.operator == "and"
        assert when.conditions == []
        
        result = when.as_dict()
        expected = {
            "operator": "and",
            "conditions": []
        }
        assert result == expected

    def test_when_mixed_condition_types(self):
        """Test When with mixed condition types"""
        when = When.all_of(
            When.equals("string_prop", "string_value"),
            When.not_equals("int_prop", 42),
            When.is_present("bool_prop")
        )
        
        result = when.as_dict()
        expected = {
            "operator": "and",
            "conditions": [
                {
                    "property": "string_prop",
                    "equals": "string_value"
                },
                {
                    "property": "int_prop",
                    "not_equals": 42
                },
                {
                    "property": "bool_prop",
                    "is_present": True
                }
            ]
        }
        assert result == expected

    def test_when_backward_compatibility(self):
        """Test that existing When usage still works"""
        # Test simple conditions still work as before
        when_equals = When.equals("property", "value")
        assert when_equals.property == "property"
        assert when_equals.condition_type == "equals"
        assert when_equals.value == "value"
        
        when_not_equals = When.not_equals("property", "value")
        assert when_not_equals.property == "property"
        assert when_not_equals.condition_type == "not_equals"
        assert when_not_equals.value == "value"
        
        when_is_present = When.is_present("property")
        assert when_is_present.property == "property"
        assert when_is_present.condition_type == "is_present"
        assert when_is_present.value is True
        
        # Test as_dict still works for simple conditions
        assert when_equals.as_dict() == {"property": "property", "equals": "value"}
        assert when_not_equals.as_dict() == {"property": "property", "not_equals": "value"}
        assert when_is_present.as_dict() == {"property": "property", "is_present": True} 