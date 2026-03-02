"""Generate VyaparSetu technical architecture diagram (SVG + PNG)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle


def _draw_box(ax, x: float, y: float, w: float, h: float, title: str, body: str = "", color: str = "#dbeafe", dashed: bool = False) -> None:
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=1.6,
        edgecolor="#1f2937",
        facecolor=color,
        linestyle="--" if dashed else "-",
        alpha=0.95,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h * 0.70, title, ha="center", va="center", fontsize=9.5, fontweight="bold")
    if body:
        ax.text(x + w / 2, y + h * 0.35, body, ha="center", va="center", fontsize=8)


def _draw_cloud(ax, x: float, y: float, w: float, h: float, label: str) -> None:
    cx = x + w / 2
    cy = y + h / 2
    radii = [0.035, 0.045, 0.04, 0.03]
    offsets = [(-0.05, 0.0), (-0.01, 0.02), (0.03, 0.0), (0.065, -0.005)]
    for (ox, oy), r in zip(offsets, radii):
        circ = Circle((cx + ox, cy + oy), r, fill=False, linewidth=1.4, linestyle="--", edgecolor="#6b7280")
        ax.add_patch(circ)
    ax.text(cx, cy - 0.055, label, ha="center", va="center", fontsize=8.2, color="#374151")


def _arrow(ax, x1: float, y1: float, x2: float, y2: float, dashed: bool = False) -> None:
    arrow = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle="->",
        mutation_scale=10,
        linewidth=1.2,
        color="#1f2937",
        linestyle="--" if dashed else "-",
    )
    ax.add_patch(arrow)


def main() -> None:
    out_dir = Path(__file__).resolve().parents[1] / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(18, 11))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.text(0.5, 0.97, "VyaparSetu - Technical Architecture", ha="center", fontsize=20, fontweight="bold")
    fig.text(0.5, 0.94, "IndiaAI Innovation Challenge 2026 | Problem Statement 2", ha="center", fontsize=12)

    blue = "#bfdbfe"
    green = "#bbf7d0"
    orange = "#fed7aa"
    gray = "#e5e7eb"

    _draw_box(ax, 0.08, 0.83, 0.16, 0.08, "MSE User", "(Phone/Web)", blue)
    _draw_box(ax, 0.39, 0.83, 0.22, 0.09, "Streamlit UI (8501)", "Unified onboarding console", blue)
    _draw_box(ax, 0.72, 0.83, 0.16, 0.08, "Admin User", "Monitoring and control", blue)

    _arrow(ax, 0.24, 0.87, 0.39, 0.87)
    _arrow(ax, 0.72, 0.87, 0.61, 0.87)

    _draw_box(ax, 0.08, 0.58, 0.20, 0.18, "UdyamBodh - Registration", "Udyam Fetcher\nGST Validator\nOCR Engine\nBusiness Classifier", green)
    _draw_box(ax, 0.31, 0.58, 0.20, 0.18, "VastraSuchi - Catalog", "Product Classifier\nHSN Mapper\nPricing Engine\nONDC Formatter", green)
    _draw_box(ax, 0.54, 0.58, 0.20, 0.18, "SahayakMap - SNP Match", "SNP Scorer (6-dim)\nMatching Engine\nExplainer", green)
    _draw_box(ax, 0.77, 0.58, 0.20, 0.18, "VriddhiDisha - Analytics", "Funnel\nGeo Maps\nWomen MSE\nCatalog Perf", green)

    _arrow(ax, 0.50, 0.83, 0.18, 0.76)
    _arrow(ax, 0.50, 0.83, 0.41, 0.76)
    _arrow(ax, 0.50, 0.83, 0.64, 0.76)
    _arrow(ax, 0.50, 0.83, 0.87, 0.76)

    _draw_box(ax, 0.04, 0.43, 0.20, 0.10, "Voice Engine", "Bhashini ASR/TTS", orange)
    _draw_box(ax, 0.32, 0.43, 0.22, 0.10, "Conversation Engine", "Guided dialogue flow", orange)
    _draw_box(ax, 0.60, 0.43, 0.30, 0.10, "LLM Engine", "Ollama / llama3.1:8b", orange)

    _arrow(ax, 0.24, 0.48, 0.32, 0.48)
    _arrow(ax, 0.43, 0.53, 0.43, 0.58)
    _arrow(ax, 0.90, 0.48, 0.90, 0.58)
    _arrow(ax, 0.76, 0.48, 0.74, 0.58)
    _arrow(ax, 0.70, 0.48, 0.51, 0.58)
    _arrow(ax, 0.66, 0.48, 0.28, 0.58)
    _arrow(ax, 0.10, 0.53, 0.18, 0.58)
    _arrow(ax, 0.10, 0.53, 0.41, 0.58)

    _draw_box(ax, 0.10, 0.22, 0.18, 0.09, "PostgreSQL / SQLite", "Operational storage", gray)
    _draw_box(ax, 0.32, 0.22, 0.18, 0.09, "ONDC Taxonomy (JSON)", "Categories + HSN", gray)
    _draw_box(ax, 0.54, 0.22, 0.18, 0.09, "SNP Database (JSON)", "Profiles + performance", gray)
    _draw_box(ax, 0.76, 0.22, 0.18, 0.09, "Synthetic Data (CSV)", "MSE + products + funnel", gray)

    _arrow(ax, 0.19, 0.31, 0.18, 0.58)
    _arrow(ax, 0.41, 0.31, 0.41, 0.58)
    _arrow(ax, 0.63, 0.31, 0.64, 0.58)
    _arrow(ax, 0.85, 0.31, 0.87, 0.58)

    _draw_cloud(ax, 0.03, 0.06, 0.14, 0.10, "Udyam API")
    _draw_cloud(ax, 0.18, 0.06, 0.14, 0.10, "GST API")
    _draw_cloud(ax, 0.33, 0.06, 0.14, 0.10, "Bhashini API")
    _draw_cloud(ax, 0.48, 0.06, 0.14, 0.10, "ONDC Network")
    _draw_cloud(ax, 0.63, 0.06, 0.14, 0.10, "TEAM Portal")

    _arrow(ax, 0.10, 0.16, 0.16, 0.58, dashed=True)
    _arrow(ax, 0.25, 0.16, 0.18, 0.58, dashed=True)
    _arrow(ax, 0.40, 0.16, 0.14, 0.48, dashed=True)
    _arrow(ax, 0.55, 0.16, 0.41, 0.58, dashed=True)
    _arrow(ax, 0.70, 0.16, 0.18, 0.58, dashed=True)

    svg_path = out_dir / "architecture_diagram.svg"
    png_path = out_dir / "architecture_diagram.png"
    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    fig.savefig(png_path, format="png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {svg_path}")
    print(f"Saved: {png_path}")


if __name__ == "__main__":
    main()
