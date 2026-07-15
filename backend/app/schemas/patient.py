from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class PatientBase(BaseModel):
    hospital_number: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=150)
    date_of_birth: date | None = None
    sex: str | None = None
    phone: str | None = None
    blood_group: str | None = None
    genotype: str | None = None
    weight_kg: float | None = Field(default=None, gt=0, le=700)
    height_cm: float | None = Field(default=None, gt=0, le=300)
    ward: str | None = None
    bed: str | None = None
    primary_diagnosis: str | None = None
    allergies: str | None = None


class PatientCreate(PatientBase):
    """Payload to register a patient. institution comes from the token."""


class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int | None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def age(self) -> int | None:
        if self.date_of_birth is None:
            return None
        today = date.today()
        years = today.year - self.date_of_birth.year
        had_birthday = (today.month, today.day) >= (
            self.date_of_birth.month,
            self.date_of_birth.day,
        )
        return years - (0 if had_birthday else 1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def bmi(self) -> float | None:
        if not self.weight_kg or not self.height_cm:
            return None
        m = self.height_cm / 100
        return round(self.weight_kg / (m * m), 1)
