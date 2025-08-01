"""
Field utilities for form building and validation.
"""

# Import field helper functions
from .field_helpers import (
    boolean_field,
    string_field,
    number_field,
    select_field,
    experiment_design_field,
    condition_column_field,
    condition_comparisons_field,
    control_variables_field,
    numberrange_field,
    intensity_input_dataset_field,
)

# Import rules and rule builders
from .rules_builder import (
    is_equal_to_value,
    is_not_equal_to_value,
    is_equal_to_value_from_field,
    is_not_equal_to_value_from_field,
    is_required,
    is_all_unique_in_column,
    has_unique_in_column,
    is_all_unique_in_column_from_field,
    has_unique_in_column_from_field,
)

# Import When class
from .when import When

# Import base classes for extensibility
from .rules import Rule, EqualsToValueRule, EqualsToFieldRule, RequiredRule, ColumnValidationRule, ColumnFromFieldValidationRule

__all__ = [
    # Field helpers
    "boolean_field",
    "string_field", 
    "number_field",
    "select_field",
    "experiment_design_field",
    "condition_column_field",
    "condition_comparisons_field",
    "control_variables_field",
    "numberrange_field",
    "intensity_input_dataset_field",
    
    # Rules
    "is_equal_to_value",
    "is_not_equal_to_value", 
    "is_equal_to_value_from_field",
    "is_not_equal_to_value_from_field",
    "is_required",
    "is_all_unique_in_column",
    "has_unique_in_column",
    "is_all_unique_in_column_from_field",
    "has_unique_in_column_from_field",
    
    # Classes
    "When",
    "Rule",
    "EqualsToValueRule",
    "EqualsToFieldRule", 
    "RequiredRule",
    "ColumnValidationRule",
    "ColumnFromFieldValidationRule",
] 