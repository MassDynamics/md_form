from enum import Enum
from typing import Dict, Any, Union, Literal, TypeVar, Generic, List
from pydantic import BaseModel


class FieldType(str, Enum):
    """Enum for common field types to prevent typos"""
    STRING = "String"
    BOOLEAN = "Boolean"
    NUMBER = "Number"
    NUMBER_RANGE = "NumberRange"
    EXPERIMENT_DESIGN = "SampleMetadataTable"
    CONDITION_COLUMN = "DatasetSampleMetadata"
    CONDITION_COLUMN_MULTI_SELECT = "SelectBySampleMetadata"
    CONDITION_COMPARISONS = "PairwiseConditionComparisons"
    CONTROL_VARIABLES = "PairwiseControlVariables"
    INTENSITY_INPUT_DATASET = "Datasets"
    ENTITY_TYPE = "EntityType"