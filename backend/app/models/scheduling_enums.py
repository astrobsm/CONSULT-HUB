import enum


class StationType(str, enum.Enum):
    CONSULTANT = "consultant"
    REGISTRAR = "registrar"
    MEDICAL_OFFICER = "medical_officer"
    RESIDENT = "resident"
    NURSE_PRACTITIONER = "nurse_practitioner"
    DIETICIAN = "dietician"
    PHYSIOTHERAPY = "physiotherapy"
    PSYCHOLOGY = "psychology"
    OCCUPATIONAL_THERAPY = "occupational_therapy"
    SOCIAL_WELFARE = "social_welfare"
    TELEMEDICINE = "telemedicine"
    PROCEDURE = "procedure"
    REVIEW = "review"
    EMERGENCY_WALK_IN = "emergency_walk_in"


class StationStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class LoadBalancing(str, enum.Enum):
    LEAST_BUSY = "least_busy"
    ROUND_ROBIN = "round_robin"


class AppointmentType(str, enum.Enum):
    NEW_PATIENT = "new_patient"
    REVIEW = "review"
    FOLLOW_UP = "follow_up"
    POSTOPERATIVE = "postoperative"
    PROCEDURE = "procedure"
    TELEMEDICINE = "telemedicine"
    EMERGENCY = "emergency"
    WALK_IN = "walk_in"
    PRIORITY = "priority"
    VIP = "vip"
    STAFF = "staff"
    INSURANCE = "insurance"
    PRIVATE = "private"


class AppointmentStatus(str, enum.Enum):
    BOOKED = "booked"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    WAITING = "waiting"
    CALLED = "called"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DID_NOT_ATTEND = "did_not_attend"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    REFERRED = "referred"
    ADMITTED = "admitted"
    DISCHARGED = "discharged"


# Statuses that free the slot for re-booking (a booking in any other status
# occupies the station+time). The partial unique index uses the member NAMES,
# because SQLAlchemy's Enum column stores the member name.
FREEING_STATUSES = {
    AppointmentStatus.CANCELLED,
    AppointmentStatus.RESCHEDULED,
}

# Statuses reachable from each status (lifecycle guard).
APPOINTMENT_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.BOOKED: {
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.RESCHEDULED,
        AppointmentStatus.DID_NOT_ATTEND,
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.RESCHEDULED,
        AppointmentStatus.DID_NOT_ATTEND,
    },
    AppointmentStatus.CHECKED_IN: {
        AppointmentStatus.WAITING,
        AppointmentStatus.CALLED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.WAITING: {
        AppointmentStatus.CALLED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.CALLED: {
        AppointmentStatus.IN_PROGRESS,
        AppointmentStatus.DID_NOT_ATTEND,
        AppointmentStatus.WAITING,
    },
    AppointmentStatus.IN_PROGRESS: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.REFERRED,
        AppointmentStatus.ADMITTED,
        AppointmentStatus.DISCHARGED,
    },
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.DID_NOT_ATTEND: {AppointmentStatus.RESCHEDULED},
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.RESCHEDULED: set(),
    AppointmentStatus.REFERRED: set(),
    AppointmentStatus.ADMITTED: set(),
    AppointmentStatus.DISCHARGED: set(),
}
