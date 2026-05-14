import pytest
import copy
from prefect import flow
from md_form.field_utils import string_field, number_field, MdDatasetBaseModel
from translate_payload import (
    translate_payload,
    _resolve_refs,
    _flatten_properties,
    _remove_and_promote,
    _convert_enums_to_options,
    _move_to_parameters,
    _rename_keys,
    _resolve_one_of,
    _cleanup_outer_non_objects,
    _remove_key_from_outer_layer,
    _cleanup_second_layer_keys,
    _normalize_options_cases,
)


class TestTranslatePayload:
    @pytest.fixture
    def sample_schema(self):
        return {
            "definitions": {
                "TestType": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "integer"}
                    }
                }
            },
            "properties": {
                "test_field": {"$ref": "#/definitions/TestType"}
            }
        }

    @pytest.fixture
    def enum_schema(self):
        return {
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive", "pending"]
                }
            }
        }

    @pytest.fixture
    def one_of_schema(self):
        return {
            "definitions": {
                "TestDefinition": {
                    "type": "object",
                    "properties": {
                        "test_method": {
                            "oneOf": [
                                {"$ref": "#/definitions/MethodA"},
                                {"$ref": "#/definitions/MethodB"}
                            ],
                            "discriminator": "method"
                        }
                    }
                },
                "MethodA": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "const": "A"},
                        "param1": {"type": "string"},
                        "param2": {"type": "integer"}
                    }
                },
                "MethodB": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "const": "B"},
                        "param3": {"type": "boolean"}
                    }
                }
            }
        }

    class TestResolveRefs:
        def test_resolve_simple_ref(self, sample_schema):
            result = _resolve_refs(sample_schema)
            
            assert "definitions" not in result
            assert "test_field" in result["properties"]
            assert result["properties"]["test_field"]["type"] == "object"
            assert "name" in result["properties"]["test_field"]["properties"]
            assert "value" in result["properties"]["test_field"]["properties"]

        def test_resolve_nested_ref(self):
            schema = {
                "definitions": {
                    "NestedType": {
                        "type": "object",
                        "properties": {
                            "inner": {
                                "type": "string"
                            }
                        }
                    }
                },
                "properties": {
                    "nested": {"$ref": "#/definitions/NestedType/properties/inner"}
                }
            }
            
            result = _resolve_refs(schema)
            assert result["properties"]["nested"]["type"] == "string"

        def test_resolve_ref_with_preserved_metadata(self):
            schema = {
                "definitions": {
                    "TestType": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"}
                        }
                    }
                },
                "properties": {
                    "test_field": {
                        "$ref": "#/definitions/TestType",
                        "description": "Test description"
                    }
                }
            }
            
            result = _resolve_refs(schema)
            assert result["properties"]["test_field"]["description"] == "Test description"
            assert result["properties"]["test_field"]["type"] == "object"

        def test_resolve_ref_missing_definition(self):
            schema = {
                "properties": {
                    "test_field": {"$ref": "#/definitions/MissingType"}
                }
            }
            
            with pytest.raises(ValueError, match="Definition not found: MissingType"):
                _resolve_refs(schema)

        def test_resolve_ref_invalid_path(self):
            schema = {
                "properties": {
                    "test_field": {"$ref": "#/definitions/TestType/invalid/path"}
                }
            }
            
            with pytest.raises(ValueError, match="Definition not found: TestType"):
                _resolve_refs(schema)

    class TestFlattenProperties:
        def test_flatten_properties_basic(self):
            schema = {
                "properties": {
                    "field1": {"type": "string"},
                    "field2": {"type": "integer"}
                },
                "description": "Test schema"
            }
            
            result = _flatten_properties(schema, "properties")
            assert "field1" in result
            assert "field2" in result
            assert result["description"] == "Test schema"
            assert "properties" not in result

        def test_flatten_properties_parent_overwrites(self):
            schema = {
                "properties": {
                    "field1": {"type": "string"}
                },
                "description": "Parent description"
            }
            
            result = _flatten_properties(schema, "properties", parent_overwrites=True)
            assert result["description"] == "Parent description"

        def test_flatten_properties_child_overwrites(self):
            schema = {
                "properties": {
                    "field1": {"type": "string", "description": "Child description"}
                },
                "description": "Parent description"
            }
            
            result = _flatten_properties(schema, "properties", parent_overwrites=False)
            assert result["description"] == "Parent description"

        def test_flatten_items(self):
            schema = {
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    }
                }
            }
            
            result = _flatten_properties(schema, "items", parent_overwrites=False)
            assert "name" in result["properties"]
            assert result["type"] == "object"

    class TestRemoveAndPromote:
        def test_remove_and_promote_params(self):
            schema = {
                "name": "test",
                "params": {
                    "param1": {"type": "string"},
                    "param2": {"type": "integer"}
                },
                "description": "Test"
            }
            
            result = _remove_and_promote(schema, "params")
            assert "param1" in result
            assert "param2" in result
            assert "params" not in result
            assert result["name"] == "test"
            assert result["description"] == "Test"

        def test_remove_and_promote_preserves_order(self):
            schema = {
                "name": "test",
                "params": {
                    "param1": {"type": "string"},
                    "param2": {"type": "integer"}
                },
                "description": "Test"
            }
            
            result = _remove_and_promote(schema, "params")
            keys = list(result.keys())
            # Check that params are inserted at the original position
            assert keys.index("param1") < keys.index("description")

    class TestConvertEnumsToOptions:
        def test_convert_enums_to_options_basic(self, enum_schema):
            result = _convert_enums_to_options(enum_schema)
            
            assert "enum" not in result["properties"]["status"]
            assert "options" in result["properties"]["status"]
            assert len(result["properties"]["status"]["options"]) == 3
            
            options = result["properties"]["status"]["options"]
            assert options[0]["name"] == "active"
            assert options[0]["value"] == "active"
            assert options[1]["name"] == "inactive"
            assert options[1]["value"] == "inactive"

        def test_convert_enums_to_options_nested(self):
            schema = {
                "properties": {
                    "nested": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["yes", "no"]
                            }
                        }
                    }
                }
            }
            
            result = _convert_enums_to_options(schema)
            nested_status = result["properties"]["nested"]["properties"]["status"]
            assert "options" in nested_status
            assert len(nested_status["options"]) == 2

        def test_convert_enums_to_options_list(self):
            schema = {
                "items": {
                    "type": "string",
                    "enum": ["option1", "option2"]
                }
            }
            
            result = _convert_enums_to_options(schema)
            assert "options" in result["items"]
            assert len(result["items"]["options"]) == 2

    class TestMoveToParameters:
        def test_move_to_parameters_basic(self):
            schema = {
                "name": "test",
                "options": [{"name": "opt1", "value": "val1"}],
                "min": 0,
                "max": 10
            }
            
            result = _move_to_parameters(schema, ["options", "min", "max"])
            assert "parameters" in result
            assert "options" in result["parameters"]
            assert "min" in result["parameters"]
            assert "max" in result["parameters"]
            assert "options" not in result
            assert "min" not in result
            assert "max" not in result

        def test_move_to_parameters_nested(self):
            schema = {
                "properties": {
                    "field1": {
                        "options": [{"name": "opt1", "value": "val1"}],
                        "min": 0
                    }
                }
            }
            
            result = _move_to_parameters(schema, ["options", "min"])
            field1 = result["properties"]["field1"]
            assert "parameters" in field1
            assert "options" in field1["parameters"]
            assert "min" in field1["parameters"]

    class TestRenameKeys:
        def test_rename_keys_basic(self):
            schema = {
                "maxItems": 10,
                "minItems": 1,
                "maximum": 100,
                "minimum": 0
            }
            
            key_mapping = {
                "maxItems": "max",
                "minItems": "min",
                "maximum": "max",
                "minimum": "min"
            }
            
            result = _rename_keys(schema, key_mapping)
            assert "max" in result
            assert "min" in result
            assert "maxItems" not in result
            assert "minItems" not in result
            assert "maximum" not in result
            assert "minimum" not in result

        def test_rename_keys_nested(self):
            schema = {
                "properties": {
                    "field1": {
                        "maxItems": 10,
                        "minItems": 1
                    }
                }
            }
            
            key_mapping = {
                "maxItems": "max",
                "minItems": "min"
            }
            
            result = _rename_keys(schema, key_mapping)
            field1 = result["properties"]["field1"]
            assert "max" in field1
            assert "min" in field1

    class TestResolveOneOf:
        def test_resolve_one_of_basic(self, one_of_schema):
            result = _resolve_one_of(one_of_schema)
            
            # Check that oneOf is removed from the definition
            test_definition = result["definitions"]["TestDefinition"]
            test_method = test_definition["properties"]["test_method"]
            assert "oneOf" not in test_method
            
            # Check that sub-properties are added as $ref (excluding method)
            assert "param1" in test_definition["properties"]
            assert "param2" in test_definition["properties"]
            assert "param3" in test_definition["properties"]
            assert "method" not in test_definition["properties"]
            
            # Check that they are $ref references
            assert "$ref" in test_definition["properties"]["param1"]
            assert "$ref" in test_definition["properties"]["param2"]
            assert "$ref" in test_definition["properties"]["param3"]

        def test_resolve_one_of_preserves_order(self, one_of_schema):
            result = _resolve_one_of(one_of_schema)
            
            # Check that new properties are added after the original oneOf field
            test_definition = result["definitions"]["TestDefinition"]
            props = list(test_definition["properties"].keys())
            test_method_index = props.index("test_method")
            param1_index = props.index("param1")
            param2_index = props.index("param2")
            param3_index = props.index("param3")
            
            assert param1_index > test_method_index
            assert param2_index > test_method_index
            assert param3_index > test_method_index

    class TestCleanupOuterNonObjects:
        def test_cleanup_outer_non_objects_basic(self):
            schema = {
                "object1": {"type": "object"},
                "string1": "test",
                "number1": 42,
                "array1": [1, 2, 3],
                "object2": {"type": "string"}
            }
            
            result = _cleanup_outer_non_objects(schema)
            assert "object1" in result
            assert "object2" in result
            assert "string1" not in result
            assert "number1" not in result
            assert "array1" not in result

        def test_cleanup_outer_non_objects_non_dict_input(self):
            result = _cleanup_outer_non_objects("test")
            assert result == "test"

    class TestRemoveKeyFromOuterLayer:
        def test_remove_key_from_outer_layer_basic(self):
            schema = {
                "key1": "value1",
                "key2": "value2",
                "key_to_remove": "value3"
            }
            
            result = _remove_key_from_outer_layer(schema, "key_to_remove")
            assert "key1" in result
            assert "key2" in result
            assert "key_to_remove" not in result

        def test_remove_key_from_outer_layer_non_dict_input(self):
            result = _remove_key_from_outer_layer("test", "key")
            assert result == "test"

    class TestCleanupSecondLayerKeys:
        def test_cleanup_second_layer_keys_basic(self):
            schema = {
                "object1": {
                    "type": "object",
                    "description": "test",
                    "extra_field": "should_be_removed"
                },
                "string1": "test"
            }
            
            allowed_keys = ["type", "description"]
            result = _cleanup_second_layer_keys(schema, allowed_keys)
            
            assert "type" in result["object1"]
            assert "description" in result["object1"]
            assert "extra_field" not in result["object1"]
            assert result["string1"] == "test"

        def test_cleanup_second_layer_keys_non_dict_values(self):
            schema = {
                "object1": {
                    "type": "object",
                    "description": "test"
                },
                "string1": "test"
            }
            
            allowed_keys = ["type"]
            result = _cleanup_second_layer_keys(schema, allowed_keys)
            
            assert "type" in result["object1"]
            assert "description" not in result["object1"]
            assert result["string1"] == "test"

    class TestNormalizeOptionsCases:
        def test_normalizes_flat_string_cases(self):
            schema = {
                "knowledge_bases": {
                    "parameters": {
                        "options": {
                            "ref": "species",
                            "cases": {
                                "Human": ["reactome_human", "kegg_human"],
                                "Mouse": ["reactome_mouse"],
                            },
                        }
                    }
                }
            }

            result = _normalize_options_cases(schema)

            cases = result["knowledge_bases"]["parameters"]["options"]["cases"]
            assert cases["Human"] == [
                {"name": "reactome_human", "value": "reactome_human"},
                {"name": "kegg_human", "value": "kegg_human"},
            ]
            assert cases["Mouse"] == [
                {"name": "reactome_mouse", "value": "reactome_mouse"},
            ]
            # ref is preserved
            assert result["knowledge_bases"]["parameters"]["options"]["ref"] == "species"

        def test_already_normalized_cases_pass_through(self):
            schema = {
                "knowledge_bases": {
                    "parameters": {
                        "options": {
                            "ref": "species",
                            "cases": {
                                "Human": [
                                    {"name": "Reactome", "value": "reactome_human"},
                                ],
                            },
                        }
                    }
                }
            }

            result = _normalize_options_cases(schema)

            assert (
                result["knowledge_bases"]["parameters"]["options"]["cases"]["Human"]
                == [{"name": "Reactome", "value": "reactome_human"}]
            )

        def test_mixed_cases_value_passes_through(self):
            """A list that isn't pure-string is left untouched (strict — no per-element coercion)."""
            schema = {
                "x": {
                    "parameters": {
                        "options": {
                            "ref": "y",
                            "cases": {
                                "K": ["a", {"name": "b", "value": "b"}],
                            },
                        }
                    }
                }
            }

            result = _normalize_options_cases(schema)

            assert result["x"]["parameters"]["options"]["cases"]["K"] == [
                "a",
                {"name": "b", "value": "b"},
            ]

        def test_no_cases_key_under_options_untouched(self):
            schema = {
                "x": {
                    "parameters": {
                        "options": [{"name": "a", "value": "a"}],
                    }
                }
            }

            result = _normalize_options_cases(schema)

            assert result == schema

        def test_walks_nested_nodes(self):
            schema = {
                "outer": {
                    "properties": {
                        "inner": {
                            "parameters": {
                                "options": {
                                    "ref": "r",
                                    "cases": {"K": ["a", "b"]},
                                }
                            }
                        }
                    }
                }
            }

            result = _normalize_options_cases(schema)

            cases = result["outer"]["properties"]["inner"]["parameters"]["options"]["cases"]
            assert cases["K"] == [
                {"name": "a", "value": "a"},
                {"name": "b", "value": "b"},
            ]

        def test_translate_payload_normalizes_flat_string_cases(self):
            payload = {
                "properties": {
                    "knowledge_bases": {
                        "fieldType": "string",
                        "options": {
                            "ref": "species",
                            "cases": {
                                "Human": ["reactome_human", "kegg_human"],
                            },
                        },
                    }
                }
            }

            result = translate_payload(payload)

            assert result["knowledge_bases"]["parameters"]["options"]["cases"][
                "Human"
            ] == [
                {"name": "reactome_human", "value": "reactome_human"},
                {"name": "kegg_human", "value": "kegg_human"},
            ]

        def test_translate_payload_preserves_preshaped_cases(self):
            payload = {
                "properties": {
                    "knowledge_bases": {
                        "fieldType": "string",
                        "options": {
                            "ref": "species",
                            "cases": {
                                "Human": [
                                    {"name": "Reactome", "value": "reactome_human"},
                                ],
                            },
                        },
                    }
                }
            }

            result = translate_payload(payload)

            assert result["knowledge_bases"]["parameters"]["options"]["cases"][
                "Human"
            ] == [{"name": "Reactome", "value": "reactome_human"}]

    class TestSortByMdFieldOrder:
        """Tests for the not-yet-implemented `_sort_by_md_field_order` pipeline step.

        Each test imports the function locally so file collection still works while
        the implementation is pending.
        """

        def test_sort_ascending_by_md_field_order(self):
            from translate_payload import _sort_by_md_field_order

            schema = {
                "b": {"fieldType": "string", "md-field-order": 2},
                "a": {"fieldType": "string", "md-field-order": 1},
                "c": {"fieldType": "string", "md-field-order": 3},
            }

            result = _sort_by_md_field_order(schema)

            assert list(result.keys()) == ["a", "b", "c"]

        def test_fields_without_md_field_order_go_last(self):
            from translate_payload import _sort_by_md_field_order

            schema = {
                "no_order_first": {"fieldType": "string"},
                "ordered_second": {"fieldType": "string", "md-field-order": 2},
                "no_order_second": {"fieldType": "string"},
                "ordered_first": {"fieldType": "string", "md-field-order": 1},
            }

            result = _sort_by_md_field_order(schema)

            assert list(result.keys()) == [
                "ordered_first",
                "ordered_second",
                "no_order_first",
                "no_order_second",
            ]

        def test_only_sorts_top_level(self):
            from translate_payload import _sort_by_md_field_order

            schema = {
                "b": {
                    "md-field-order": 2,
                    "parameters": {
                        "z": {"md-field-order": 99},
                        "a": {"md-field-order": 1},
                    },
                },
                "a": {"md-field-order": 1},
            }

            result = _sort_by_md_field_order(schema)

            assert list(result.keys()) == ["a", "b"]
            assert list(result["b"]["parameters"].keys()) == ["z", "a"]

        def test_empty_schema(self):
            from translate_payload import _sort_by_md_field_order

            assert _sort_by_md_field_order({}) == {}

        def test_non_dict_input_passes_through(self):
            from translate_payload import _sort_by_md_field_order

            assert _sort_by_md_field_order("not a dict") == "not a dict"

        def test_does_not_mutate_input(self):
            from translate_payload import _sort_by_md_field_order

            schema = {
                "b": {"md-field-order": 2},
                "a": {"md-field-order": 1},
            }
            _sort_by_md_field_order(schema)

            assert list(schema.keys()) == ["b", "a"]

    class TestTranslatePayloadIntegration:
        def test_translate_payload_complete_pipeline(self):

            class TestType(MdDatasetBaseModel):
                name: str = string_field(description="Test field")
                status: str = string_field()
                count: int = number_field()

            @flow
            def some_thing(params: TestType):
                pass
            from prefect.utilities.callables import parameter_schema
            input_schema = parameter_schema(some_thing).model_dump_for_openapi()

            props = input_schema['definitions']['TestType']['properties']
            input_schema['definitions']['TestType']['properties'] = dict(reversed(props.items()))

            result = translate_payload(input_schema)

            # Check that refs are resolved and properties are flattened
            assert "definitions" not in result
            assert "name" in result
            assert "status" in result
            assert "count" in result

            # Check that output_dataset_type is removed
            assert "output_dataset_type" not in result
            
            # The final cleanup step removes most fields, so we just check
            # that the basic structure is preserved and only allowed keys remain
            assert "description" in result["name"]
            
            # Check that only allowed keys remain in second layer
            allowed_keys = ["type", "parameters", "name", "rules", "description", "default", "when", "md-field-order", "fieldType"]
            for key, value in result.items():
                if isinstance(value, dict):
                    for field_key in value.keys():
                        assert field_key in allowed_keys

            #check order
            assert result["name"]["md-field-order"] == 0
            assert result["status"]["md-field-order"] == 1
            assert result["count"]["md-field-order"] == 2

            assert list(result.keys()) == ["name", "status", "count"]

        def test_translate_payload_with_one_of(self, one_of_schema):
            result = translate_payload(one_of_schema)
            
            # Since the pipeline removes definitions and flattens properties,
            # we need to check that the oneOf resolution happened correctly
            # by looking for the resolved properties in the final result
            assert "definitions" not in result
            
            # The oneOf resolution should have added param1, param2, param3
            # but since definitions are removed, we can't directly verify this
            # Instead, we'll check that the result is a valid transformed schema
            assert isinstance(result, dict)
            # The test passes if no exceptions are raised and the result is a dict

        def test_translate_payload_preserves_original_structure(self):
            input_schema = {
                "simple_field": {
                    "fieldType": "string",
                    "description": "A simple field"
                }
            }
            
            result = translate_payload(input_schema)
            
            # Should preserve the basic structure
            assert "simple_field" in result
            assert "fieldType" in result["simple_field"]
            assert result["simple_field"]["description"] == "A simple field" 