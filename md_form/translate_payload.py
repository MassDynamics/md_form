import copy
from functools import partial


def translate_payload(payload: dict) -> dict:
    return _apply_pipeline(payload, _pipeline)

def _resolve_refs(schema: dict) -> dict:
    definitions = schema.get("definitions", {})
    def _resolve(node: dict) -> dict:
        if isinstance(node, dict):
            if "$ref" in node:
                ref_path = node["$ref"]
                if ref_path.startswith("#/definitions/"):
                    # Split the path to handle nested property references
                    path_parts = ref_path.split("/")
                    def_name = path_parts[2]  # Get the definition name
                    
                    if def_name not in definitions:
                        msg = f"Definition not found: {def_name}"  # TRY003, EM102
                        raise ValueError(msg)
                    
                    # Start with the base definition
                    resolved = copy.deepcopy(definitions[def_name])
                    
                    # Navigate through the nested path if it exists
                    if len(path_parts) > 3:
                        current = resolved
                        for part in path_parts[3:]:
                            if isinstance(current, dict) and part in current:
                                current = current[part]
                            else:
                                msg = f"Invalid path in $ref: {ref_path}"  # TRY003, EM102
                                raise ValueError(msg)
                        resolved = current
                    
                    # Preserve original values for duplicate keys
                    original_keys = {k: v for k, v in node.items() if k != "$ref"}
                    resolved = _resolve(resolved)
                    # Merge resolved with original, keeping original values for duplicates
                    merged = {**resolved, **original_keys}
                    return merged
                msg = "Unsupported $ref path: " + ref_path  # TRY003, EM102
                raise ValueError(msg)
            return {k: _resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_resolve(item) for item in node]
        return node
    resolved_schema = copy.deepcopy(schema)
    resolved_schema.pop("definitions", None)
    return _resolve(resolved_schema)

def _flatten_properties(schema: dict, key_to_flatten: str, parent_overwrites: bool = True) -> dict:
    def _flatten(node: dict) -> dict:
        if isinstance(node, dict):
            if key_to_flatten in node and isinstance(node[key_to_flatten], dict):
                parent_meta = {k: v for k, v in node.items() if k != key_to_flatten}
                flat_props = {k: _flatten(v) for k, v in node[key_to_flatten].items()}
                if parent_overwrites:
                    # Parent metadata takes precedence
                    merged = {**flat_props, **parent_meta}
                else:
                    # Properties take precedence
                    merged = {**parent_meta, **flat_props}
                return merged
            else:
                return {k: _flatten(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [_flatten(item) for item in node]
        else:
            return node
    return _flatten(schema)

def _remove_and_promote(schema: dict, key_to_promote: str) -> dict:
    # Preserve original order by iterating through items in order
    new_schema = {}
    for key, value in schema.items():
        if key == key_to_promote and isinstance(value, dict):
            # Insert the promoted items at the current position
            for inner_key, inner_val in value.items():
                new_schema[inner_key] = inner_val
        elif key != key_to_promote:
            # Keep other items in their original order
            new_schema[key] = value
    return new_schema

def _convert_enums_to_options(schema: dict) -> dict:
    def format_name(v: str) -> str:
        return v.strip().title()
    def _convert(node: dict) -> dict:
        if isinstance(node, dict):
            node = dict(node)
            if "enum" in node:
                node["options"] = [
                    {"name": format_name(v), "value": v}
                    for v in node["enum"]
                ]
                del node["enum"]
            return {k: _convert(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_convert(item) for item in node]
        return node
    return _convert(schema)

def _move_to_parameters(schema: dict, keys_to_move: list) -> dict:
    def _move(node: dict) -> dict:
        if isinstance(node, dict):
            node = dict(node)
            for key_to_move in keys_to_move:
                if key_to_move in node:
                    value = node.pop(key_to_move)
                    if "parameters" not in node:
                        node["parameters"] = {}
                    node["parameters"][key_to_move] = value
            return {
                k: _move(v) if k != "parameters" else v
                for k, v in node.items()
            }
        if isinstance(node, list):
            return [_move(item) for item in node]
        return node
    return _move(schema)

def _apply_pipeline(payload: dict, transforms: list) -> dict:
    for transform in transforms:
        payload = transform(payload)
    return payload

def _rename_keys(schema: dict, key_mapping: dict) -> dict:
    def _rename(node: dict) -> dict:
        if isinstance(node, dict):
            new_node = {}
            for k, v in node.items():
                new_key = key_mapping.get(k, k)
                new_node[new_key] = _rename(v)
            return new_node
        if isinstance(node, list):
            return [_rename(item) for item in node]
        return node

    return _rename(schema)

def _resolve_one_of(schema: dict) -> dict:
    """
    Resolves `oneOf` fields with discriminator by flattening the referenced sub-properties
    into the parent schema's properties, excluding the discriminator key (e.g., 'method').
    The resolved fields are added immediately after the original oneOf field.
    """
    import copy
    from collections import OrderedDict

    new_schema = copy.deepcopy(schema)
    definitions = new_schema.get("definitions", {})

    for def_name, def_schema in definitions.items():
        if not isinstance(def_schema, dict):
            continue

        props = def_schema.get("properties", {})
        if not isinstance(props, dict):
            continue

        # Use ordered dict to control field order
        new_props = OrderedDict()

        for prop_name, prop_schema in props.items():
            new_props[prop_name] = prop_schema

            # If this property contains a oneOf with discriminator
            if "oneOf" in prop_schema and "discriminator" in prop_schema:
                for oneof_entry in prop_schema["oneOf"]:
                    if "$ref" not in oneof_entry:
                        continue

                    ref_path = oneof_entry["$ref"]
                    parts = ref_path.split("/")
                    if len(parts) != 3 or parts[0] != "#" or parts[1] != "definitions":
                        continue

                    ref_def_name = parts[2]
                    ref_def = definitions.get(ref_def_name, {})
                    sub_props = ref_def.get("properties", {})

                    for sub_prop_name in sub_props:
                        if sub_prop_name == "method":
                            continue
                        new_props[sub_prop_name] = {
                            "$ref": f"#/definitions/{ref_def_name}/properties/{sub_prop_name}"
                        }

                # Remove the oneOf but preserve the rest
                cleaned_prop = {
                    key: val
                    for key, val in prop_schema.items()
                    if key != "oneOf"
                }
                new_props[prop_name] = cleaned_prop

        # Replace with reordered properties
        def_schema["properties"] = new_props

    return new_schema

def _cleanup_outer_non_objects(schema: dict) -> dict:
    """
    Removes all non-dictionary values from the outermost layer of the schema.
    This function should be used as the final step in the pipeline to clean up
    any remaining non-object nodes at the top level.
    """
    if not isinstance(schema, dict):
        return schema
    
    cleaned_schema = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            cleaned_schema[key] = value
        # Skip non-dictionary values (strings, numbers, lists, etc.)
    
    return cleaned_schema

def _remove_key_from_outer_layer(schema: dict, key_to_remove: str) -> dict:
    """
    Removes a specific key from the outermost layer of the schema.
    This function can be reused to remove different keys from the top level.
    """
    if not isinstance(schema, dict):
        return schema
    
    cleaned_schema = {}
    for key, value in schema.items():
        if key != key_to_remove:
            cleaned_schema[key] = value
        # Skip the specified key
    
    return cleaned_schema

def _cleanup_second_layer_keys(schema: dict, allowed_keys: list) -> dict:
    """
    For each top-level key in the schema, if its value is a dict, keep only the allowed_keys in that dict.
    Non-dict values are left unchanged.
    """
    if not isinstance(schema, dict):
        return schema
    cleaned_schema = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            cleaned_schema[key] = {k: v for k, v in value.items() if k in allowed_keys}
        else:
            cleaned_schema[key] = value
    return cleaned_schema

_key_mapping = {
    "maxItems": "max",
    "minItems": "min",
    "maximum": "max",
    "minimum": "min",
}

_allowed_keys = ["field_type", "parameters", "name", "rules", "description", "default", "when"]

_pipeline = [
    _convert_enums_to_options,
    _resolve_one_of,
    _resolve_refs,
    partial(_rename_keys, key_mapping=_key_mapping),
    partial(_move_to_parameters, keys_to_move=["options", "min", "max"]),
    partial(_flatten_properties, key_to_flatten="properties"),
    partial(_flatten_properties, key_to_flatten="items", parent_overwrites=False),
    partial(_remove_and_promote, key_to_promote="params"),
    partial(_remove_key_from_outer_layer, key_to_remove="output_dataset_type"),
    _cleanup_outer_non_objects,
    partial(_cleanup_second_layer_keys, allowed_keys=_allowed_keys),
]

# # Example usage:
# import json

# with open("model_schema.json") as f:
#     payload_old = json.load(f)

# with open("payload_new_generated.json", "w") as f:
#     json.dump(translate_payload(payload_old), f, indent=4)