from enum import Enum
from typing import Dict, Any, Union, Literal, TypeVar, Generic, List
from pydantic import BaseModel


class FieldType(str, Enum):
    """Enum for common field types to prevent typos"""
    STRING = "String"
    BOOLEAN = "Boolean"
    NUMBER = "Number"
    NUMBER_RANGE = "NumberRange"
    EXPERIMENT_DESIGN = "ExperimentDesign"
    CONDITION_COLUMN = "DatasetSampleMetadata"
    CONDITION_COMPARISONS = "ConditionComparisons"
    CONTROL_VARIABLES = "ControlVariables"
    INTENSITY_INPUT_DATASET = "DatasetSearchSelect"