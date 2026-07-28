"""
data/real_wc26.py — Legacy interface to the real WC26 dataset.

Originally (mid-tournament) this module read the Kaggle CSVs directly with
pandas. After the tournament ended and the data was promoted to AWS Athena
(see migrate_kaggle_to_aws.py), every loader here was rewritten to query the
materialized Athena views instead — keeping the AWS-compute path the project
has always used (BigQuery pre-tournament, then Athena after the GCP→AWS move).

For backward-compatibility with the page files, this module re-exports the
same public function names. Internally they all go to data.athena.

If you need the original pandas-side loaders (e.g. for offline development
where AWS is unavailable), see the git history at commit prior to
"feat(real-data): rewire runtime layer to AWS Athena views".
"""
# Re-export the Athena-backed loaders under their legacy "real_wc26_*" names so
# existing `from data.real_wc26 import …` imports in the pages keep working.
from data.athena import (  # noqa: F401 — re-exports
    get_real_wc26_data_source_status,
    get_real_wc26_summary,
    get_real_wc26_outcome_counts,
    get_real_wc26_team_stats,
    get_real_wc26_team_strength,
    get_real_wc26_teams,
    get_real_wc26_match_team_stats,
    get_real_wc26_matches,
    get_real_wc26_matches_enriched,
    get_real_wc26_venues,
    get_real_wc26_referees,
    get_real_wc26_knockout_bracket,
    get_real_wc26_xg_by_team,
    get_real_wc26_players,
    get_real_wc26_player_stats,
)

# Stage ordering — Athena's view doesn't expose this as a column, so we declare
# it here once. Used by overview / predictions / matches pages for chart axes.
STAGE_ORDER = [
    "Group Stage",
    "Round of 32",
    "Round of 16",
    "Quarter-finals",
    "Semi-finals",
    "Third-place match",
    "Final",
]
