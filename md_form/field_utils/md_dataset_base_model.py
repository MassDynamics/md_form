from itertools import count

from pydantic import BaseModel


class MdDatasetBaseModel(BaseModel):
    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        json_schema = handler(schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        counter = count()

        def number(field_schema):
            field_schema["md-field-order"] = next(counter)

        for field_name in cls.model_fields:
            field_schema = json_schema.get("properties", {}).get(field_name)
            if field_schema is None:
                continue
            number(field_schema)

            if "oneOf" not in field_schema:
                continue
            discriminator = field_schema.get("discriminator", {}).get("propertyName")
            for variant in field_schema["oneOf"]:
                if not isinstance(variant, dict) or "$ref" not in variant:
                    continue
                variant_schema = handler.resolve_ref_schema(variant)
                for sub_name, sub_schema in variant_schema.get("properties", {}).items():
                    if sub_name == discriminator:
                        continue
                    number(sub_schema)

        return json_schema
