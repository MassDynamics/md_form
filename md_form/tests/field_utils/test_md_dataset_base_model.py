from field_utils.md_dataset_base_model import MdDatasetBaseModel
from md_form.field_utils import number_field, string_field


class TestMdDatasetBaseModel:
    def test_simple_model_with_two_ints(self):
        class SimpleModel(MdDatasetBaseModel):
            a: int = number_field()
            b: str = string_field()

        schema = SimpleModel.model_json_schema()

        assert schema["properties"]["a"]["md-field-order"] == 0
        assert schema["properties"]["b"]["md-field-order"] == 1


    def test_nested_model(self):
        class Inner(MdDatasetBaseModel):
            x: int
            y: int

        class Outer(MdDatasetBaseModel):
            inner: Inner
            z: int

        schema = Outer.model_json_schema()

        assert schema["properties"]["inner"]["md-field-order"] == 0
        assert schema["properties"]["z"]["md-field-order"] == 1

        inner_def = schema["$defs"]["Inner"]
        assert inner_def["properties"]["x"]["md-field-order"] == 0
        assert inner_def["properties"]["y"]["md-field-order"] == 1

