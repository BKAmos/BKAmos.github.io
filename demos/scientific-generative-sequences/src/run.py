"""PWM sampling + latent-modulated motif strength; scores and interpolation path."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"

BASES = list("ACGT")
BASE_IDX = {b: i for i, b in enumerate(BASES)}
SEQ_LEN = 40
MOTIF_START = 8
RNG = np.random.default_rng(7)


def load_pwm() -> tuple[np.ndarray, np.ndarray]:
    long = pd.read_csv(DATA_DIR / "motif_pwm_long.csv")
    npos = long["position"].nunique()
    pwm = np.zeros((npos, 4))
    for _, row in long.iterrows():
        pwm[int(row["position"]), BASE_IDX[row["base"]]] = row["probability"]
    bg_row = pd.read_csv(DATA_DIR / "background_nt.csv").iloc[0]
    bg = np.array([bg_row[b] for b in BASES], dtype=float)
    bg = bg / bg.sum()
    return pwm, bg


def mix_pwm_strength(pwm_fg: np.ndarray, bg: np.ndarray, strength: float) -> np.ndarray:
    """Per-row convex mix; renormalize."""
    s = np.clip(strength, 0.0, 1.0)
    m = s * pwm_fg + (1.0 - s) * bg
    return m / m.sum(axis=1, keepdims=True)


def sample_seq(mix_mat: np.ndarray, motif_start: int, bg: np.ndarray) -> str:
    """mix_mat rows only cover motif; flanks use bg."""
    chars = []
    for pos in range(SEQ_LEN):
        if motif_start <= pos < motif_start + mix_mat.shape[0]:
            probs = mix_mat[pos - motif_start]
        else:
            probs = bg
        chars.append(RNG.choice(list(BASES), p=probs))
    return "".join(chars)


def log_odds_score(seq: str, pwm: np.ndarray, bg: np.ndarray, motif_start: int) -> float:
    score = 0.0
    for k in range(pwm.shape[0]):
        b = seq[motif_start + k]
        score += np.log(max(pwm[k, BASE_IDX[b]], 1e-12) / max(bg[BASE_IDX[b]], 1e-12))
    return float(score)


def freq_matrix(seqs: list[str], start: int, length: int) -> np.ndarray:
    mat = np.zeros((length, 4))
    for s in seqs:
        for k in range(length):
            mat[k, BASE_IDX[s[start + k]]] += 1
    return mat / max(len(seqs), 1)


def plot_logo(freq: np.ndarray, ax, title: str) -> None:
    x = np.arange(freq.shape[0])
    bottom = np.zeros_like(x, dtype=float)
    colors = ["#4c72b0", "#55a868", "#c44e52", "#8172b2"]
    for j, (b, c) in enumerate(zip(BASES, colors)):
        ax.bar(x, freq[:, j], bottom=bottom, label=b, color=c, width=0.85)
        bottom = bottom + freq[:, j]
    ax.set_ylim(0, 1)
    ax.set_xlabel("Motif position")
    ax.set_ylabel("Frequency")
    ax.set_title(title)


def latent_strength(z0: float, z1: float) -> float:
    """Logistic in 2D latent — toy 'decoder'."""
    return float(1.0 / (1.0 + np.exp(-(0.9 * z0 + 0.55 * z1 - 0.15))))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pwm, bg = load_pwm()
    L = pwm.shape[0]
    assert MOTIF_START + L <= SEQ_LEN

    n_each = 220
    neg, pos = [], []
    for _ in range(n_each):
        mix_neg = np.tile(bg, (L, 1))
        neg.append(sample_seq(mix_neg, MOTIF_START, bg))
        mix_pos = pwm
        pos.append(sample_seq(mix_pos, MOTIF_START, bg))

    # High-strength latent corner vs low-strength
    z_hi = (1.6, 1.1)
    z_lo = (-1.8, -1.2)
    gen_hi, gen_lo = [], []
    for _ in range(n_each):
        s_hi = latent_strength(*z_hi)
        s_lo = latent_strength(*z_lo)
        gen_hi.append(sample_seq(mix_pwm_strength(pwm, bg, s_hi), MOTIF_START, bg))
        gen_lo.append(sample_seq(mix_pwm_strength(pwm, bg, s_lo), MOTIF_START, bg))

    # Interpolation in latent space
    ts = np.linspace(0, 1, 15)
    path_scores = []
    z_path = []
    for t in ts:
        z = (1 - t) * np.array(z_lo) + t * np.array(z_hi)
        z_path.append(z)
        st = latent_strength(float(z[0]), float(z[1]))
        scores = []
        for _ in range(120):
            seq = sample_seq(mix_pwm_strength(pwm, bg, st), MOTIF_START, bg)
            scores.append(log_odds_score(seq, pwm, bg, MOTIF_START))
        path_scores.append(np.mean(scores))

    fig1, axes = plt.subplots(1, 3, figsize=(12, 3.4), sharey=True)
    plot_logo(freq_matrix(neg, MOTIF_START, L), axes[0], "Negative (background)")
    plot_logo(freq_matrix(pos, MOTIF_START, L), axes[1], "Positive (PWM)")
    plot_logo(freq_matrix(gen_hi, MOTIF_START, L), axes[2], f"Generated (latent z={z_hi}, high strength)")
    axes[1].legend(ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.22))
    fig1.suptitle("Motif region composition — PWM vs latent-modulated generation", y=1.12)
    fig1.tight_layout()
    fig1.savefig(OUT_DIR / "motif_composition.png", dpi=120, bbox_inches="tight")
    plt.close(fig1)

    scores_neg = [log_odds_score(s, pwm, bg, MOTIF_START) for s in neg]
    scores_pos = [log_odds_score(s, pwm, bg, MOTIF_START) for s in pos]
    scores_hi = [log_odds_score(s, pwm, bg, MOTIF_START) for s in gen_hi]
    fig2, ax = plt.subplots(figsize=(7, 4))
    ax.hist(scores_neg, bins=22, alpha=0.55, label="Negative", color="#888888")
    ax.hist(scores_pos, bins=22, alpha=0.55, label="Positive (PWM)", color="#4c72b0")
    ax.hist(scores_hi, bins=22, alpha=0.55, label="Generated (high latent)", color="#c44e52")
    ax.set_xlabel("PWM log-odds score (motif window)")
    ax.set_ylabel("Count")
    ax.set_title("Score distributions — classical PWM vs generative latent mix")
    ax.legend()
    fig2.tight_layout()
    fig2.savefig(OUT_DIR / "score_histograms.png", dpi=120)
    plt.close(fig2)

    fig3, ax = plt.subplots(figsize=(7, 4))
    ax.plot(ts, path_scores, "o-", color="#157878", lw=2, markersize=6)
    ax.set_xlabel("Interpolation t (latent path z_lo → z_hi)")
    ax.set_ylabel("Mean PWM log-odds (n=120 samples / point)")
    ax.set_title("Latent interpolation — smooth motif strength trajectory (toy decoder)")
    fig3.tight_layout()
    fig3.savefig(OUT_DIR / "latent_interpolation.png", dpi=120)
    plt.close(fig3)

    # Path in latent plane colored by strength
    zs = np.array(z_path)
    strengths = [latent_strength(float(a), float(b)) for a, b in zs]
    fig4, ax = plt.subplots(figsize=(5.2, 4.2))
    sc = ax.scatter(zs[:, 0], zs[:, 1], c=strengths, cmap="viridis", s=80, edgecolor="k", lw=0.3)
    ax.plot(zs[:, 0], zs[:, 1], color="#333", lw=0.8, alpha=0.5)
    plt.colorbar(sc, ax=ax, label="Motif strength s(z)")
    ax.set_xlabel("z0")
    ax.set_ylabel("z1")
    ax.set_title("Latent path colored by decoder strength")
    fig4.tight_layout()
    fig4.savefig(OUT_DIR / "latent_path.png", dpi=120)
    plt.close(fig4)

    pd.DataFrame({"t": ts, "mean_log_odds": path_scores}).to_csv(OUT_DIR / "interpolation_curve.csv", index=False)
    print(f"Wrote figures and {OUT_DIR / 'interpolation_curve.csv'}")


if __name__ == "__main__":
    main()
