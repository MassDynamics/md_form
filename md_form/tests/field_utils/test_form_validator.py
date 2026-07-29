import json
import os

import pytest

from field_utils.form_validator import (
    FormValidationError,
    is_valid_form,
    validate_form,
)

TUTORIAL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "tutorial",
)


def _errors(result):
    return {(e.field, e.message) for e in result.errors}


class TestRequired:
    definition = {
        "properties": {
            "name": {"fieldType": "String", "rules": [{"name": "is_required"}]},
            "notes": {"fieldType": "String"},
        }
    }

    def test_valid_when_required_present(self):
        assert validate_form(self.definition, {"name": "x"}).is_valid

    def test_invalid_when_required_missing(self):
        result = validate_form(self.definition, {})
        assert not result.is_valid
        assert ("name", "is required") in _errors(result)

    def test_invalid_when_required_none(self):
        result = validate_form(self.definition, {"name": None})
        assert not result.is_valid

    def test_optional_field_absent_is_fine(self):
        assert validate_form(self.definition, {"name": "x"}).is_valid


class TestConditionalRequired:
    definition = {
        "properties": {
            "mode": {
                "fieldType": "String",
                "parameters": {"options": [{"name": "skip", "value": "skip"},
                                           {"name": "batch", "value": "batch"}]},
            },
            "batch_variables": {
                "fieldType": "PairwiseControlVariables",
                "rules": [{"name": "is_required"}],
                "when": {"property": "mode", "equals": "batch"},
            },
        }
    }

    def test_not_required_when_condition_unmet(self):
        assert validate_form(self.definition, {"mode": "skip"}).is_valid

    def test_required_when_condition_met(self):
        result = validate_form(self.definition, {"mode": "batch"})
        assert ("batch_variables", "is required") in _errors(result)

    def test_provided_when_condition_met(self):
        assert validate_form(
            self.definition, {"mode": "batch", "batch_variables": ["v1"]}
        ).is_valid

    def test_inactive_field_is_skipped(self):
        # batch_variables carries a disallowed option, but its `when` is unmet
        # so it is inactive and every check on it is skipped.
        definition = {
            "properties": {
                "mode": {"fieldType": "String"},
                "batch_variables": {
                    "fieldType": "String",
                    "parameters": {"options": [{"name": "a", "value": "a"}]},
                    "when": {"property": "mode", "equals": "batch"},
                },
            }
        }
        assert validate_form(definition, {"mode": "skip", "batch_variables": "nope"}).is_valid
        assert not validate_form(definition, {"mode": "batch", "batch_variables": "nope"}).is_valid


class TestBounds:
    definition = {
        "properties": {
            "p": {"fieldType": "Number", "parameters": {"min": 0.0, "max": 1.0}},
        }
    }

    def test_within(self):
        assert validate_form(self.definition, {"p": 0.5}).is_valid

    def test_below(self):
        result = validate_form(self.definition, {"p": -1})
        assert ("p", "must be >= 0.0") in _errors(result)

    def test_above(self):
        result = validate_form(self.definition, {"p": 2})
        assert ("p", "must be <= 1.0") in _errors(result)


class TestOptions:
    definition = {
        "properties": {
            "entity_type": {
                "fieldType": "String",
                "parameters": {"options": [
                    {"name": "peptide", "value": "peptide"},
                    {"name": "protein", "value": "protein"},
                ]},
            },
            "method": {
                "fieldType": "String",
                "parameters": {"options": [
                    {"name": "none", "value": "none"},
                    {"name": "ptm", "value": "ptm",
                     "when": {"property": "entity_type", "equals": "peptide"}},
                ]},
            },
        }
    }

    def test_valid_option(self):
        assert validate_form(self.definition, {"entity_type": "protein"}).is_valid

    def test_invalid_option(self):
        result = validate_form(self.definition, {"entity_type": "mouse"})
        assert not result.is_valid

    def test_option_gated_by_when_available(self):
        assert validate_form(
            self.definition, {"entity_type": "peptide", "method": "ptm"}
        ).is_valid

    def test_option_gated_by_when_unavailable(self):
        result = validate_form(
            self.definition, {"entity_type": "protein", "method": "ptm"}
        )
        assert not result.is_valid


class TestMultipleOptions:
    definition = {
        "properties": {
            "tags": {
                "fieldType": "Multiple",
                "parameters": {"options": [
                    {"name": "a", "value": "a"},
                    {"name": "b", "value": "b"},
                ]},
            },
        }
    }

    def test_all_valid(self):
        assert validate_form(self.definition, {"tags": ["a", "b"]}).is_valid

    def test_one_invalid(self):
        result = validate_form(self.definition, {"tags": ["a", "z"]})
        assert not result.is_valid


class TestDynamicOptions:
    definition = {
        "properties": {
            "entity_type": {"fieldType": "String"},
            "db": {
                "fieldType": "String",
                "parameters": {"options": {
                    "ref": "entity_type",
                    "cases": {
                        "protein": [{"name": "reactome", "value": "reactome"}],
                        "gene": [{"name": "go", "value": "go"}],
                    },
                }},
            },
        }
    }

    def test_matches_case(self):
        assert validate_form(
            self.definition, {"entity_type": "protein", "db": "reactome"}
        ).is_valid

    def test_wrong_case(self):
        result = validate_form(
            self.definition, {"entity_type": "protein", "db": "go"}
        )
        assert not result.is_valid

    def test_unknown_case_is_skipped(self):
        # No case for "mouse" -> cannot validate membership, so it passes
        assert validate_form(
            self.definition, {"entity_type": "mouse", "db": "anything"}
        ).is_valid


class TestValueRules:
    def test_is_equal_to_value(self):
        d = {"properties": {"x": {"fieldType": "String",
                                  "rules": [{"name": "is_equal_to_value",
                                             "parameters": {"value": "yes"}}]}}}
        assert validate_form(d, {"x": "yes"}).is_valid
        assert not validate_form(d, {"x": "no"}).is_valid

    def test_is_not_equal_to_value(self):
        d = {"properties": {"x": {"fieldType": "String",
                                  "rules": [{"name": "is_not_equal_to_value",
                                             "parameters": {"value": "sample_name"}}]}}}
        assert validate_form(d, {"x": "condition"}).is_valid
        assert not validate_form(d, {"x": "sample_name"}).is_valid

    def test_is_equal_to_value_from_field(self):
        d = {"properties": {
            "a": {"fieldType": "String"},
            "b": {"fieldType": "String",
                  "rules": [{"name": "is_equal_to_value_from_field",
                             "parameters": {"field": "a"}}]},
        }}
        assert validate_form(d, {"a": "x", "b": "x"}).is_valid
        assert not validate_form(d, {"a": "x", "b": "y"}).is_valid

    def test_is_not_included_in_values_from_field(self):
        d = {"properties": {
            "control_variables": {"fieldType": "PairwiseControlVariables"},
            "condition_column": {"fieldType": "DatasetSampleMetadata",
                                 "rules": [{"name": "is_not_included_in_values_from_field",
                                            "parameters": {"field": "control_variables"}}]},
        }}
        assert validate_form(
            d, {"control_variables": ["batch"], "condition_column": "condition"}
        ).is_valid
        assert not validate_form(
            d, {"control_variables": ["condition"], "condition_column": "condition"}
        ).is_valid


class TestUnknownFields:
    definition = {"properties": {"name": {"fieldType": "String"}}}

    def test_allowed_by_default(self):
        assert validate_form(self.definition, {"name": "x", "extra": 1}).is_valid

    def test_rejected_when_strict(self):
        result = validate_form(
            self.definition, {"name": "x", "extra": 1}, allow_unknown=False
        )
        assert not result.is_valid
        assert result.errors[0].__str__() == "extra: unknown field not present in the form definition"
        assert ("extra", "unknown field not present in the form definition") in _errors(result)


class TestApiSurface:
    definition = {"properties": {"name": {"fieldType": "String",
                                           "rules": [{"name": "is_required"}]}}}

    def test_is_valid_form(self):
        assert is_valid_form(self.definition, {"name": "x"}) is True
        assert is_valid_form(self.definition, {}) is False

    def test_raise_on_error(self):
        with pytest.raises(FormValidationError):
            validate_form(self.definition, {}, raise_on_error=True)

    def test_result_is_truthy(self):
        assert validate_form(self.definition, {"name": "x"})
        assert not validate_form(self.definition, {})

    def test_bare_properties_map_accepted(self):
        bare = {"name": {"fieldType": "String", "rules": [{"name": "is_required"}]}}
        assert not validate_form(bare, {}).is_valid
        assert validate_form(bare, {"name": "x"}).is_valid

    def test_non_field_entries_ignored(self):
        d = {"properties": {"name": {"fieldType": "String"}, "$defs": {}}}
        assert validate_form(d, {"name": "x"}).is_valid


class TestTutorialForms:
    def _load(self, filename):
        with open(os.path.join(TUTORIAL_DIR, filename)) as f:
            return json.load(f)

    def test_entity_filtration_valid(self):
        definition = self._load("entity_filtration_form.json")
        data = {"entity_type": "peptide", "filtration_methods": "ptm_localization_probability"}
        assert validate_form(definition, data).is_valid

    def test_entity_filtration_missing_required(self):
        definition = self._load("entity_filtration_form.json")
        result = validate_form(definition, {"entity_type": "protein"})
        assert ("filtration_methods", "is required") in _errors(result)

    def test_entity_filtration_ptm_option_requires_peptide(self):
        definition = self._load("entity_filtration_form.json")
        # ptm_localization_probability is only available when entity_type == peptide
        result = validate_form(
            definition,
            {"entity_type": "protein", "filtration_methods": "ptm_localization_probability"},
        )
        assert not result.is_valid

    datasets = [{"id": "ds1", "name": "Dataset 1", "type": "INTENSITY", "state": "COMPLETED"}]

    def test_transform_intensities_conditional_fields(self):
        definition = self._load("transform_intensities_form.json")
        # input_datasets absent -> the `when: is_present input_datasets` fields are inactive,
        # but input_datasets itself is required.
        result = validate_form(definition, {}, datasets=self.datasets)
        assert ("input_datasets", "is required") in _errors(result)

    def test_transform_intensities_valid(self):
        definition = self._load("transform_intensities_form.json")
        data = {
            "input_datasets": ["ds1"],
            "normalisation_method": "quantile",
            "p_value_threshold": 0.05,
            "apply_log_transform": True,
            "intensity_range": 0.5,
        }
        assert validate_form(definition, data, datasets=self.datasets).is_valid


class TestDifferentialExpressionExample:
    """The payload shape from the feature request."""

    definition = {
        "properties": {
            "input_datasets": {
                "md-field-order": 0,
                "parameters": {
                    "type": "INTENSITY",
                    "width": "large",
                    "multiple": False
                },
                "name": "Select Intensity dataset",
                "group": "Details",
                "rules": [
                    {
                        "name": "is_required"
                    }
                ],
                "fieldType": "Datasets"
            },
            "entity_type": {
                "name": "Entity Type",
                "when": {
                    "property": "input_datasets",
                    "is_present": True
                },
                "group": "Details",
                "rules": [
                    {
                        "name": "is_required"
                    }
                ],
                "default": "protein",
                "fieldType": "EntityType",
                "parameters": {
                    "width": "large",
                    "datasetsSearch": {
                        "ref": "input_datasets"
                    },
                    "options": [
                        {
                            "name": "gene",
                            "value": "gene"
                        },
                        {
                            "name": "peptide",
                            "value": "peptide"
                        },
                        {
                            "name": "protein",
                            "value": "protein"
                        },
                        {
                            "name": "metabolite",
                            "value": "metabolite"
                        },
                        {
                            "name": "ptm",
                            "value": "ptm"
                        }
                    ]
                },
                "description": "Entity type of the intensity dataset",
                "md-field-order": 1
            },
            "condition_column": {
                "name": "Condition Column",
                "when": {
                    "property": "input_datasets",
                    "is_present": True
                },
                "group": "Details",
                "rules": [
                    {
                        "name": "is_not_equal_to_value",
                        "parameters": {
                            "value": "sample_name"
                        }
                    },
                    {
                        "name": "is_not_equal_to_value",
                        "parameters": {
                            "value": None
                        }
                    },
                    {
                        "name": "is_not_included_in_values_from_field",
                        "parameters": {
                            "field": "control_variables",
                            "values": "control_variables[].column"
                        }
                    },
                    {
                        "name": "is_required"
                    }
                ],
                "default": None,
                "fieldType": "DatasetSampleMetadata",
                "parameters": {
                    "width": "large",
                    "datasetsSearch": {
                        "ref": "input_datasets"
                    }
                },
                "md-field-order": 2
            },
            "condition_comparisons": {
                "name": "Condition Comparisons",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "experiment_design",
                            "is_present": True
                        },
                        {
                            "property": "condition_column",
                            "is_present": True
                        }
                    ]
                },
                "group": "Details",
                "rules": [
                    {
                        "name": "is_required"
                    }
                ],
                "default": None,
                "fieldType": "PairwiseConditionComparisons",
                "parameters": {
                    "conditionColumn": {
                        "ref": "condition_column"
                    },
                    "experimentDesign": {
                        "ref": "experiment_design"
                    }
                },
                "description": "The condition comparisons to be performed. The condition levels used to build the contrasts below are taken from the required \"Condition\" column in the samples metadata. The limma model will fit contrasts of the form: \"Condition 1\" vs \"Condition 2\"",
                "md-field-order": 3
            },
            "control_variables": {
                "name": "Control Variables",
                "when": {
                    "property": "input_datasets",
                    "is_present": True
                },
                "group": "Control Variables",
                "rules": [
                    {
                        "name": "is_not_equal_to_value",
                        "parameters": {
                            "value": "sample_name"
                        }
                    }
                ],
                "default": None,
                "fieldType": "PairwiseControlVariables",
                "parameters": {
                    "radioOptions": [
                        "categorical",
                        "numerical"
                    ],
                    "datasetsSearch": {
                        "ref": "input_datasets"
                    }
                },
                "description": "Optional control variables to include in the model. These can be either categorical (e.g., known batches, subject IDs) or numerical (e.g., continuous measurements like age, weight, etc.). Control variables help account for known sources of variation in your data, improving the accuracy of differential abundance analysis. Warning: samples with any missing values in the variables are removed from the analysis. Empty entries are considered as missing values.",
                "md-field-order": 4
            },
            "de_method_gene": {
                "name": "DE Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "gene",
                            "property": "entity_type"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "limma",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "limma",
                            "value": "limma"
                        },
                        {
                            "name": "edgeR",
                            "value": "edgeR"
                        },
                        {
                            "name": "DESeq2",
                            "value": "DESeq2"
                        }
                    ]
                },
                "description": "Differential expression method. limma: Best for pre-normalised data (CPM, TPM, FPKM) or log-transformed intensities. Works well with small sample sizes. edgeR: Designed for raw integer counts. Uses quasi-likelihood F-tests. Requires raw, unnormalised counts. DESeq2: Designed for raw integer counts. Uses Wald tests with shrinkage estimation. Requires raw unnormalised counts.<br><br><b>Note (limma + gene path):</b> limma-trend assumes library sizes vary by less than ~3-fold across samples. If your raw library sizes are more variable than this, limma-trend is not recommended for your data.<br><br>Reference: <a href=\"https://doi.org/10.1186/gb-2014-15-2-r29\">Law, Chen, Shi & Smyth 2014, Genome Biology</a>.",
                "md-field-order": 5
            },
            "de_method_peptide": {
                "name": "DE Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "peptide",
                            "property": "entity_type"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "limma",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "limma",
                            "value": "limma"
                        }
                    ]
                },
                "description": "Differential expression method. For peptide data the limma framework is used.",
                "md-field-order": 6
            },
            "de_method_protein": {
                "name": "DE Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "protein",
                            "property": "entity_type"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "limma",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "limma",
                            "value": "limma"
                        }
                    ]
                },
                "description": "Differential expression method. For protein data the limma framework is used.",
                "md-field-order": 7
            },
            "de_method_metabolite": {
                "name": "DE Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "metabolite",
                            "property": "entity_type"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "limma",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "limma",
                            "value": "limma"
                        }
                    ]
                },
                "description": "Differential expression method. For metabolite data the limma framework is used.",
                "md-field-order": 8
            },
            "de_method_ptm": {
                "name": "DE Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "ptm",
                            "property": "entity_type"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "limma",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "limma",
                            "value": "limma"
                        }
                    ]
                },
                "description": "Differential expression method. For PTM data the limma framework is used.",
                "md-field-order": 9
            },
            "limma_trend": {
                "name": "Limma Trend",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "operator": "or",
                            "conditions": [
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "peptide",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_peptide"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "protein",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_protein"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "metabolite",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_metabolite"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "ptm",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_ptm"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": True,
                "fieldType": "Boolean",
                "parameters": {
                    "label": "Limma Trend"
                },
                "description": "Argument passed to the limma function ebayes(). When TRUE, an intensity-dependent trend is allowed for the prior variances, known as the limma-trend method (Law et al, 2014; Phipson et al, 2016). If FALSE, a costant prior variance is assumed.",
                "md-field-order": 10
            },
            "robust_empirical_bayes": {
                "name": "Robust Empirical Bayes",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "operator": "or",
                            "conditions": [
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "gene",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_gene"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "peptide",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_peptide"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "protein",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_protein"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "metabolite",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_metabolite"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "ptm",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_ptm"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": True,
                "fieldType": "Boolean",
                "parameters": {
                    "label": "Robust Empirical Bayes"
                },
                "description": "Argument passed to the limma function ebayes(). When TRUE, the robust empirical Bayes procedure of Phipson et al (2016) is used. This method is adopted to protect the estimation procedure against hyper or hypo variable genes.",
                "md-field-order": 11
            },
            "fit_separate_models": {
                "name": "Fit Separate Models",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "operator": "or",
                            "conditions": [
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "peptide",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_peptide"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "protein",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_protein"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "metabolite",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_metabolite"
                                        }
                                    ]
                                },
                                {
                                    "operator": "and",
                                    "conditions": [
                                        {
                                            "equals": "ptm",
                                            "property": "entity_type"
                                        },
                                        {
                                            "equals": "limma",
                                            "property": "de_method_ptm"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": True,
                "fieldType": "Boolean",
                "parameters": {
                    "label": "Fit Separate Models"
                },
                "description": "When TRUE fits separate limma models for each pairwise comparisons instead of a single model. This approach filters proteins individually for each comparison, reducing the impact of conditions with a high number of missing or imputed values.",
                "md-field-order": 12
            },
            "edger_norm_method": {
                "name": "edgeR Normalisation Method",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "edgeR",
                            "property": "de_method_gene"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "TMM",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "TMM",
                            "value": "TMM"
                        },
                        {
                            "name": "RLE",
                            "value": "RLE"
                        },
                        {
                            "name": "upperquartile",
                            "value": "upperquartile"
                        },
                        {
                            "name": "none",
                            "value": "none"
                        }
                    ]
                },
                "description": "Library size normalisation method for edgeR. TMM (trimmed mean of M-values) is the default and recommended method. RLE (relative log expression) is an alternative. 'upperquartile' normalises to the 75th percentile. 'none' skips normalisation (use when data is already normalised).",
                "md-field-order": 13
            },
            "deseq2_lfc_shrinkage": {
                "name": "DESeq2 LFC Shrinkage",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "DESeq2",
                            "property": "de_method_gene"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": "none",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "none",
                            "value": "none"
                        },
                        {
                            "name": "apeglm",
                            "value": "apeglm"
                        },
                        {
                            "name": "ashr",
                            "value": "ashr"
                        },
                        {
                            "name": "normal",
                            "value": "normal"
                        }
                    ]
                },
                "description": "Log-fold-change shrinkage method for DESeq2. 'none' uses raw maximum-likelihood estimates (default). 'apeglm' (recommended) produces shrunken fold changes that are more reliable for ranking genes. 'ashr' uses adaptive shrinkage. 'normal' uses a normal prior.",
                "md-field-order": 14
            },
            "deseq2_alpha": {
                "name": "DESeq2 FDR Threshold (alpha)",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "DESeq2",
                            "property": "de_method_gene"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": 0.05,
                "fieldType": "NumberRange",
                "parameters": {
                    "width": "large",
                    "interval": 0.01,
                    "min": 0,
                    "max": 1
                },
                "description": "Significance threshold for DESeq2 independent filtering. <b>Set this equal to the FDR threshold you intend to apply downstream</b> (i.e., the AdjPValue cutoff at which you will declare significance). DESeq2's independent filtering optimises the gene rejection set under this alpha; mismatched values silently lose power. A user who keeps the default 0.05 but applies a different downstream FDR threshold (e.g., 0.10) will lose statistical power because the IF cutoff was tuned for the wrong target.<br><br>Reference: <a href=\"https://doi.org/10.1073/pnas.0914005107\">Bourgon, Gentleman & Huber 2010, PNAS</a>.",
                "md-field-order": 15
            },
            "apeglm_seed": {
                "name": "apeglm RNG Seed",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "equals": "DESeq2",
                            "property": "de_method_gene"
                        },
                        {
                            "equals": "apeglm",
                            "property": "deseq2_lfc_shrinkage"
                        }
                    ]
                },
                "group": "Advanced Model Parameters",
                "default": 1,
                "fieldType": "NumberRange",
                "parameters": {
                    "width": "large",
                    "min": 0,
                    "max": 2147483647
                },
                "description": "RNG seed for apeglm shrinkage reproducibility. apeglm's posterior optimisation uses random initialisation for some genes; fixing this seed ensures bit-identical results across runs. Default 1; change only if you want to assess sensitivity of borderline genes to the initialisation.",
                "md-field-order": 16
            },
            "filter_values_criteria": {
                "name": "Filter Values Criteria",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "property": "entity_type",
                            "not_equals": "gene"
                        }
                    ]
                },
                "group": "Filtering Parameters",
                "default": "percentage",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "percentage",
                            "value": "percentage"
                        },
                        {
                            "name": "count",
                            "value": "count"
                        }
                    ]
                },
                "description": "Options: 'percentage' or 'count' of valid values.",
                "md-field-order": 17
            },
            "filter_threshold_percentage": {
                "name": "Filter Threshold Percentage",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "equals": "percentage",
                            "property": "filter_values_criteria"
                        },
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "property": "entity_type",
                            "not_equals": "gene"
                        }
                    ]
                },
                "group": "Filtering Parameters",
                "rules": [
                    {
                        "name": "is_required"
                    }
                ],
                "default": 0.5,
                "fieldType": "NumberRange",
                "parameters": {
                    "width": "large",
                    "interval": 0.01,
                    "min": 0,
                    "max": 1
                },
                "description": "Percentage threshold for filtering. Must be between 0 and 1, inclusive. Only entities with a percentage of valid values larger or equal than the threshold are kept in the analysis. The filtering threshold is evaluated with respect to the 'Filter Valid Values Logic', e.g. by default entities with more than 50% valid values in 'at least one condition' are kept.",
                "md-field-order": 18
            },
            "filter_threshold_count": {
                "name": "Filter Threshold Count",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "equals": "count",
                            "property": "filter_values_criteria"
                        },
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "property": "entity_type",
                            "not_equals": "gene"
                        }
                    ]
                },
                "group": "Filtering Parameters",
                "rules": [
                    {
                        "name": "is_required"
                    }
                ],
                "default": 3,
                "fieldType": "Number",
                "parameters": {
                    "width": "xsmall",
                    "min": 1
                },
                "description": "Minimum count threshold for filtering. Must be greater than or equal to 1. Only entities with a number of valid values larger or equal than the threshold are kept in the analysis. The filtering threshold is evaluated with respect to the 'Filter Valid Values Logic', e.g. by default entities with at least 3 valid values in 'at least one condition' are kept.",
                "md-field-order": 19
            },
            "filter_valid_values_logic": {
                "name": "Filter Valid Values Logic",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "property": "entity_type",
                            "not_equals": "gene"
                        }
                    ]
                },
                "group": "Filtering Parameters",
                "default": "at least one condition",
                "fieldType": "String",
                "parameters": {
                    "width": "large",
                    "options": [
                        {
                            "name": "all conditions",
                            "value": "all conditions"
                        },
                        {
                            "name": "at least one condition",
                            "value": "at least one condition"
                        },
                        {
                            "name": "full experiment",
                            "value": "full experiment"
                        }
                    ]
                },
                "description": "Logic for filtering. Options: 'all conditions': the count/percentage of valid values must exceed the threshold in all conditions; 'at least one condition' (Default): the count/percentage of valid values must exceed the threshold in at least one condition; 'full experiment': the count/percentage of valid values must exceed the threshold across the whole experiment.",
                "md-field-order": 20
            },
            "experiment_design": {
                "name": "Sample Metadata",
                "when": {
                    "operator": "and",
                    "conditions": [
                        {
                            "property": "input_datasets",
                            "is_present": True
                        },
                        {
                            "property": "condition_column",
                            "is_present": True
                        }
                    ]
                },
                "group": "Sample Metadata used for Dataset",
                "rules": [
                    {
                        "name": "has_unique_column_values_in_table",
                        "parameters": {
                            "column": "sample_name"
                        }
                    },
                    {
                        "name": "has_multiple_column_values_from_field_in_table",
                        "parameters": {
                            "values": "condition_column"
                        }
                    },
                    {
                        "name": "has_multiple_column_values_from_field_in_table",
                        "parameters": {
                            "field": "control_variables",
                            "values": "control_variables[].column"
                        }
                    }
                ],
                "default": None,
                "fieldType": "SampleMetadataTable",
                "parameters": {
                    "columnNames": {
                        "ref": [
                            "condition_column",
                            "control_variables[].column"
                        ]
                    },
                    "datasetsSearch": {
                        "ref": "input_datasets"
                    }
                },
                "md-field-order": 21
            }
        } 
    }

    # A valid submission for the real definition above. Note the flat shape the
    # translated form expects: `input_datasets` gates the whole form, and the
    # filter criteria is a plain string alongside a separate threshold field
    # (not the nested dict of some hand-written payloads).
    payload = {
        "input_datasets": ["intensity_dataset_id"],
        "entity_type": "protein",
        "condition_column": "condition",
        "condition_comparisons": {"condition_comparison_pairs": [["Heart", "Brain_1ug"]]},
        "de_method_protein": "limma",
        "limma_trend": True,
        "robust_empirical_bayes": True,
        "fit_separate_models": True,
        "filter_values_criteria": "percentage",
        "filter_threshold_percentage": 0.5,
        "filter_valid_values_logic": "at least one condition",
        "experiment_design": {
            "sample_name": ["Heart_1", "Heart_2"],
            "condition": ["Heart", "Heart"],
        },
    }

    # The definition has an input_datasets field (fieldType "Datasets"), so a
    # datasets list must be supplied to validate it.
    datasets = [
        {
            "id": "intensity_dataset_id",
            "name": "Denis uPhos tissue - pg_matrix (condition)",
            "type": "INTENSITY",
            "state": "COMPLETED",
        }
    ]

    def test_example_payload_is_valid(self):
        assert validate_form(self.definition, self.payload, datasets=self.datasets).is_valid

    def test_missing_required_input_datasets(self):
        bad = dict(self.payload)
        del bad["input_datasets"]
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert ("input_datasets", "is required") in _errors(result)

    def test_datasets_required_when_omitted(self):
        # The form has a Datasets field but no datasets list is supplied.
        result = validate_form(self.definition, self.payload)
        assert ("input_datasets", "a datasets list must be provided to validate this field") in _errors(result)

    def test_selected_dataset_not_in_provided_list(self):
        bad = dict(self.payload)
        bad["input_datasets"] = ["some_other_id"]
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert ("input_datasets", "dataset 'some_other_id' is not in the provided datasets") in _errors(result)

    def test_selected_dataset_as_dicts(self):
        # A selection expressed as dataset dicts (with an id) is matched by id.
        ok = dict(self.payload)
        ok["input_datasets"] = [{"id": "intensity_dataset_id", "name": "whatever"}]
        assert validate_form(self.definition, ok, datasets=self.datasets).is_valid

    def test_dataset_wrong_type(self):
        # input_datasets declares parameters.type == "INTENSITY".
        datasets = [{"id": "intensity_dataset_id", "name": "x", "type": "PAIRWISE", "state": "COMPLETED"}]
        result = validate_form(self.definition, self.payload, datasets=datasets)
        assert (
            "input_datasets",
            "dataset 'intensity_dataset_id' must be of type 'INTENSITY', not 'PAIRWISE'",
        ) in _errors(result)

    def test_missing_required_options(self):
        bad = dict(self.payload)
        del bad['filter_values_criteria']
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert (
                   "filter_values_criteria",
                   "is required",
               ) in _errors(result)

    def test_missing_required_boolean(self):
        bad = dict(self.payload)
        del bad['limma_trend']
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert (
                   "limma_trend",
                   "is required",
               ) in _errors(result)

    def test_dataset_not_completed(self):
        datasets = [{"id": "intensity_dataset_id", "name": "x", "type": "INTENSITY", "state": "PROCESSING"}]
        result = validate_form(self.definition, self.payload, datasets=datasets)
        assert (
            "input_datasets",
            "dataset 'intensity_dataset_id' must be in state 'COMPLETED', not 'PROCESSING'",
        ) in _errors(result)

    def test_bad_de_method_option(self):
        bad = dict(self.payload)
        bad["de_method_protein"] = "not-a-method"
        assert not validate_form(self.definition, bad, datasets=self.datasets).is_valid

    def test_bad_filter_logic_option(self):
        bad = dict(self.payload)
        bad["filter_valid_values_logic"] = "sometimes"
        assert not validate_form(self.definition, bad, datasets=self.datasets).is_valid

    def test_missing_conditional_required(self):
        # filter_threshold_percentage is required only while
        # filter_values_criteria == "percentage" (and the form is active).
        bad = dict(self.payload)
        del bad["filter_threshold_percentage"]
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert ("filter_threshold_percentage", "is required") in _errors(result)

    def test_number_bound_enforced(self):
        # filter_threshold_percentage is a NumberRange with min 0 / max 1.
        bad = dict(self.payload)
        bad["filter_threshold_percentage"] = 5
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert ("filter_threshold_percentage", "must be <= 1") in _errors(result)

    def test_experiment_design_shape(self):
        # experiment_design must be a table (object of column -> list). A
        # list-of-lists is the wrong shape and is rejected via its table rule.
        bad = dict(self.payload)
        bad["experiment_design"] = [
            ["sample_name", "condition"],
            ["Heart_1", "Heart_2"],
            ["Heart", "Heart"],
        ]
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert not result.is_valid
        assert (
            "experiment_design",
            "must be a table (an object mapping column names to lists)",
        ) in _errors(result)

    def test_experiment_design_uneven_columns(self):
        bad = dict(self.payload)
        bad["experiment_design"] = {
            "sample_name": ["Heart_1", "Heart_2"],
            "condition": ["Heart"],
        }
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert ("experiment_design", "table columns must all have the same length") in _errors(result)

    def test_experiment_design_duplicate_sample_names(self):
        # experiment_design declares has_unique_column_values_in_table on the
        # sample_name column, so duplicate sample names are rejected.
        bad = dict(self.payload)
        bad["experiment_design"] = {
            "sample_name": ["Heart_1", "Heart_1"],
            "condition": ["Heart", "Heart"],
        }
        result = validate_form(self.definition, bad, datasets=self.datasets)
        assert not result.is_valid
        assert (
            "experiment_design",
            "column 'sample_name' must contain unique values",
        ) in _errors(result)





