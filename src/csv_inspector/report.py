
from pathlib import Path
from typing import Dict, List, Tuple
import json

import pandas as pd
import matplotlib.pyplot as plt

from jinja2 import Environment, FileSystemLoader

def summarize(df: pd.DataFrame) -> dict:
    
    try:
        desc = df.describe(include="all", datetime_is_numeric=True)
    except TypeError:
        
        desc = df.describe(include="all")
    summary = {
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "na_percent": {c: float(df[c].isna().mean() * 100) for c in df.columns},
        "describe": desc.to_dict(),
    }
    return summary

def numeric_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

def save_histograms(df: pd.DataFrame, outdir: Path, max_cols: int = 8) -> List[str]:
    outdir.mkdir(parents=True, exist_ok=True)
    paths = []
    for c in numeric_columns(df)[:max_cols]:
        plt.figure()
        df[c].dropna().plot(kind="hist", bins=30)
        plt.title(f"Histogram: {c}")
        p = outdir / f"hist_{c}.png"
        plt.savefig(p, dpi=150, bbox_inches="tight")
        plt.close()
        paths.append(str(p))
    return paths

def correlation(df: pd.DataFrame) -> pd.DataFrame:
    num_df = df[numeric_columns(df)]
    if num_df.empty:
        return pd.DataFrame()
    return num_df.corr(numeric_only=True)

def top_correlations(corr: pd.DataFrame, k: int = 5, min_abs: float = 0.0) -> List[Tuple[str, str, float]]:
    if corr.empty:
        return []
    pairs = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            val = float(corr.iloc[i, j])
            if abs(val) >= min_abs:
                pairs.append((cols[i], cols[j], val))
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    return pairs[:k]


def save_corr_heatmap(corr: pd.DataFrame, outdir: Path) -> str:
    if corr.empty:
        return ""
    outdir.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6, 5))
    plt.imshow(corr, interpolation='nearest')
    plt.colorbar()
    plt.xticks(range(len(corr.columns)), corr.columns, rotation=45, ha="right")
    plt.yticks(range(len(corr.index)), corr.index)
    plt.title("Correlation Heatmap")
    p = outdir / "corr_heatmap.png"
    plt.tight_layout()
    plt.savefig(p, dpi=150, bbox_inches="tight")
    plt.close()
    return str(p)

def outlier_counts(
    df: pd.DataFrame,
    z_thresh: float = 3.0,
    method: str = "z",           # "z" veya "iqr"
    iqr_mult: float = 1.5        # IQR çarpanı (1.5 klasik, 3.0 daha muhafazakâr)
) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for c in numeric_columns(df):
        s = df[c].dropna()
        if s.empty:
            counts[c] = 0
            continue

        if method == "iqr":
            q1 = s.quantile(0.25)
            q3 = s.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                counts[c] = 0
                continue
            lower = q1 - iqr_mult * iqr
            upper = q3 + iqr_mult * iqr
            counts[c] = int(((s < lower) | (s > upper)).sum())
        else:
            # z-score
            m = s.mean()
            std = s.std() or 0.0
            if std == 0:
                counts[c] = 0
                continue
            z = (s - m).abs() / std
            counts[c] = int((z > z_thresh).sum())
    return counts


def save_json(data: Dict, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def render_html_report(
    summary: Dict,
    hist_images: List[str],
    corr_image: str,
    top_corr_pairs: List[Tuple[str, str, float]],
    outdir: Path,
    templates_dir: Path,
    title: str = "CSV Inspector Report",
) -> str:
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    tmpl = env.get_template("report.html.j2")
    html = tmpl.render(
        title=title,
        summary=summary,
        hist_images=[Path(p).name for p in hist_images],
        corr_image=(Path(corr_image).name if corr_image else ""),
        top_corr_pairs=top_corr_pairs,
    )
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "report.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return str(out)
