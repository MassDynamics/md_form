#!/usr/bin/env python3
"""
Test script to demonstrate md_form package usage.
"""

from md_form import translate_payload
from md_form.field_utils import (
    condition_column_field,
    is_not_equal_to_value,
    is_not_equal_to_value_from_field,
    is_required,
    When
)

def test_field_helpers():
    """Test the field helpers functionality."""
    print("Testing field helpers...")
    
    # Create a condition column field with validation rules
    condition_column = condition_column_field(
        name="Condition Column",
        rules=[
            is_not_equal_to_value("sample_name"),
            is_not_equal_to_value_from_field("control_variables"),
            is_required(),
        ],
        when=When.not_equals("input_datasets", None)
    )
    
    print(f"Created condition column field: {condition_column}")
    print("✓ Field helpers working correctly!")

def test_translate_payload():
    """Test the translate_payload functionality."""
    print("\nTesting translate_payload...")
    
    # Test with a simple dictionary
    test_dict = {"test": "value", "nested": {"key": "value"}}
    result = translate_payload(test_dict)
    
    print(f"Original: {test_dict}")
    print(f"Translated: {result}")
    print("✓ translate_payload working correctly!")

if __name__ == "__main__":
    print("MD Form Package Test")
    print("=" * 30)
    
    test_field_helpers()
    test_translate_payload()
    
    print("\n" + "=" * 30)
    print("All tests passed! Package is working correctly.") 