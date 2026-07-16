"""Canonical role constants and role-based permission helpers."""

from __future__ import annotations

# Administrative tiers
SUPER_ADMIN = "super_admin"
INSTITUTION_ADMIN = "institution_admin"
DEPARTMENT_ADMIN = "department_admin"

# Clinical / operational roles
CONSULTANT = "consultant"
REGISTRAR = "registrar"
MEDICAL_OFFICER = "medical_officer"
INTERN = "intern"
NURSE = "nurse"
PHYSIOTHERAPIST = "physiotherapist"
DIETICIAN = "dietician"
SOCIAL_WORKER = "social_worker"
RADIOLOGY = "radiology"
LABORATORY = "laboratory"
MEDICAL_RECORDS = "medical_records"
RECEPTION = "reception"
QUALITY_ASSURANCE = "quality_assurance"
RESEARCH = "research"

# All assignable roles (order is display order).
ALL_ROLES: list[str] = [
    SUPER_ADMIN,
    INSTITUTION_ADMIN,
    DEPARTMENT_ADMIN,
    CONSULTANT,
    REGISTRAR,
    MEDICAL_OFFICER,
    INTERN,
    NURSE,
    PHYSIOTHERAPIST,
    DIETICIAN,
    SOCIAL_WORKER,
    RADIOLOGY,
    LABORATORY,
    MEDICAL_RECORDS,
    RECEPTION,
    QUALITY_ASSURANCE,
    RESEARCH,
]

# Roles allowed to manage users / departments.
ADMIN_ROLES: set[str] = {SUPER_ADMIN, INSTITUTION_ADMIN}


def is_admin(role: str) -> bool:
    return role in ADMIN_ROLES


def is_valid_role(role: str) -> bool:
    return role in ALL_ROLES
