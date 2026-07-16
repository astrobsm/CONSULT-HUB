"""Map ConsultHUB ORM models to FHIR R4 resource dicts.

Hand-built JSON (no FHIR library) — kept minimal but standards-valid: a
consultation is a ServiceRequest (the R4 resource for a referral / request for
service), a patient is a Patient. Values are plain dicts so routes can wrap them
in JSONResponse with the application/fhir+json media type.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.core.config import settings
from app.models.consultation import Consultation
from app.models.entities import Patient
from app.models.enums import ConsultationStatus, Priority

FHIR_VERSION = "4.0.1"
HOSPITAL_NUMBER_SYSTEM = "urn:consulthub:hospital-number"

# ConsultationStatus -> FHIR ServiceRequest.status
_STATUS_MAP: dict[ConsultationStatus, str] = {
    ConsultationStatus.DRAFT: "draft",
    ConsultationStatus.SUBMITTED: "active",
    ConsultationStatus.RECEIVED: "active",
    ConsultationStatus.VIEWED: "active",
    ConsultationStatus.ACKNOWLEDGED: "active",
    ConsultationStatus.ACCEPTED: "active",
    ConsultationStatus.SEEN: "active",
    ConsultationStatus.TRANSFERRED: "active",
    ConsultationStatus.DELEGATED: "active",
    ConsultationStatus.RETURNED: "on-hold",
    ConsultationStatus.ESCALATED: "active",
    ConsultationStatus.COMPLETED: "completed",
    ConsultationStatus.CANCELLED: "revoked",
    ConsultationStatus.REJECTED: "revoked",
}

# Priority -> FHIR request priority
_PRIORITY_MAP: dict[Priority, str] = {
    Priority.ROUTINE: "routine",
    Priority.URGENT: "urgent",
    Priority.EMERGENCY: "stat",
}


def _fhir_datetime(dt: datetime) -> str:
    """FHIR dateTime with a timezone (naive DB values are treated as UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _gender(sex: str | None) -> str:
    if not sex:
        return "unknown"
    s = sex.strip().lower()
    if s in ("male", "m"):
        return "male"
    if s in ("female", "f"):
        return "female"
    return "other"


def _human_name(full_name: str) -> dict[str, Any]:
    parts = full_name.split()
    name: dict[str, Any] = {"text": full_name}
    if len(parts) >= 2:
        name["family"] = parts[-1]
        name["given"] = parts[:-1]
    return name


def patient_to_fhir(p: Patient) -> dict[str, Any]:
    resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": str(p.id),
        "identifier": [
            {"system": HOSPITAL_NUMBER_SYSTEM, "value": p.hospital_number}
        ],
        "name": [_human_name(p.full_name)],
        "gender": _gender(p.sex),
    }
    if isinstance(p.date_of_birth, date):
        resource["birthDate"] = p.date_of_birth.isoformat()
    if p.phone:
        resource["telecom"] = [{"system": "phone", "value": p.phone}]
    return resource


def consultation_to_service_request(c: Consultation) -> dict[str, Any]:
    resource: dict[str, Any] = {
        "resourceType": "ServiceRequest",
        "id": str(c.id),
        "status": _STATUS_MAP.get(c.status, "unknown"),
        "intent": "order",
        "priority": _PRIORITY_MAP.get(c.priority, "routine"),
        "authoredOn": _fhir_datetime(c.created_at),
        "reasonCode": [{"text": c.reason}],
    }
    if c.patient_id is not None:
        resource["subject"] = {"reference": f"Patient/{c.patient_id}"}
    if c.requesting_user_id is not None:
        resource["requester"] = {
            "reference": f"Practitioner/{c.requesting_user_id}"
        }
    if c.target_specialty:
        resource["code"] = {"text": c.target_specialty}
    notes = [n for n in (c.clinical_summary, c.specific_questions) if n]
    if notes:
        resource["note"] = [{"text": n} for n in notes]
    return resource


def make_bundle(
    resources: list[dict[str, Any]], *, bundle_type: str = "searchset"
) -> dict[str, Any]:
    return {
        "resourceType": "Bundle",
        "type": bundle_type,
        "total": len(resources),
        "entry": [{"resource": r} for r in resources],
    }


def capability_statement() -> dict[str, Any]:
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": _fhir_datetime(datetime.now(timezone.utc)),
        "publisher": settings.app_name,
        "kind": "instance",
        "fhirVersion": FHIR_VERSION,
        "format": ["application/fhir+json"],
        "rest": [
            {
                "mode": "server",
                "resource": [
                    {
                        "type": "Patient",
                        "interaction": [
                            {"code": "read"},
                            {"code": "search-type"},
                        ],
                        "searchParam": [
                            {"name": "identifier", "type": "token"},
                            {"name": "name", "type": "string"},
                        ],
                    },
                    {
                        "type": "ServiceRequest",
                        "interaction": [
                            {"code": "read"},
                            {"code": "search-type"},
                        ],
                        "searchParam": [
                            {"name": "patient", "type": "reference"}
                        ],
                    },
                ],
            }
        ],
    }
