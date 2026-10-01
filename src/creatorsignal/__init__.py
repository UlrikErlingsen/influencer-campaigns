"""CreatorSignal: open, local-first influencer campaign manager for the Norwegian market.

Public API. The package never imports Streamlit: the UI (``app.py``) calls these functions, so another front end
(for example a future merged Signal Hub) can reuse the same logic and storage.
"""

__version__ = "1.0.0.dev0"

DISCLAIMER = "Checklist support, not legal advice."

from .compliance import (  # noqa: E402
    ChecklistStatus,
    GateResult,
    applicable_rules,
    campaign_restricted_categories,
    checklist_status,
    paid_gate,
)
from .demo import DEMO_NOTICE, load_demo  # noqa: E402
from .errors import DataProblem, GateBlocked, friendly_message  # noqa: E402
from .io import read_table, safe_frame, validate_creators, validate_results  # noqa: E402
from .metrics import cost_per_redemption, cpc, cpm, roas, summarize_results  # noqa: E402
from .report import CampaignReport, build_html, build_report, build_xlsx  # noqa: E402
from .rules import Rule, RuleSet, load_rules  # noqa: E402
from .storage import STAGES, Store, default_db_path  # noqa: E402
from .utm import build_tracked_url, utm_params  # noqa: E402

__all__ = [
    "DEMO_NOTICE",
    "DISCLAIMER",
    "STAGES",
    "CampaignReport",
    "ChecklistStatus",
    "DataProblem",
    "GateBlocked",
    "GateResult",
    "Rule",
    "RuleSet",
    "Store",
    "__version__",
    "applicable_rules",
    "build_html",
    "build_report",
    "build_tracked_url",
    "build_xlsx",
    "campaign_restricted_categories",
    "checklist_status",
    "cost_per_redemption",
    "cpc",
    "cpm",
    "default_db_path",
    "friendly_message",
    "load_demo",
    "load_rules",
    "paid_gate",
    "read_table",
    "roas",
    "safe_frame",
    "summarize_results",
    "utm_params",
    "validate_creators",
    "validate_results",
]
