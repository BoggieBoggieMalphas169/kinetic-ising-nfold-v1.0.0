"""Versioned data contracts for the Ising analysis layer.

Prompt 8A.19 deliberately keeps two record levels separate:

* RUN_LEVEL / RUN_SUMMARY: one algorithm at a time, derived from raw simulator output.
* COMPARISON_SUMMARY: a paired Standard-vs-n-fold experiment, typically produced by
  the Prompt 6 validation/scalability/temperature harnesses.

Keeping these levels explicit prevents accidental averaging of already-aggregated values
and prevents a paired comparison row from being mistaken for an independent run.
"""

from __future__ import annotations

SCHEMA_VERSION = "8A19.1"
CONTEXT_SCHEMA_VERSION = "8A19-context-v1"

RUN_LEVEL = "run"
RUN_SUMMARY = "run_summary"
COMPARISON_SUMMARY = "comparison_summary"

PROMPT6_STUDIES = ("validation", "scalability_L", "temperature_sweep")

COMPARISON_COLUMNS = [
    "schema_version",
    "record_level",
    "source_schema",
    "study",
    "source_file",
    "source_row",
    "dynamics",
    "L",
    "N",
    "T",
    "invT",
    "J",
    "H",
    "runs",
    "n_standard",
    "n_nfold",
    "mean_tau_standard_mcss",
    "median_tau_standard_mcss",
    "sd_tau_standard_mcss",
    "mean_tau_nfold_mcss",
    "median_tau_nfold_mcss",
    "sd_tau_nfold_mcss",
    "mean_tau_standard_ci95_lo",
    "mean_tau_standard_ci95_hi",
    "mean_tau_nfold_ci95_lo",
    "mean_tau_nfold_ci95_hi",
    "lifetime_ratio_nfold_standard",
    "ratio_ci95_lo",
    "ratio_ci95_hi",
    "equivalence_margin",
    "equivalence_pass",
    "equivalence_status",
    "ratio_ci_contains_one",
    "ks_statistic",
    "ks_pvalue",
    "ks_holm_reject_fwer_0p05",
    "cpu_standard_s_per_escape",
    "cpu_nfold_s_per_escape",
    "speedup_standard_over_nfold",
    "mean_standard_attempts_per_escape",
    "mean_nfold_equiv_attempts_per_escape",
    "mean_nfold_events_per_escape",
    "nfold_equiv_attempts_per_event",
    "standard_acceptance_fraction",
    "standard_cpu_ns_per_attempt",
    "nfold_cpu_ns_per_event",
    "contract_status",
    "context_fields_applied",
]

# Fields required to interpret a physical comparison unambiguously. Some historical
# validation files did not store L/T/J; these can be supplied by an explicit sidecar
# rather than silently hard-coded by the loader.
PHYSICAL_CONTEXT_FIELDS = ("L", "T", "J", "H", "dynamics")
