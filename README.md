# MD Form Package

A Python package for form field helpers and payload translation utilities.

## Installation

```bash
pip install git+https://github.com/MassDynamics/md_form.git
```

## Usage

### Field Helpers

The package provides field helper functions for creating form fields with validation rules and conditional visibility. All helpers accept common parameters via the decorator:

- `name`: Display name
- `description`: Help text
- `when`: A `When` condition to control visibility
- `rules`: A rule or list of rules from `md_form.field_utils.rules`
- `parameters`: Dict of custom UI parameters to merge into `json_schema_extra.parameters`. These are merged with any existing parameters from the field helper, allowing you to customize or extend the default behavior.

Note: Fields are optional by default (`default=None`). Include `is_required()` in `rules` to make a field required.

#### Parameter Merging

The `parameters` argument allows you to customize field behavior by merging custom UI parameters with the field helper's default parameters. The merging logic works as follows:

1. **Field helpers provide default parameters** - Each helper function includes sensible defaults (e.g., `select_field` includes `options`, `control_variables_field` includes `radioOptions`)
2. **Custom parameters are merged** - Your custom `parameters` dict is merged into the existing `json_schema_extra.parameters`
3. **Custom parameters take precedence** - If you provide a parameter with the same key as a default, your value will override the default
4. **New parameters are added** - Any new parameters you provide are added to the existing set

**Example:**
```python
# control_variables_field has default parameters.radioOptions = ["categorical", "numerical"]
control_vars = control_variables_field(
    name="Control Variables",
    parameters={
        "placeholder": "Select control variable type",  # New parameter
        "radioOptions": ["custom", "other"]            # Override default
    }
)
# Result: parameters.radioOptions = ["custom", "other"], parameters.placeholder = "Select control variable type"
```



#### Common helpers

- `boolean_field(default=None, label=None)`
- `string_field(default=None, disabled=False)`
- `number_field(default=None, ge=None, le=None)`
- `select_field(default=None, options=None, discriminator=None)`
  - `options` is a list of strings; each option becomes `{ "name": v, "value": v }` (name equals value)
  - `discriminator` is passed through for downstream oneOf selection
- `numberrange_field(default=None, ge=None, le=None, interval=None)`

#### Domain-specific helpers

- `experiment_design_field()`
- `condition_column_field()`
- `condition_comparisons_field()`
- `control_variables_field(default=None)`
- `intensity_input_dataset_field()`
- `entity_type_field(default=None)`

**Example:**
```python
from md_form.field_utils import (
    condition_column_field,
    is_not_equal_to_value,
    is_not_equal_to_value_from_field,
    is_required,
    When
)

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
```

### Available Rules

- **`is_equal_to_value(value)`** - Validates that a field equals a specific literal value
- **`is_not_equal_to_value(value)`** - Validates that a field does not equal a specific literal value  
- **`is_equal_to_value_from_field(field)`** - Validates that a field equals the value of another specified field
- **`is_not_equal_to_value_from_field(field)`** - Validates that a field does not equal the value of another specified field
- **`is_required()`** - Marks a field as required/mandatory
- **`is_all_unique_in_column(column)`** - Ensures all values in a specified column are unique (no duplicates)
- **`has_unique_in_column(column)`** - Ensures at least one unique value exists in a specified column
- **`is_all_unique_in_column_from_field(field)`** - Ensures all values in a column (specified by another field) are unique
- **`has_unique_in_column_from_field(field)`** - Ensures at least one unique value exists in a column (specified by another field)

### When Conditions

Use the `When` class to create conditional logic:

```python
from md_form.field_utils import When

# Field is shown when input_datasets is not None
when = When.not_equals("input_datasets", None)

# Field is shown when some_field equals "value"
when = When.equals("some_field", "value")
```

### Payload Translation

Use the `translate_payload` function to transform JSON-schema-like payloads to a simplified form schema suitable for UI rendering.

Key behaviors:

- Keeps only allowed second-layer keys: `field_type`, `parameters`, `name`, `rules`, `description`, `default`, `when`
- Converts `enum: [v1, v2]` to `parameters.options: [{"name": v, "value": v}]` (name equals value)
- Renames keys: `maximum/minimum -> max/min`, `maxItems/minItems -> max/min`
- Moves `options`, `min`, `max` into `parameters`
- Flattens `$ref` and nested `properties`; resolves `oneOf` with `discriminator` by inlining referenced sub-properties
- Removes top-level `output_dataset_type` and non-object nodes

```python
from md_form import translate_payload

# Transform function parameters schema (example)
parameters_new = translate_payload(dict(fn.parameters))
```

## Development

To install in development mode:

```bash
pip install -e .
``` 