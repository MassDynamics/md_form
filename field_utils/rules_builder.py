from typing import Any
from field_utils.rules import EqualsToValueRule, EqualsToFieldRule, ColumnValidationRule, ColumnFromFieldValidationRule, RequiredRule
from typeguard import typechecked
import inspect


@typechecked
def is_equal_to_value(value: Any) -> EqualsToValueRule:
    function_name = inspect.currentframe().f_code.co_name
    return EqualsToValueRule(function_name, value)

@typechecked
def is_not_equal_to_value(value: Any) -> EqualsToValueRule:
    function_name = inspect.currentframe().f_code.co_name
    return EqualsToValueRule(function_name, value)

@typechecked
def is_equal_to_value_from_field(field: str) -> EqualsToFieldRule:
    function_name = inspect.currentframe().f_code.co_name
    return EqualsToFieldRule(function_name, field)

@typechecked
def is_not_equal_to_value_from_field(field: str) -> EqualsToFieldRule:
    function_name = inspect.currentframe().f_code.co_name
    return EqualsToFieldRule(function_name, field)

@typechecked
def is_required() -> RequiredRule:
    function_name = inspect.currentframe().f_code.co_name
    return RequiredRule(function_name)

@typechecked
def is_all_unique_in_column(column: str) -> ColumnValidationRule:
    function_name = inspect.currentframe().f_code.co_name
    return ColumnValidationRule(function_name, column)

@typechecked
def has_unique_in_column(column: str) -> ColumnValidationRule:
    function_name = inspect.currentframe().f_code.co_name
    return ColumnValidationRule(function_name, column)

@typechecked
def is_all_unique_in_column_from_field(field: str) -> ColumnFromFieldValidationRule:
    function_name = inspect.currentframe().f_code.co_name
    return ColumnFromFieldValidationRule(function_name, field)

@typechecked
def has_unique_in_column_from_field(field: str) -> ColumnFromFieldValidationRule:
    function_name = inspect.currentframe().f_code.co_name
    return ColumnFromFieldValidationRule(function_name, field) 