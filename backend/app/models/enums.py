import enum


class Priority(str, enum.Enum):
    ROUTINE = "routine"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class ConsultationType(str, enum.Enum):
    ROUTINE = "routine"
    URGENT = "urgent"
    EMERGENCY = "emergency"
    ICU = "icu"
    WARD = "ward"
    CLINIC = "clinic"
    EMERGENCY_DEPARTMENT = "emergency_department"
    THEATRE = "theatre"
    PREOPERATIVE = "preoperative"
    POSTOPERATIVE = "postoperative"
    NUTRITION = "nutrition"
    PAIN_MANAGEMENT = "pain_management"
    REHABILITATION = "rehabilitation"
    PSYCHOLOGICAL = "psychological"
    SOCIAL_WELFARE = "social_welfare"
    TELECONSULTATION = "teleconsultation"
    SECOND_OPINION = "second_opinion"
    TUMOR_BOARD = "tumor_board"
    MDT = "mdt"
    REFERRAL = "referral"
    HOME_CARE = "home_care"
    PALLIATIVE_CARE = "palliative_care"
    DISCHARGE_PLANNING = "discharge_planning"


class ConsultationStatus(str, enum.Enum):
    """Workflow states a consultation moves through (see spec workflow)."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    RECEIVED = "received"
    VIEWED = "viewed"
    ACKNOWLEDGED = "acknowledged"
    ACCEPTED = "accepted"
    SEEN = "seen"
    TRANSFERRED = "transferred"
    DELEGATED = "delegated"
    REJECTED = "rejected"
    RETURNED = "returned"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Allowed forward transitions. Terminal states map to an empty set.
STATUS_TRANSITIONS: dict[ConsultationStatus, set[ConsultationStatus]] = {
    ConsultationStatus.DRAFT: {
        ConsultationStatus.SUBMITTED,
        ConsultationStatus.CANCELLED,
    },
    ConsultationStatus.SUBMITTED: {
        ConsultationStatus.RECEIVED,
        ConsultationStatus.ACKNOWLEDGED,
        ConsultationStatus.ESCALATED,
        ConsultationStatus.CANCELLED,
    },
    ConsultationStatus.RECEIVED: {
        ConsultationStatus.VIEWED,
        ConsultationStatus.ACKNOWLEDGED,
        ConsultationStatus.ESCALATED,
        ConsultationStatus.CANCELLED,
    },
    ConsultationStatus.VIEWED: {
        ConsultationStatus.ACKNOWLEDGED,
        ConsultationStatus.ESCALATED,
        ConsultationStatus.CANCELLED,
    },
    ConsultationStatus.ACKNOWLEDGED: {
        ConsultationStatus.ACCEPTED,
        ConsultationStatus.TRANSFERRED,
        ConsultationStatus.DELEGATED,
        ConsultationStatus.REJECTED,
        ConsultationStatus.RETURNED,
        ConsultationStatus.ESCALATED,
        ConsultationStatus.CANCELLED,
    },
    ConsultationStatus.ACCEPTED: {
        ConsultationStatus.SEEN,
        ConsultationStatus.TRANSFERRED,
        ConsultationStatus.DELEGATED,
        ConsultationStatus.ESCALATED,
        ConsultationStatus.CANCELLED,
    },
    ConsultationStatus.SEEN: {
        ConsultationStatus.COMPLETED,
        ConsultationStatus.RETURNED,
        ConsultationStatus.ESCALATED,
    },
    ConsultationStatus.TRANSFERRED: {
        ConsultationStatus.ACKNOWLEDGED,
        ConsultationStatus.CANCELLED,
    },
    ConsultationStatus.DELEGATED: {
        ConsultationStatus.ACKNOWLEDGED,
        ConsultationStatus.CANCELLED,
    },
    ConsultationStatus.RETURNED: {
        ConsultationStatus.SUBMITTED,
        ConsultationStatus.CANCELLED,
    },
    ConsultationStatus.REJECTED: set(),
    ConsultationStatus.ESCALATED: {
        ConsultationStatus.ACKNOWLEDGED,
        ConsultationStatus.ACCEPTED,
        ConsultationStatus.CANCELLED,
    },
    ConsultationStatus.COMPLETED: set(),
    ConsultationStatus.CANCELLED: set(),
}
