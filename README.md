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
- `parameters`: Dict of custom UI parameters to merge into `json_schema_extra.parameters`. These are merged with any existing parameters from the field helper, allowing you to customise or extend the default behaviour.

Note: Fields are optional by default (`default=None`). Include `is_required()` in `rules` to make a field required.

#### Parameter Merging

The `parameters` argument allows you to customise field behaviour by merging custom UI parameters with the field helper's default parameters. The merging logic works as follows:

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


#### Dynamic options

A `select_field`'s (or `multiple_select_field`'s) `options` can resolve at runtime from another field's value. Pass a `{ref, cases}` object — either directly as `options` or via `parameters` — and `cases[key]` may be a flat list of strings or a pre-shaped list of `{name, value}` dicts. Flat string lists are normalized to `[{"name": s, "value": s}, ...]` automatically (mirroring the flat-list behaviour of `options=["a", "b"]`).

```python
species = select_field(
    name="Species",
    options=["Human", "Mouse"],
)

# Flat-string cases (recommended when name == value)
knowledge_bases = select_field(
    name="Knowledge Bases",
    options={
        "ref": "species",
        "cases": {
            "Human": ["reactome_human", "kegg_human"],
            "Mouse": ["reactome_mouse", "kegg_mouse"],
        },
    },
)

# Pre-shaped cases (when display name differs from value)
knowledge_bases = select_field(
    name="Knowledge Bases",
    parameters={
        "options": {
            "ref": "species",
            "cases": {
                "Human": [
                    {"name": "Reactome (Human)", "value": "reactome_human"},
                    {"name": "KEGG (Human)", "value": "kegg_human"},
                ],
                "Mouse": [
                    {"name": "Reactome (Mouse)", "value": "reactome_mouse"},
                    {"name": "KEGG (Mouse)", "value": "kegg_mouse"},
                ],
            },
        },
    },
)
```

- When the referenced field's value matches a case, that array is used as the options.
- When the referenced field is empty or its value doesn't match any case, resolved options are `undefined` and the dependent field renders with no options.
- When the user changes the referenced field, the dependent field's value resets and re-renders.
- At the helper level (`options={...}`), each `cases[key]` must be a list of strings — mixed or pre-shaped lists raise `ValueError`. When passing pre-shaped lists, use `parameters={"options": {...}}`; the `translate_payload` pipeline passes already-normalized `cases` through untouched.

#### Common helpers

- `boolean_field(default=None, label=None)`
- `string_field(default=None, disabled=False)`
- `number_field(field_data_type, default=None, ge=None, le=None)`
  - `field_data_type` must always be passed: `FieldDataType.INT` or `FieldDataType.FLOAT` (emitted as `parameters.fieldDataType`), or `None` to accept either
- `select_field(default=None, options=None, discriminator=None)`
  - `options` is a list of strings; each option becomes `{ "name": v, "value": v }` (name equals value)
  - `discriminator` is passed through for downstream oneOf selection
- `radio_selection_field(default=None, options=None, inline=None)`
  - Picks one option, shown as radio buttons (`fieldType: "RadioSelectionField"`)
  - `options` works as in `select_field`; `inline=True` lays the buttons out on one line
- `selection_type_field(default="selection", inline=None)`
  - A `radio_selection_field` that always has the options `{"name": "Use Selection", "value": "selection"}` and `{"name": "Use List", "value": "list"}`
  - Emits `parameters.selectionType: true` so the frontend can tell it apart from an ordinary radio
- `numberrange_field(field_data_type, default=None, ge=None, le=None, interval=None)`
  - `field_data_type` must always be passed, as for `number_field`

#### Domain-specific helpers

- `experiment_design_field()`
- `condition_column_field(datasets_ref="input_datasets")`
  - `datasets_ref` names the field holding the datasets whose sample metadata columns are offered
- `condition_comparisons_field()`
  - Picks any number of comparisons from the conditions in this form's own experiment design
    (`fieldType: "PairwiseConditionComparisons"`)
  - The value is `{"condition_comparison_pairs": [["C1", "C2"], ...]}`
- `condition_comparison_field(datasets_ref="input_datasets")`
  - Picks one comparison already in the dataset chosen in the `datasets_ref` field
    (`fieldType: "ConditionComparison"`), and which way round to read it
  - The value is `{"comparison": {"condition_pair": "C7 - C5", "left": "C5", "right": "C7"}}`:
    `condition_pair` is the dataset's comparison, and `left` and `right` are its two conditions, each of which
    must appear in `condition_pair`, in either order
- `control_variables_field(default=None)`
- `intensity_input_dataset_field()`
- `intensity_input_datasets_field(entity_types=None, min=1, max=None)`
  - `entity_types` is a list of `EntityType` values, e.g. `["protein", "gene"]`
- `entity_type_field(default=None, datasets_ref="input_datasets")`
  - `default` is an `EntityType` value, e.g. `"protein"`
  - `datasets_ref` names the dataset field it applies to; the datasets selected there must have the chosen entity type
- `sample_metadata_values_filter_field(column_ref="filter_based_on_condition", datasets_ref="input_datasets",
  filterable=None, sortable=None, advanced_filtering=None, ignored_values=None)`
  - Picks values to keep from the sample metadata column chosen in the `column_ref` field
    (`fieldType: "SampleMetadataValuesFilter"`)
  - The value is `{"values": ["C1", "C3"], "filters": [{"column": "batch", "value": ["B1"]}]}`: `values` are
    different, non-empty strings, none of them in `ignored_values`; `filters` (only filled in with
    `advanced_filtering`) may be left out
- `dataset_param_multiple_field(datasets_ref="input_datasets", initialise_with_all=True)`
  - Picks any of the databases recorded in the job run params of the dataset chosen in the `datasets_ref` field
    (`fieldType: "DatasetParamMultiple"`): the knowledge bases and analysis set names of its `Databases` params
    or, failing those, its `sets`
  - The value is a list of different database names, e.g. `["GO - Biological Process", "MSigDB-H (hallmark gene sets)"]`
  - With `initialise_with_all`, the frontend starts with every database selected
  - When `validate_form` is given `datasets`, each name must be one of the dataset's databases
- `plot_size_field(width=None, height=None)`
  - The value is `{"fixed": False}` (fit to module) or `{"fixed": True, "width": <px>, "height": <px>}`,
    with width and height ints between 1 and 1000
  - The default is `{"fixed": False}`; pass both `width` and `height` to default to a fixed size
- `scientific_notation_field(default=None)`
  - The value is a string holding a finite number, such as `"1.5e-3"` or `"0.0015"`
  - A `default` that isn't such a number raises `ValueError`
- `fold_change_threshold_field(default=None)`
  - The value is a float of at least 1 (an int such as `2` counts, as JSON sends `2.0` as `2`);
    the frontend also shows its log2 ratio
  - A `default` below 1 raises `ValueError`
- `entity_list_field(type=None, owner_only=None)`
  - Picks a single entity list (`fieldType: "ProteinList"`); the value is the list's id, a non-empty string
  - `type` filters the lists by entity type; `owner_only=True` offers only the user's own lists
  - Unlike `entity_list_entity_ids_field` the value is the id rather than the list's entity ids, and unlike
    `entity_lists_field` only one list is picked
- `entity_title_field(entity_type=None, datasets_ref=None, include_hierarchical_entities=None)`
  - Picks the column used to label entities (`fieldType: "EntityTitle"`); the value is a column name such as `"protein_name"`
  - The entity type comes from `entity_type` (a value or a `{"ref": "<field>"}` dict) or else the datasets in
    `datasets_ref`; with neither the frontend uses `"protein"`
  - The value must be one of that entity type's title columns: protein `protein_name`/`gene_name`, peptide
    `modified_sequence`/`gene_name`, gene `gene_name`/`gene_id`, metabolite `metabolite_id`, ptm `ptm_protein`/`gene_name`
  - `include_hierarchical_entities=True` also allows the parent type's columns (protein's for peptide and ptm)
  - When the entity type comes from the datasets, only that the value is a string is checked
- `EntityType` is `Literal["protein", "peptide", "gene", "metabolite", "ptm", "precursor"]`. It is also taken by
  `intensity_input_dataset_field`, `datasets_field` (`entity_types`), and by `entity_list_entity_ids_field`,
  `entity_list_field`, `entity_lists_field` (`type`), `entity_title_field` (`entity_type`) and `databases_field` (`entity_type`), which also accept a `{"ref": "<field>"}` dict.
  Any other string is rejected.

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

Key behaviours:

- Keeps only allowed second-layer keys: `fieldType`, `parameters`, `name`, `rules`, `description`, `default`, `when`
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