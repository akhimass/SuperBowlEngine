from __future__ import annotations

import argparse
from pathlib import Path

from gridironiq.models.training_data import build_training_rows, save_training_rows_parquet
from gridironiq.models.fit_win_prob_model import fit_win_prob_model, save_win_prob_artifact
from gridironiq.models.fit_margin_model import fit_margin_model, save_margin_artifact
from gridironiq.models.fit_total_model import fit_total_model, save_total_artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2020)
    parser.add_argument("--end", type=int, default=2025)
    parser.add_argument("--no-parquet", action="store_true")
    args = parser.parse_args()

    seasons = list(range(args.start, args.end + 1))
    df = build_training_rows(seasons)
    print("Built training rows:", len(df))

    if not args.no_parquet:
        p = save_training_rows_parquet(df, f"outputs/model_training/training_rows_{args.start}_{args.end}.parquet")
        print("Saved training parquet:", p)

    win_fit = fit_win_prob_model(df, calibrate=True)
    m_fit = fit_margin_model(df)
    t_fit = fit_total_model(df)

    win_path = save_win_prob_artifact(win_fit)
    m_path = save_margin_artifact(m_fit)
    t_path = save_total_artifact(t_fit)

    print("\n=== Win probability model ===")
    print(win_fit.metrics)
    print("Saved:", win_path)

    print("\n=== Margin model ===")
    print(m_fit.metrics)
    print("Saved:", m_path)

    print("\n=== Total model ===")
    print(t_fit.metrics)
    print("Saved:", t_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

