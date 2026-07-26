"""Render the PRD-10 figures from the committed experiment artifacts.

Two plots, both regenerated from JSON so the README/notebook never drift from
the measurements: the fit-gate precision/coverage trade-off, and the
forged-trail arms (where the honest bar is the false-positive rate).

Run: uv run python scripts/render_pin_figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ASSETS = Path("assets")
EXPERIMENTS = Path("results/experiments")


def fit_sweep() -> None:
    data = json.loads((EXPERIMENTS / "plateau_localization.json").read_text())
    table = data["by_fit_threshold"]
    fits = [float(k) for k in table]
    fire = [table[k]["fire_rate"] for k in table]
    exact = [table[k]["exact_when_fired"] or 0.0 for k in table]
    figure, axis = plt.subplots(figsize=(6.4, 4))
    axis.plot(fits, fire, marker="o", color="#1f6feb", label="fires (share of turns)")
    axis.plot(fits, exact, marker="s", color="#1a7f37", label="exact when it fires")
    axis.axvline(data["shipped_fit_threshold"], ls="--", c="gray",
                 label=f"shipped gate = {data['shipped_fit_threshold']}")
    axis.axhline(data["argmax_exact_rate"], ls=":", c="#cf222e",
                 label=f"posterior argmax exact = {data['argmax_exact_rate']:.2f}")
    axis.set_xlabel("plateau fit threshold (Jaccard)")
    axis.set_ylabel("rate")
    axis.set_ylim(0, 1.05)
    axis.set_title("Dwell-plateau pin: precision bought with coverage")
    axis.legend(fontsize=8, loc="lower left")
    figure.tight_layout()
    figure.savefig(ASSETS / "plateau_fit_sweep.png", dpi=120)
    plt.close(figure)


def forgery_arms() -> None:
    data = json.loads((EXPERIMENTS / "trail_forgery.json").read_text())
    arms = data["arms"]
    names = list(arms)
    detected = [arms[a]["detected_rate"] for a in names]
    capture = [arms[a]["capture_rate"] for a in names]
    positions = range(len(names))
    figure, axis = plt.subplots(figsize=(6.4, 4))
    axis.bar([p - 0.2 for p in positions], detected, width=0.4,
             color="#8250df", label="forgery detected")
    axis.bar([p + 0.2 for p in positions], capture, width=0.4,
             color="#1f6feb", label="capture rate")
    axis.set_xticks(list(positions))
    axis.set_xticklabels(names, fontsize=8)
    axis.set_ylabel("rate")
    axis.set_ylim(0, 1.05)
    axis.set_title("Forged trails: the honest bar is the false-positive rate")
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(ASSETS / "trail_forgery_arms.png", dpi=120)
    plt.close(figure)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    fit_sweep()
    forgery_arms()
    print("wrote assets/plateau_fit_sweep.png, assets/trail_forgery_arms.png")


if __name__ == "__main__":
    main()
