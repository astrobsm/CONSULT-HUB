# Clinic Appointment Management Module (ConsultHUB Enterprise)

## Intelligent Timed Outpatient Clinic Appointment Scheduling System

This document is the product specification for the outpatient appointment module.
It sits **alongside** the inpatient/interdepartmental consultation workflow — the
two are distinct and must not overlap:

| Concern | Module | Core resource |
|---|---|---|
| Inpatient / interdepartmental **consult request** | Consultations | `Consultation` (FHIR ServiceRequest) |
| Outpatient **timed clinic appointment** | Appointments | `Appointment` (in a `Clinic` at a `ConsultationStation`) |

An outpatient appointment MAY link back to a consultation (e.g. a consult
recommends a follow-up clinic visit) via `Appointment.consultation_id`, but the
booking, slotting, and load-balancing logic is entirely separate.

---

## Overview

Enterprise-grade intelligent appointment scheduling integrated into ConsultHUB.
Coordinates all outpatient appointments across every department, specialty and
subspecialty while ensuring: no double booking, even patient distribution,
configurable consultation stations, reduced waiting time, better clinic workflow,
AI-assisted scheduling, and a complete audit trail.

## Objectives

Digitize outpatient booking; eliminate overcrowding; reduce waiting time; prevent
conflicts; balance workload; optimize rooms; improve patient & staff satisfaction;
generate analytics; integrate with ConsultHUB.

## Clinic structure

Institution → Department → Specialty → Subspecialty → Clinic → Clinic Day →
Consultation Stations → Healthcare Workers → Appointments.

## Clinic configuration

Each clinic defines: name, department, subspecialty, location, consultation rooms,
consultation stations, operating days, operating hours, maximum patients,
consultation duration, break times, and slot mixes (emergency / priority /
follow-up / new-patient / telemedicine).

## Consultation stations

Each clinic registers unlimited stations. Each station has: number, name, assigned
staff, room number, maximum patients, available time, consultation duration, and a
status (active / inactive / maintenance). Station types include consultant,
registrar, medical officer, resident, nurse practitioner, dietician, physiotherapy,
psychology, occupational therapy, social welfare, telemedicine, procedure, review,
and emergency walk-in.

## Slot generation

The system generates appointment slots per station from the clinic's operating
hours and the configured consultation duration (10 / 15 / 20 / 30 / 45 / 60 min),
skipping break windows. Each station maintains its own independent schedule.

## Intelligent load balancing (mandatory)

Appointments must be evenly distributed across all active stations — the difference
in booking counts should never exceed one patient unless overridden.
- **Least-busy**: always assign to the active station with the fewest bookings.
- **Round-robin**: rotate across stations.
- **AI (future)**: weigh consultant experience, complexity, duration, patient type.

## Duplicate prevention (critical)

The system MUST NEVER permit the same appointment time to be booked twice for the
same station. A second attempt is rejected immediately with
"This appointment slot is no longer available." — enforced at the database level.

## Real-time slot locking

When booking starts, the slot is locked temporarily (2–5 minutes, configurable).
If the booking is abandoned, the lock is released automatically.

## Appointment types

New patient, review, follow-up, postoperative, procedure, telemedicine, emergency,
walk-in, priority, VIP, staff, insurance, private.

## Booking workflow

Search patient → select clinic → select date → select appointment type → system
calculates the best station → displays available times → patient selects time →
system locks slot → confirm → appointment number generated → notification sent →
calendar updated.

## Auto-assignment & manual override

System assigns station, consultant, room, queue position, estimated waiting time,
QR code. Clinic administrators can change station, move appointments, merge
schedules, increase capacity, add/block stations, and cancel clinics.

## Lifecycle & queue

Statuses: booked, confirmed, checked-in, waiting, called, consultation started,
completed, did not attend, cancelled, rescheduled, referred, admitted, discharged.
QR check-in updates the live queue (waiting number, current station, estimated
wait). Rescheduling preserves history and re-balances workload.

## Waiting list

If a clinic is full, the patient joins the waiting list; on cancellation the system
automatically offers the slot to the next eligible patient.

## Reminders & self-booking (future)

SMS / email / WhatsApp / push / voice reminders at 7d / 3d / 24h / 2h / 30m. A
future patient portal supports self-booking, cancellation, rescheduling, referral
upload, questionnaires, online payment, and directions.

## AI features (future)

Appointment optimizer (no-show prediction, overbooking), wait-time prediction,
capacity planning, smart rescheduling, patient navigation, voice booking, and
clinical prioritization (cancer / stroke / trauma / burns / children / pregnancy).

## Analytics

Attendance, no-show rate, average waiting time, consultation duration, consultant
productivity, station utilization, peak hours, satisfaction, revenue, trends,
capacity utilization, referral sources.

## Integration

Patient registration, consult requests, EMR, radiology, laboratory, billing,
pharmacy, theatre scheduling, ward admission, telemedicine, research registry,
hospital analytics.

---

## Implementation status in this repo

**Implemented (backend + UI, verified):**
- Configurable clinics and unlimited consultation stations (admin-managed).
- Per-station slot generation from operating hours / duration, skipping breaks and
  non-operating weekdays.
- Load-balanced auto-assignment (least-busy; round-robin configurable).
- **Database-guaranteed no double-booking** — a partial unique index on
  (station, slot) over active statuses; conflicting bookings get a 409.
- Real-time slot **holds** with expiry (temporary lock during booking).
- Appointment lifecycle (book → confirm → check-in/queue → called → in-progress →
  completed / DNA / cancelled / rescheduled), tenant-scoped, with an audit of the
  booking user and timestamps.
- Notifications on booking / reschedule / cancellation (reuses the notification
  system) and an optional link to an inpatient `Consultation`.

**Deferred (noted for later):** waiting-list auto-promotion, QR codes, SMS/WhatsApp
reminders, the patient self-booking portal, all AI features, and advanced analytics
beyond the basic clinic dashboard.
