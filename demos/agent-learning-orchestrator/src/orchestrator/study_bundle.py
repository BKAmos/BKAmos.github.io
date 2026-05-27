"""Generate a shared cohort bundle for contamination QC and DESeq."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

CONTAM_PROFILES: dict[str, dict[str, float]] = {
    "clean": {"contam_lambda": 80.0, "marker_boost": 0.0, "control_bleed": 0.0008},
    "low_contam": {"contam_lambda": 2500.0, "marker_boost": 1.4, "control_bleed": 0.002},
    "high_contam": {"contam_lambda": 8500.0, "marker_boost": 2.2, "control_bleed": 0.0045},
    "edge_case": {"contam_lambda": 1400.0, "marker_boost": 0.8, "control_bleed": 0.0055},
}

DESEQ_PROFILES: dict[str, dict[str, int]] = {
    "small": {"genes": 1000, "samples": 12, "n_de": 120},
    "medium": {"genes": 5000, "samples": 24, "n_de": 400},
    "large": {"genes": 10000, "samples": 32, "n_de": 700},
}

CONTAM_TAXA = ["Pseudomonas_aeruginosa", "E_coli_K12", "Bacillus_subtilis", "SyntheticVectorX"]

REQUIRED_CONTAM_FILES = (
    "alignment_stats.csv",
    "marker_hits.csv",
    "taxa_abundance.csv",
    "sample_metrics.csv",
    "qc.log",
)
REQUIRED_EXPRESSION_FILES = ("counts.csv", "metadata.csv")


def sample_ids(sample_count: int) -> list[str]:
    return [f"S{i:03d}" for i in range(1, sample_count + 1)]


def _write_contam_tables(
    *,
    output_dir: Path,
    samples: list[str],
    profile: str,
    seed: int,
) -> None:
    if profile not in CONTAM_PROFILES:
        raise ValueError(f"Unknown contamination profile {profile!r}")

    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    cfg = CONTAM_PROFILES[profile]
    controls = set(samples[: max(2, len(samples) // 5)])

    taxa_rows: list[dict[str, object]] = []
    marker_rows: list[dict[str, object]] = []
    align_rows: list[dict[str, object]] = []
    qc_lines: list[str] = []
    metrics_rows: list[dict[str, object]] = []

    for sample in samples:
        total_reads = int(rng.normal(3_600_000, 250_000))
        host_ratio = float(np.clip(rng.normal(0.985, 0.006), 0.92, 0.999))
        non_host_reads = max(1, int(total_reads * (1.0 - host_ratio)))
        contam_reads = int(max(0.0, rng.poisson(cfg["contam_lambda"])))
        if sample in controls:
            contam_reads = int(contam_reads * cfg["control_bleed"])
        contam_reads = min(contam_reads, int(non_host_reads * 0.95))
        marker_hits = int(rng.poisson(max(0.2, cfg["marker_boost"] * (contam_reads / 1100.0))))

        align_rows.append(
            {
                "sample_id": sample,
                "total_reads": total_reads,
                "host_mapped_reads": int(total_reads * host_ratio),
                "non_host_reads": non_host_reads,
                "mapping_rate": round(host_ratio, 5),
                "is_negative_control": sample in controls,
            }
        )
        metrics_rows.append(
            {
                "sample_id": sample,
                "profile": profile,
                "contaminant_reads": contam_reads,
                "marker_hits": marker_hits,
                "is_negative_control": sample in controls,
            }
        )
        marker_rows.append(
            {
                "sample_id": sample,
                "marker_name": "VectorResistanceCassette",
                "hit_count": marker_hits,
                "expected_in_host": False,
            }
        )

        host_count = max(1, non_host_reads - contam_reads)
        taxa_rows.append(
            {"sample_id": sample, "taxon": "HostReferenceResidual", "read_count": host_count, "domain": "host"}
        )
        for taxon in CONTAM_TAXA:
            frac = rng.uniform(0.08, 0.45)
            taxa_rows.append(
                {
                    "sample_id": sample,
                    "taxon": taxon,
                    "read_count": int(contam_reads * frac / len(CONTAM_TAXA) * 10),
                    "domain": "non_host",
                }
            )

        qc_status = "warn" if contam_reads > 2200 or marker_hits > 2 else "ok"
        qc_lines.append(
            f"{sample} profile={profile} mapped={host_ratio:.4f} contam_reads={contam_reads} "
            f"marker_hits={marker_hits} qc={qc_status}"
        )

    pd.DataFrame(taxa_rows).to_csv(output_dir / "taxa_abundance.csv", index=False)
    pd.DataFrame(align_rows).to_csv(output_dir / "alignment_stats.csv", index=False)
    pd.DataFrame(marker_rows).to_csv(output_dir / "marker_hits.csv", index=False)
    pd.DataFrame(metrics_rows).to_csv(output_dir / "sample_metrics.csv", index=False)
    (output_dir / "qc.log").write_text("\n".join(qc_lines) + "\n", encoding="utf-8")
    (output_dir / "profile_manifest.json").write_text(
        json.dumps(
            {
                "profile": profile,
                "seed": seed,
                "sample_count": len(samples),
                "controls": sorted(controls),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_expression_tables(
    *,
    output_dir: Path,
    samples: list[str],
    genes: int,
    n_de: int,
    seed: int,
) -> None:
    if genes < 50:
        raise ValueError("Need at least 50 genes for a meaningful fit.")
    if len(samples) < 4 or len(samples) % 2 != 0:
        raise ValueError("samples must be an even number >= 4 (balanced control/treated).")

    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    n_de_genes = min(n_de, genes)

    half = len(samples) // 2
    conditions = np.array(["control"] * half + ["treated"] * half)
    batches = np.array([f"batch_{(i % 2) + 1}" for i in range(len(samples))])

    gene_width = max(4, len(str(genes)))
    gene_ids = [f"gene_{i:0{gene_width}d}" for i in range(1, genes + 1)]
    base_means = rng.lognormal(mean=4.2, sigma=1.0, size=genes)
    dispersions = rng.gamma(shape=2.0, scale=0.22, size=genes) + 0.05

    log2_fc = np.zeros(genes)
    de_idx = rng.choice(genes, size=n_de_genes, replace=False)
    log2_fc[de_idx] = rng.choice([-1, 1], size=n_de_genes) * rng.uniform(1.2, 2.2, size=n_de_genes)

    sample_size_factors = rng.lognormal(mean=0.0, sigma=0.18, size=len(samples))
    counts = np.zeros((genes, len(samples)), dtype=int)

    for sample_idx, condition in enumerate(conditions):
        fold_change = np.where(condition == "treated", np.power(2.0, log2_fc), 1.0)
        mu = base_means * fold_change * sample_size_factors[sample_idx]
        shape = 1.0 / dispersions
        scale = mu * dispersions
        rates = rng.gamma(shape=shape, scale=scale)
        counts[:, sample_idx] = rng.poisson(rates)

    counts_df = pd.DataFrame(counts, index=gene_ids, columns=samples)
    metadata_df = pd.DataFrame(
        {
            "sample_id": samples,
            "condition": conditions,
            "batch": batches,
        }
    )
    truth_df = pd.DataFrame(
        {
            "gene_id": gene_ids,
            "true_log2_fold_change": log2_fc,
            "is_differential": np.isin(np.arange(genes), de_idx),
        }
    )

    counts_df.to_csv(output_dir / "counts.csv")
    metadata_df.to_csv(output_dir / "metadata.csv", index=False)
    truth_df.to_csv(output_dir / "truth.csv", index=False)


def write_study_bundle(
    study_dir: Path,
    *,
    study_id: str,
    contam_profile: str,
    deseq_profile: str,
    cohort_seed: int,
    sample_count: int | None = None,
    expression_seed: int | None = None,
) -> dict[str, Any]:
    if deseq_profile not in DESEQ_PROFILES:
        raise ValueError(f"Unknown DESeq profile {deseq_profile!r}")

    profile = DESEQ_PROFILES[deseq_profile]
    resolved_sample_count = sample_count or profile["samples"]
    if resolved_sample_count != profile["samples"]:
        raise ValueError(
            f"sample_count {resolved_sample_count} must match deseq profile {deseq_profile!r} "
            f"({profile['samples']} samples) for shared cohort demo."
        )

    samples = sample_ids(resolved_sample_count)
    study_dir.mkdir(parents=True, exist_ok=True)

    _write_contam_tables(output_dir=study_dir, samples=samples, profile=contam_profile, seed=cohort_seed)
    _write_expression_tables(
        output_dir=study_dir,
        samples=samples,
        genes=profile["genes"],
        n_de=profile["n_de"],
        seed=expression_seed if expression_seed is not None else cohort_seed + 42,
    )

    manifest = {
        "study_id": study_id,
        "cohort_seed": cohort_seed,
        "expression_seed": expression_seed if expression_seed is not None else cohort_seed + 42,
        "requested_contam_profile": contam_profile,
        "effective_contam_profile": contam_profile,
        "contam_profile": contam_profile,
        "deseq_profile": deseq_profile,
        "sample_count": resolved_sample_count,
        "sample_ids": samples,
        "genes": profile["genes"],
        "n_de": profile["n_de"],
        "inputs_dir": str(study_dir.resolve()),
        "files": {
            "counts": "counts.csv",
            "metadata": "metadata.csv",
            "truth": "truth.csv",
            "alignment_stats": "alignment_stats.csv",
            "marker_hits": "marker_hits.csv",
            "taxa_abundance": "taxa_abundance.csv",
            "sample_metrics": "sample_metrics.csv",
            "qc_log": "qc.log",
        },
    }
    (study_dir / "study_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def refresh_contam_profile(study_dir: Path, *, profile: str, cohort_seed: int) -> None:
    manifest_path = study_dir / "study_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing study manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = manifest["sample_ids"]
    _write_contam_tables(output_dir=study_dir, samples=samples, profile=profile, seed=cohort_seed)
    manifest["effective_contam_profile"] = profile
    manifest["contam_profile"] = profile
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def finalize_study_manifest(study_dir: Path, *, effective_contam_profile: str) -> dict[str, Any]:
    manifest_path = study_dir / "study_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["effective_contam_profile"] = effective_contam_profile
    manifest["contam_profile"] = effective_contam_profile
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def validate_study_inputs(inputs_dir: Path) -> None:
    for name in REQUIRED_CONTAM_FILES:
        if not (inputs_dir / name).exists():
            raise FileNotFoundError(f"Missing contamination input {name} in {inputs_dir}")
    for name in REQUIRED_EXPRESSION_FILES:
        if not (inputs_dir / name).exists():
            raise FileNotFoundError(f"Missing expression input {name} in {inputs_dir}")
