"""Synthetic dataset generation for contamination investigation demo."""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd

PROFILES: dict[str, dict[str, float]] = {
    "clean": {"contam_lambda": 80.0, "marker_boost": 0.0, "control_bleed": 0.0008},
    "low_contam": {"contam_lambda": 2500.0, "marker_boost": 1.4, "control_bleed": 0.002},
    "high_contam": {"contam_lambda": 8500.0, "marker_boost": 2.2, "control_bleed": 0.0045},
    "edge_case": {"contam_lambda": 1400.0, "marker_boost": 0.8, "control_bleed": 0.0055},
}

CONTAM_TAXA = ["Pseudomonas_aeruginosa", "E_coli_K12", "Bacillus_subtilis", "SyntheticVectorX"]


def write_synthetic_dataset(
    *,
    output_dir: Path,
    sample_count: int,
    profile: str,
    seed: int = 42,
) -> dict[str, Path]:
    if sample_count < 6:
        raise ValueError("sample_count must be >= 6")
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile {profile!r}")

    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    cfg = PROFILES[profile]

    samples = [f"S{i:03d}" for i in range(1, sample_count + 1)]
    controls = set(samples[: max(2, sample_count // 5)])
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

    profile_manifest = {
        "profile": profile,
        "seed": seed,
        "sample_count": sample_count,
        "controls": sorted(controls),
        "heuristic_thresholds": {
            "non_host_ratio_warn": 0.01,
            "marker_hits_warn": 2,
            "control_bleed_warn": 300,
        },
    }

    paths = {
        "taxa_abundance": output_dir / "taxa_abundance.csv",
        "alignment_stats": output_dir / "alignment_stats.csv",
        "marker_hits": output_dir / "marker_hits.csv",
        "sample_metrics": output_dir / "sample_metrics.csv",
        "qc_log": output_dir / "qc.log",
        "profile_manifest": output_dir / "profile_manifest.json",
    }
    pd.DataFrame(taxa_rows).to_csv(paths["taxa_abundance"], index=False)
    pd.DataFrame(align_rows).to_csv(paths["alignment_stats"], index=False)
    pd.DataFrame(marker_rows).to_csv(paths["marker_hits"], index=False)
    pd.DataFrame(metrics_rows).to_csv(paths["sample_metrics"], index=False)
    paths["qc_log"].write_text("\n".join(qc_lines) + "\n", encoding="utf-8")
    paths["profile_manifest"].write_text(json.dumps(profile_manifest, indent=2), encoding="utf-8")
    return paths
