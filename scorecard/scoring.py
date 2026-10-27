"""Turning raw metrics into relative scores."""

from __future__ import annotations

import pandas as pd


def rank_and_score(metrics: pd.DataFrame, higher_is_better: dict[str, bool], score_name: str) -> pd.DataFrame:
    """Percentile-rank each metric within the group and average into a score /100.

    For metrics where lower is better (e.g. debt), the ranking is flipped so
    that 100 always means "best in the group". A company missing a metric is
    scored on the metrics it has.
    """
    ranks = pd.DataFrame(index=metrics.index)
    for col, higher in higher_is_better.items():
        ranks[f"{col}_rank"] = metrics[col].rank(pct=True, ascending=higher, method="average") * 100
    result = metrics.join(ranks)
    result[score_name] = ranks.mean(axis=1, skipna=True).round(1)
    return result.sort_values(score_name, ascending=False)
