
import argparse
from pathlib import Path
import pandas as pd

from .report import (
    summarize, save_histograms, correlation, save_corr_heatmap,
    top_correlations, outlier_counts, save_json, render_html_report
)

def main():
    parser = argparse.ArgumentParser(description="CSV Inspector Pro")
    parser.add_argument("csv_path", type=str, help="Path to CSV file")
    parser.add_argument("--sep", default=",", help="CSV separator")
    parser.add_argument("--limit", type=int, default=None, help="Read first N rows")
    parser.add_argument("--out", default="reports", help="Output directory")
    parser.add_argument("--max-hist", type=int, default=8, help="Max histograms to generate")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--zthresh", type=float, default=3.0, help="Z score threshold for Outlier (default: 3.0)")
    parser.add_argument("--outlier-method", choices=["z", "iqr"], default="z",help="Outlier method: z or iqr (default: z)")
    parser.add_argument("--iqr-mult", type=float, default=1.5, help="IQR multiplexer (default: 1.5; 3.0 is stricter)")
    parser.add_argument("--title", default="CSV Inspector Report", help="Title for the HTML report")
    parser.add_argument("--corr-min", type=float, default=0.0, help="Minimum |correlation| to list in the top pairs (default: 0.0)")


    args = parser.parse_args()

    path = Path(args.csv_path)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    df = pd.read_csv(path, sep=args.sep, nrows=args.limit)

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # Summary + outliers
    summary = summarize(df)
    summary["outliers"] = outlier_counts(
    df,
    z_thresh=args.zthresh,
    method=args.outlier_method,
    iqr_mult=args.iqr_mult
    )
    # Outlier method info for HTML report
    summary["outlier_method"] = "IQR" if args.outlier_method == "iqr" else "Z-score"
    summary["outlier_param"] = (
        f"mult={args.iqr_mult}" if args.outlier_method == "iqr" else f"Z>{args.zthresh}"
    )

    save_json(summary, outdir / "summary.json")

    # Histograms
    hist_imgs = save_histograms(df, outdir, max_cols=args.max_hist)

    # Correlation
    corr = correlation(df)
    corr_img = save_corr_heatmap(corr, outdir) if not corr.empty else ""
    top_corr_pairs = top_correlations(corr, k=5, min_abs=args.corr_min)
    if args.corr_min > 0:
        print(f"Top corr pairs (|r|>={args.corr_min}):", top_corr_pairs)



    # Optional HTML report
    if args.html:
        templates_dir = Path(__file__).resolve().parents[2] / "templates"
        render_html_report(summary, hist_imgs, corr_img, top_corr_pairs, outdir, templates_dir, title=args.title)


    print("--- CSV INSPECTOR REPORT ---")
    print(f"Rows: {summary['rows']}, Cols: {summary['cols']}")
    print("Outliers (per numeric column):", summary["outliers"])
    if corr_img:
        print("Correlation heatmap:", corr_img)
    print("Histograms:", hist_imgs)

if __name__ == "__main__":
    main()
