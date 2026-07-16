"""Idempotent dev seed: one institution, an admin, and a registrar.

Run from the backend directory:

    python -m app.seed
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.entities import Department, Institution, Patient, User

# Import models so all tables register before create_all.
import app.models  # noqa: F401

DEMO_INSTITUTION_CODE = "DEMO"
DEMO_USERS = [
    {
        "full_name": "System Administrator",
        "email": "superadmin@consulthub.local",
        "password": "consulthub",
        "role": "super_admin",
        "designation": "Platform Super Admin",
        "institution_id": None,  # cross-tenant
    },
    {
        "full_name": "Dr. Amina Bello",
        "email": "admin@consulthub.local",
        "password": "consulthub",
        "role": "institution_admin",
        "designation": "Medical Director",
    },
    {
        "full_name": "Dr. Chike Okonkwo",
        "email": "registrar@consulthub.local",
        "password": "consulthub",
        "role": "registrar",
        "designation": "Senior Registrar, Internal Medicine",
    },
    {
        "full_name": "Dr. Ngozi Eze",
        "email": "consultant@consulthub.local",
        "password": "consulthub",
        "role": "consultant",
        "designation": "Consultant Plastic Surgeon",
    },
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        institution = db.scalar(
            select(Institution).where(Institution.code == DEMO_INSTITUTION_CODE)
        )
        if institution is None:
            institution = Institution(
                name="Demo Teaching Hospital", code=DEMO_INSTITUTION_CODE
            )
            db.add(institution)
            db.flush()
            db.add_all(
                [
                    Department(
                        institution_id=institution.id,
                        name="Internal Medicine",
                        specialty="Internal Medicine",
                    ),
                    Department(
                        institution_id=institution.id,
                        name="Plastic Surgery",
                        specialty="Plastic & Reconstructive Surgery",
                    ),
                    Department(
                        institution_id=institution.id,
                        name="Dietetics",
                        specialty="Nutrition & Dietetics",
                    ),
                ]
            )
            print(
                f"Created institution '{institution.name}' "
                "with 3 departments."
            )
        else:
            print(f"Institution '{institution.name}' already exists.")

        for spec in DEMO_USERS:
            existing = db.scalar(
                select(User).where(User.email == spec["email"])
            )
            if existing:
                print(f"User {spec['email']} already exists.")
                continue
            db.add(
                User(
                    full_name=spec["full_name"],
                    email=spec["email"],
                    hashed_password=hash_password(spec["password"]),
                    role=spec["role"],
                    designation=spec["designation"],
                    institution_id=spec.get("institution_id", institution.id),
                )
            )
            print(
                f"Created user {spec['email']} "
                f"(password: {spec['password']})."
            )

        _seed_patients(db, institution.id)
        _seed_clinic(db, institution.id)

        db.commit()
        print(
            "\nSeed complete. Log in with "
            "admin@consulthub.local / consulthub"
        )
    finally:
        db.close()


def _seed_clinic(db, institution_id: int) -> None:
    from app.models.scheduling import Clinic, ConsultationStation
    from app.models.scheduling_enums import StationType

    existing = db.scalar(
        select(Clinic).where(
            Clinic.institution_id == institution_id,
            Clinic.name == "Burn Clinic",
        )
    )
    if existing:
        print("Clinic 'Burn Clinic' already exists.")
        return

    clinic = Clinic(
        institution_id=institution_id,
        name="Burn Clinic",
        subspecialty="Plastic & Reconstructive Surgery",
        location="Outpatient Block, Level 2",
        operating_days="0,1,2,3,4",
        open_time="08:00",
        close_time="13:00",
        slot_duration_minutes=20,
    )
    db.add(clinic)
    db.flush()
    db.add_all(
        [
            ConsultationStation(
                clinic_id=clinic.id,
                institution_id=institution_id,
                station_number=1,
                name="Station 1 — Consultant A",
                station_type=StationType.CONSULTANT,
                room_number="201",
            ),
            ConsultationStation(
                clinic_id=clinic.id,
                institution_id=institution_id,
                station_number=2,
                name="Station 2 — Consultant B",
                station_type=StationType.CONSULTANT,
                room_number="202",
            ),
            ConsultationStation(
                clinic_id=clinic.id,
                institution_id=institution_id,
                station_number=3,
                name="Station 3 — Registrar",
                station_type=StationType.REGISTRAR,
                room_number="203",
            ),
        ]
    )
    print("Created clinic 'Burn Clinic' with 3 stations.")


DEMO_PATIENTS = [
    {
        "hospital_number": "MRN-100234",
        "full_name": "Grace Adeyemi",
        "date_of_birth": date(1959, 3, 12),
        "sex": "Female",
        "blood_group": "O+",
        "genotype": "AA",
        "weight_kg": 72.0,
        "height_cm": 162.0,
        "ward": "Male Medical Ward",
        "bed": "12",
        "primary_diagnosis": "Type 2 Diabetes Mellitus with foot ulcer",
        "allergies": "Penicillin",
    },
    {
        "hospital_number": "MRN-100517",
        "full_name": "Emeka Nwosu",
        "date_of_birth": date(1987, 11, 2),
        "sex": "Male",
        "blood_group": "A+",
        "genotype": "AS",
        "weight_kg": 68.0,
        "height_cm": 175.0,
        "ward": "Surgical Ward",
        "bed": "4",
        "primary_diagnosis": "Post-laparotomy, prolonged ileus",
        "allergies": None,
    },
]


def _seed_patients(db, institution_id: int) -> None:
    for spec in DEMO_PATIENTS:
        existing = db.scalar(
            select(Patient).where(
                Patient.hospital_number == spec["hospital_number"]
            )
        )
        if existing:
            print(f"Patient {spec['hospital_number']} already exists.")
            continue
        db.add(Patient(**spec, institution_id=institution_id))
        print(f"Created patient {spec['full_name']} ({spec['hospital_number']}).")


if __name__ == "__main__":
    seed()
