"""Turning raw metrics into relative scores.

Two kinds of ranking:

  Universe-wide: a metric is ranked against every company. Right for things
  that mean the same in any business, like return on capital.

  Peer-relative: a metric is ranked only against similar companies. Right for
  things driven by the business model. A supermarket's 7% gross margin and a
  luxury brand's 68% aren't better or worse than each other, just different
  businesses. So margins are compared within peer groups.

Peer groups use the narrowest classification with enough members: the
company's industry (e.g. "Grocery Stores") if at least MIN_PEERS companies
share it, otherwise its broader sector (e.g. "Consumer Defensive"), otherwise
the whole universe.
"""

from __future__ import annotations

import pandas as pd

MIN_PEERS = 3


def assign_peer_groups(info: pd.DataFrame, min_peers: int = MIN_PEERS) -> pd.Series:
    """Label each company with its peer group, given 'industry' and 'sector' columns."""
    industry_counts = info["industry"].map(info["industry"].value_counts())
    sector_counts = info["sector"].map(info["sector"].value_counts())
    groups = pd.Series("All companies", index=info.index)
    groups[sector_counts >= min_peers] = "Sector: " + info["sector"]
    groups[industry_counts >= min_peers] = "Industry: " + info["industry"]
    return groups


def rank_and_score(
    metrics: pd.DataFrame,
    higher_is_better: dict[str, bool],
    score_name: str,
    peer_groups: pd.Series | None = None,
    peer_relative: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Percentile-rank each metric and average into a score /100.

    For metrics where lower is better (e.g. debt), the ranking is flipped so
    that 100 always means "best". Metrics named in `peer_relative` are ranked
    within `peer_groups` when groups are supplied; all others universe-wide.
    A company missing a metric is scored on the metrics it has.
    """
    ranks = pd.DataFrame(index=metrics.index)
    for col, higher in higher_is_better.items():
        if peer_groups is not None and col in peer_relative:
            groups = peer_groups.reindex(metrics.index)
            ranks[f"{col}_rank"] = metrics[col].groupby(groups).rank(pct=True, ascending=higher, method="average") * 100
        else:
            ranks[f"{col}_rank"] = metrics[col].rank(pct=True, ascending=higher, method="average") * 100
    result = metrics.join(ranks)
    result[score_name] = ranks.mean(axis=1, skipna=True).round(1)
    return result.sort_values(score_name, ascending=False)
