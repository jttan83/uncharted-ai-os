from enum import Enum

NAME_MAX_LENGTH = 120
FUNCTIONAL_AREA_MAX_LENGTH = 120
DESCRIPTION_MAX_LENGTH = 2_000
OVERSIGHT_NOTES_MAX_LENGTH = 2_000
ASSESSMENT_NOTES_MAX_LENGTH = 5_000
CONTEXT_ENTRY_MAX_LENGTH = 200
CONTEXT_ENTRIES_MAX_COUNT = 50
ASSESSMENT_SCORE_MIN = 1
ASSESSMENT_SCORE_MAX = 5


class CapabilityStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class CapabilityMaturity(str, Enum):
    NOT_ASSESSED = "not_assessed"
    MANUAL = "manual"
    AI_ASSISTED = "ai_assisted"
    AI_EXECUTABLE = "ai_executable"
    AUTOMATED = "automated"


class HumanOversight(str, Enum):
    NONE = "none"
    REVIEW_RECOMMENDED = "review_recommended"
    APPROVAL_REQUIRED = "approval_required"
    HUMAN_LED = "human_led"


class FrequencyPeriod(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    AD_HOC = "ad_hoc"
    UNKNOWN = "unknown"


CALENDAR_FREQUENCY_PERIODS = frozenset(
    {
        FrequencyPeriod.DAY,
        FrequencyPeriod.WEEK,
        FrequencyPeriod.MONTH,
        FrequencyPeriod.QUARTER,
        FrequencyPeriod.YEAR,
    }
)

ASSESSMENT_BEARING_FIELDS = frozenset(
    {
        "current_maturity",
        "target_maturity",
        "human_oversight",
        "oversight_notes",
        "business_value",
        "ai_feasibility",
        "ai_execution_risk",
        "assessment_notes",
    }
)
