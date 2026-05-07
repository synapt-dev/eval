"""Report card generation: markdown and JSON output."""

from synapt_eval.report_card.compose import compose_report_card
from synapt_eval.report_card.json_output import (
    generate_json,
    generate_json_string,
)
from synapt_eval.report_card.markdown import generate_markdown
from synapt_eval.report_card.types import (
    CategorySection,
    ReportCard,
    ReportCardFooter,
    ReportCardHeader,
    TrendingEntry,
)

__all__ = [
    "CategorySection",
    "ReportCard",
    "ReportCardFooter",
    "ReportCardHeader",
    "TrendingEntry",
    "compose_report_card",
    "generate_json",
    "generate_json_string",
    "generate_markdown",
]
