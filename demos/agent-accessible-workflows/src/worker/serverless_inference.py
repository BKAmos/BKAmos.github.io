"""Sequential PyDESeq2 inference for AWS Lambda (joblib loky unavailable)."""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from pydeseq2 import utils
from pydeseq2.default_inference import DefaultInference


class ServerlessInference(DefaultInference):
    """Run DefaultInference routines sequentially (no joblib parallel_backend)."""

    def __init__(self) -> None:
        super().__init__(n_cpus=1, backend="loky")

    def lin_reg_mu(
        self,
        counts: np.ndarray,
        size_factors: np.ndarray,
        design_matrix: np.ndarray,
        min_mu: float,
    ) -> np.ndarray:
        mu_hat_ = np.array(
            [
                utils.fit_lin_mu(
                    counts=counts[:, i],
                    size_factors=size_factors,
                    design_matrix=design_matrix,
                    min_mu=min_mu,
                )
                for i in range(counts.shape[1])
            ]
        )
        return mu_hat_.T

    def irls(
        self,
        counts: np.ndarray,
        size_factors: np.ndarray,
        design_matrix: np.ndarray,
        disp: np.ndarray,
        min_mu: float,
        beta_tol: float,
        min_beta: float = -30,
        max_beta: float = 30,
        optimizer: Literal["BFGS", "L-BFGS-B"] = "L-BFGS-B",
        maxiter: int = 250,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        res = [
            utils.irls_solver(
                counts=counts[:, i],
                size_factors=size_factors,
                design_matrix=design_matrix,
                disp=disp[i],
                min_mu=min_mu,
                beta_tol=beta_tol,
                min_beta=min_beta,
                max_beta=max_beta,
                optimizer=optimizer,
                maxiter=maxiter,
            )
            for i in range(counts.shape[1])
        ]
        res = zip(*res, strict=False)
        mle_lfcs_, mu_hat_, hat_diagonals_, converged_ = (np.array(m) for m in res)
        return mle_lfcs_, mu_hat_.T, hat_diagonals_.T, converged_

    def alpha_mle(
        self,
        counts: np.ndarray,
        design_matrix: np.ndarray,
        mu: np.ndarray,
        alpha_hat: np.ndarray,
        min_disp: float,
        max_disp: float,
        prior_disp_var: float | None = None,
        cr_reg: bool = True,
        prior_reg: bool = False,
        optimizer: Literal["BFGS", "L-BFGS-B"] = "L-BFGS-B",
    ) -> tuple[np.ndarray, np.ndarray]:
        res = [
            utils.fit_alpha_mle(
                counts=counts[:, i],
                design_matrix=design_matrix,
                mu=mu[:, i],
                alpha_hat=alpha_hat[i],
                min_disp=min_disp,
                max_disp=max_disp,
                prior_disp_var=prior_disp_var,
                cr_reg=cr_reg,
                prior_reg=prior_reg,
                optimizer=optimizer,
            )
            for i in range(counts.shape[1])
        ]
        res = zip(*res, strict=False)
        dispersions_, l_bfgs_b_converged_ = (np.array(m) for m in res)
        return dispersions_, l_bfgs_b_converged_

    def wald_test(
        self,
        design_matrix: np.ndarray,
        disp: np.ndarray,
        lfc: np.ndarray,
        mu: np.ndarray,
        ridge_factor: np.ndarray,
        contrast: np.ndarray,
        lfc_null: np.ndarray,
        alt_hypothesis: (
            Literal["greaterAbs", "lessAbs", "greater", "less"] | None
        ) = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        num_genes = mu.shape[1]
        res = [
            utils.wald_test(
                design_matrix=design_matrix,
                disp=disp[i],
                lfc=lfc[i],
                mu=mu[:, i],
                ridge_factor=ridge_factor,
                contrast=contrast,
                lfc_null=lfc_null,
                alt_hypothesis=alt_hypothesis,
            )
            for i in range(num_genes)
        ]
        res = zip(*res, strict=False)
        pvals, stats, se = (np.array(m) for m in res)
        return pvals, stats, se

    def lfc_shrink_nbinom_glm(
        self,
        design_matrix: np.ndarray,
        counts: np.ndarray,
        size: np.ndarray,
        offset: np.ndarray,
        prior_no_shrink_scale: float,
        prior_scale: float,
        optimizer: str,
        shrink_index: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        num_genes = counts.shape[1]
        res = [
            utils.nbinomGLM(
                design_matrix=design_matrix,
                counts=counts[:, i],
                size=size[i],
                offset=offset,
                prior_no_shrink_scale=prior_no_shrink_scale,
                prior_scale=prior_scale,
                optimizer=optimizer,
                shrink_index=shrink_index,
            )
            for i in range(num_genes)
        ]
        res = zip(*res, strict=False)
        return tuple(np.array(m) for m in res)
