# MD Form Package

A Python package for form field helpers and payload translation utilities.

## Installation

```bash
pip install md_form
```

## Usage

### Field Helpers

The package provides field helper functions for creating form fields with validation rules:

```python
from md_form.field_utils import (
    condition_column_field,
    is_not_equal_to_value,
    is_not_equal_to_value_from_field,
    is_required,
    When
)

# Create a condition column field with validation rules
condition_column: str = condition_column_field(
    name="Condition Column",
    rules=[
        is_not_equal_to_value("sample_name"),
        is_not_equal_to_value_from_field("control_variables"),
        is_required(),
    ],
    when=When.not_equals("input_datasets", None)
)
```

### Available Field Helpers

- `boolean_field()` - Boolean fields
- `string_field()` - String fields  
- `number_field()` - Number fields
- `select_field()` - Select dropdown fields
- `experiment_design_field()` - Experiment design fields
- `condition_column_field()` - Condition column fields
- `condition_comparisons_field()` - Condition comparison fields
- `control_variables_field()` - Control variables fields
- `numberrange_field()` - Number range fields
- `intensity_input_dataset_field()` - Intensity input dataset fields

### Available Rules

- `is_equal_to_value(value)` - Field must equal a specific value
- `is_not_equal_to_value(value)` - Field must not equal a specific value
- `is_equal_to_value_from_field(field)` - Field must equal another field's value
- `is_not_equal_to_value_from_field(field)` - Field must not equal another field's value
- `is_required()` - Field is required
- `is_all_unique_in_column(column)` - All values in column must be unique
- `has_unique_in_column(column)` - Column must have unique values
- `is_all_unique_in_column_from_field(field)` - All values in column from field must be unique
- `has_unique_in_column_from_field(field)` - Column from field must have unique values

### When Conditions

Use the `When` class to create conditional logic:

```python
from md_form.field_utils import When

# Field is shown when input_datasets is not None
when=When.not_equals("input_datasets", None)

# Field is shown when some_field equals "value"
when=When.equals("some_field", "value")
```

### Payload Translation

Use the `translate_payload` function to transform payload dictionaries:

```python
from md_form import translate_payload

# Transform function parameters
parameters_new = translate_payload(dict(fn.parameters))
```

## Development

To install in development mode:

```bash
pip install -e .
```

## License

[Add your license information here] 