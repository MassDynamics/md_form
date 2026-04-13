import pytest
from typing import Optional, List
from pydantic import BaseModel, ValidationError
from field_utils.conditional_validator import ConditionalRequiredMixin
from field_utils.field_helpers import control_variables_field, string_field, select_field
from field_utils.rules_builder import is_required
from field_utils.when import When


class FakeModel(ConditionalRequiredMixin, BaseModel):
    mode: str = select_field(default="skip", options=["skip", "batch_correction"])

    batch_variables: Optional[list] = control_variables_field(
        name="Batch Variables",
        rules=[is_required()],
        when=When.any_of(
            When.equals("mode", "batch_correction"),
        ),
    )


class TestConditionalRequiredMixin:

    def test_field_not_required_when_condition_not_met(self):
        model = FakeModel(mode="skip")
        assert model.batch_variables is None

    def test_field_required_when_condition_met_and_provided(self):
        model = FakeModel(mode="batch_correction", batch_variables=["var1"])
        assert model.batch_variables == ["var1"]

    def test_field_required_when_condition_met_and_missing(self):
        with pytest.raises(ValidationError, match="batch_variables"):
            FakeModel(mode="batch_correction")

    def test_field_required_when_condition_met_and_none(self):
        with pytest.raises(ValidationError, match="batch_variables"):
            FakeModel(mode="batch_correction", batch_variables=None)


class MultiConditionModel(ConditionalRequiredMixin, BaseModel):
    entity_type: Optional[str] = select_field(
        default=None,
        options=["peptide", "protein", "gene"],
    )
    norm_gene: Optional[str] = select_field(
        default="skip",
        options=["skip", "batch_correction"],
        when=When.equals("entity_type", "gene"),
    )
    norm_proteomics: Optional[str] = select_field(
        default="skip",
        options=["skip", "batch_correction"],
        when=When.any_of(
            When.equals("entity_type", "peptide"),
            When.equals("entity_type", "protein"),
        ),
    )
    batch_vars: Optional[list] = control_variables_field(
        name="Batch Variables",
        rules=[is_required()],
        when=When.any_of(
            When.equals("norm_gene", "batch_correction"),
            When.equals("norm_proteomics", "batch_correction"),
        ),
    )


class TestMultiConditionRequired:

    def test_no_batch_vars_needed_when_skip(self):
        model = MultiConditionModel(entity_type="gene", norm_gene="skip")
        assert model.batch_vars is None

    def test_batch_vars_required_via_gene(self):
        with pytest.raises(ValidationError, match="batch_vars"):
            MultiConditionModel(entity_type="gene", norm_gene="batch_correction")

    def test_batch_vars_required_via_proteomics(self):
        with pytest.raises(ValidationError, match="batch_vars"):
            MultiConditionModel(entity_type="protein", norm_proteomics="batch_correction")

    def test_batch_vars_provided_passes(self):
        model = MultiConditionModel(
            entity_type="gene",
            norm_gene="batch_correction",
            batch_vars=["batch1"],
        )
        assert model.batch_vars == ["batch1"]


class NoWhenModel(ConditionalRequiredMixin, BaseModel):
    name: str = string_field(name="Name", rules=[is_required()])


class TestUnconditionalRequired:

    def test_required_without_when_still_requires(self):
        with pytest.raises(ValidationError):
            NoWhenModel()

    def test_required_without_when_provided(self):
        model = NoWhenModel(name="test")
        assert model.name == "test"
