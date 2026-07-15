"""Idempotent dev seed: one institution, an admin, and a registrar.

Run from the backend directory:

    python -m app.seed
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.entities import Department, Institution, User

# Import models so all tables register before create_all.
import app.models  # noqa: F401

DEMO_INSTITUTION_CODE = "DEMO"
DEMO_USERS = [
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
            print(f"Created institution '{institution.name}' with 3 departments.")
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
                    institution_id=institution.id,
                )
            )
            print(f"Created user {spec['email']} (password: {spec['password']}).")

        db.commit()
        print("\nSeed complete. Log in with admin@consulthub.local / consulthub")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
