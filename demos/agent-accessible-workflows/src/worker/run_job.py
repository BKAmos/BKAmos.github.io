"""Run a PyDESeq2 differential expression job for the workflow demo."""
from __future__ import annotations

import json
import math
import shutil
import sys
import contextlib
import inspect
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference
from pydeseq2.ds import DeseqStats

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from worker.plots import ma_plot, pca_plot, top_genes_heatmap, volcano_plot
else:
    from .plots import ma_plot, pca_plot, top_genes_heatmap, volcano_plot

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"
SRC_DIR = ROOT / "src"


@dataclass(frozen=True)
class DeseqConfig:
    counts_path: Path = DATA_DIR / "counts.csv"
    metadata_path: Path = DATA_DIR / "metadata.csv"
    output_dir: Path = OUT_DIR
    condition_column: str = "condition"
    reference_level: str = "control"
    treatment_level: str = "treated"
    batch_column: str | None = "batch"
    min_count: int = 10
    n_cpus: int = 2
    job_id: str = "sample-job"


def _load_inputs(config: DeseqConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    counts = pd.read_csv(config.counts_path, index_col=0)
    metadata = pd.read_csv(config.metadata_path)

    if "sample_id" in metadata.columns:
        metadata = metadata.set_index("sample_id")
    elif metadata.index.name != "sample_id":
        metadata.index = metadata.index.astype(str)

    missing_meta = set(counts.columns) - set(metadata.index)
    missing_counts = set(metadata.index) - set(counts.columns)
    if missing_meta or missing_counts:
        raise ValueError(
            "Sample IDs must match between counts columns and metadata rows. "
            f"Missing metadata: {sorted(missing_meta)}; missing counts: {sorted(missing_counts)}"
        )

    metadata = metadata.loc[counts.columns].copy()
    if config.condition_column not in metadata.columns:
        raise ValueError(f"Metadata is missing condition column {config.condition_column!r}")

    for level in (config.reference_level, config.treatment_level):
        if level not in set(metadata[config.condition_column].astype(str)):
            raise ValueError(f"Condition level {level!r} not found in metadata")

    if config.batch_column and config.batch_column not in metadata.columns:
        config = DeseqConfig(**{**asdict(config), "batch_column": None})

    counts = counts.T.astype(int)
    keep = counts.sum(axis=0) >= config.min_count
    counts = counts.loc[:, keep]
    if counts.shape[1] < 2:
        raise ValueError("Low-count filtering removed too many genes")

    metadata[config.condition_column] = pd.Categorical(
        metadata[config.condition_column].astype(str),
        categories=[config.reference_level, config.treatment_level],
        ordered=True,
    )
    if config.batch_column:
        metadata[config.batch_column] = metadata[config.batch_column].astype("category")

    return counts, metadata


def _design(config: DeseqConfig) -> str:
    if config.batch_column:
        return f"~{config.batch_column}+{config.condition_column}"
    return f"~{config.condition_column}"


def _deseq_dataset_kwargs(
    config: DeseqConfig,
    counts: pd.DataFrame,
    metadata: pd.DataFrame,
    design: str,
    inference: DefaultInference,
) -> dict[str, Any]:
    params = inspect.signature(DeseqDataSet.__init__).parameters
    common = {
        "counts": counts,
        "metadata": metadata,
        "refit_cooks": True,
        "inference": inference,
    }
    if "design" in params:
        return {**common, "design": design}

    design_factors = [config.condition_column]
    if config.batch_column:
        design_factors.insert(0, config.batch_column)
    return {
        **common,
        "design_factors": design_factors,
        "ref_level": [config.condition_column, config.reference_level],
    }


def _safe_number(value: Any) -> Any:
    if isinstance(value, (float, np.floating)) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    return value


def _write_report(
    output_dir: Path,
    config: DeseqConfig,
    results: pd.DataFrame,
    top_genes: pd.DataFrame,
    counts: pd.DataFrame,
    metadata: pd.DataFrame,
) -> None:
    strings = json.loads((SRC_DIR / "strings.json").read_text(encoding="utf-8"))
    env = Environment(
        loader=FileSystemLoader(SRC_DIR),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html.j2")
    significant = int((results["padj"].fillna(1.0) < 0.05).sum())
    plot_context = {
        "condition_column": config.condition_column,
        "reference_level": config.reference_level,
        "treatment_level": config.treatment_level,
        "batch_column": config.batch_column,
        "min_count": config.min_count,
        "design": _design(config),
        "contrast": f"{config.treatment_level} vs {config.reference_level}",
    }
    rendered = template.render(
        title=strings["title"],
        summary_note=strings["summary_note"],
        metrics={
            "sample_count": counts.shape[0],
            "gene_count": counts.shape[1],
            "significant_count": significant,
            "contrast": f"{config.treatment_level} vs {config.reference_level}",
        },
        top_genes_table=top_genes.reset_index().rename(columns={"index": "gene_id"}).to_html(
            index=False,
            float_format=lambda value: f"{value:.4g}",
            classes="top-genes",
        ),
        config=config,
        plot_context=plot_context,
        top_genes=top_genes.reset_index().rename(columns={"index": "gene_id"}).to_dict("records"),
        condition_counts=metadata[config.condition_column].astype(str).value_counts().to_dict(),
    )
    (output_dir / "report.html").write_text(rendered, encoding="utf-8")


def run_deseq(config: DeseqConfig) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config.counts_path, output_dir / "original_counts.csv")
    shutil.copyfile(config.metadata_path, output_dir / "metadata.csv")

    counts, metadata = _load_inputs(config)
    design = _design(config)

    inference = DefaultInference(n_cpus=config.n_cpus)
    dds = DeseqDataSet(**_deseq_dataset_kwargs(config, counts, metadata, design, inference))
    with open(output_dir / "pydeseq2.log", "w", encoding="utf-8") as log, contextlib.redirect_stdout(log):
        dds.deseq2()

    stats = DeseqStats(
        dds,
        contrast=[config.condition_column, config.treatment_level, config.reference_level],
        inference=inference,
    )
    with open(output_dir / "pydeseq2.log", "a", encoding="utf-8") as log, contextlib.redirect_stdout(log):
        stats.summary()
    coeff_name = f"{config.condition_column}[T.{config.treatment_level}]"
    if coeff_name in dds.varm.get("LFC", pd.DataFrame()).columns:
        with open(output_dir / "pydeseq2.log", "a", encoding="utf-8") as log, contextlib.redirect_stdout(log):
            stats.lfc_shrink(coeff=coeff_name)

    results = stats.results_df.copy()
    results.index.name = "gene_id"
    results = results.sort_values(["padj", "pvalue"], na_position="last")
    top_genes = results.head(25)

    results.to_csv(output_dir / "results.csv")
    top_genes.to_csv(output_dir / "top_genes.csv")

    raw_counts = counts.T
    normed_counts = pd.DataFrame(dds.layers["normed_counts"], index=counts.index, columns=counts.columns)
    normed_counts.to_csv(output_dir / "normalized_counts.csv")

    volcano_plot(
        results,
        output_dir / "volcano.png",
        reference_level=config.reference_level,
        treatment_level=config.treatment_level,
    )
    ma_plot(
        results,
        output_dir / "ma.png",
        reference_level=config.reference_level,
        treatment_level=config.treatment_level,
    )
    metadata_for_plots = metadata.reset_index().rename(columns={"index": "sample_id"})
    pca_plot(
        raw_counts,
        metadata_for_plots,
        output_dir / "pca.png",
        condition_column=config.condition_column,
        reference_level=config.reference_level,
        treatment_level=config.treatment_level,
    )
    top_genes_heatmap(
        raw_counts,
        metadata_for_plots,
        results,
        output_dir / "top_genes_heatmap.png",
        condition_column=config.condition_column,
        batch_column=config.batch_column,
    )
    _write_report(output_dir, config, results, top_genes, counts, metadata)

    artifacts = [
        "original_counts.csv",
        "results.csv",
        "top_genes.csv",
        "normalized_counts.csv",
        "metadata.csv",
        "volcano.png",
        "ma.png",
        "pca.png",
        "top_genes_heatmap.png",
        "report.html",
        "pydeseq2.log",
    ]
    manifest = {
        "job_id": config.job_id,
        "status": "completed",
        "analysis": "PyDESeq2 differential expression",
        "design": design,
        "condition_column": config.condition_column,
        "reference_level": config.reference_level,
        "treatment_level": config.treatment_level,
        "batch_column": config.batch_column,
        "min_count": config.min_count,
        "sample_count": int(counts.shape[0]),
        "gene_count": int(counts.shape[1]),
        "significant_gene_count": int((results["padj"].fillna(1.0) < 0.05).sum()),
        "artifacts": artifacts,
        "top_genes": [
            {key: _safe_number(value) for key, value in row.items()}
            for row in top_genes.reset_index().head(10).to_dict("records")
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    manifest = run_deseq(DeseqConfig())
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
