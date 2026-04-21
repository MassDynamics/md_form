"""
Field utilities for form building and validation.
"""

# Import field helper functions
from .field_helpers import (
    boolean_field,
    string_field,
    number_field,
    select_field,
    multiple_select_field,
    experiment_design_field,
    condition_column_field,
    condition_comparisons_field,
    control_variables_field,
    numberrange_field,
    intensity_input_dataset_field,
    sample_metadata_value_field,
)

# Import rules and rule builders
from .rules_builder import (
    is_equal_to_value,
    is_not_equal_to_value,
    is_equal_to_value_from_field,
    is_not_included_in_values_from_field,
    is_required,
    has_unique_column_values_in_table,
    has_unique_in_column,
    is_all_unique_in_column_from_field,
    has_multiple_column_values_from_field_in_table,
)

# Import When class and evaluation
from .when import When, evaluate_when

# Import conditional validation mixin
from .conditional_validator import ConditionalRequiredMixin

# Import base classes for extensibility
from .rules import Rule, EqualsToValueRule, EqualsToFieldRule, RequiredRule, ColumnValidationRule, ColumnFromFieldValidationRule

__all__ = [
    # Field helpers
    "boolean_field",
    "string_field", 
    "number_field",
    "select_field",
    "multiple_select_field",
    "experiment_design_field",
    "condition_column_field",
    "condition_comparisons_field",
    "control_variables_field",
    "numberrange_field",
    "intensity_input_dataset_field",
    "sample_metadata_value_field",

    # Rules
    "is_equal_to_value",
    "is_not_equal_to_value", 
    "is_equal_to_value_from_field",
    "is_not_included_in_values_from_field",
    "is_required",
    "has_unique_column_values_in_table",
    "has_unique_in_column",
    "is_all_unique_in_column_from_field",
    "has_multiple_column_values_from_field_in_table",
    
    # Classes
    "When",
    "evaluate_when",
    "ConditionalRequiredMixin",
    "Rule",
    "EqualsToValueRule",
    "EqualsToFieldRule", 
    "RequiredRule",
    "ColumnValidationRule",
    "ColumnFromFieldValidationRule",
] 