# services/backend/app/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# --- User Metrics ---
backend_user_registrations_total = Counter(
    "backend_user_registrations_total",
    "Total number of registered users"
)

backend_user_password_changes_total = Counter(
    "backend_user_password_changes_total",
    "Total number of password change attempts",
    ["status"] # "success", "failure"
)

backend_user_role_changes_total = Counter(
    "backend_user_role_changes_total",
    "Total number of user role changes",
    ["target_role"] # "booker", "moderator"
)

# --- Booking Metrics ---
backend_bookings_created_total = Counter(
    "backend_bookings_created_total",
    "Total number of successfully created bookings"
)

backend_bookings_creation_failures_total = Counter(
    "backend_bookings_creation_failures_total",
    "Total number of failed booking creation attempts",
    ["reason"] # "overlap", "unavailable", "validation_error", "not_found", "other"
)

backend_bookings_updated_total = Counter(
    "backend_bookings_updated_total",
    "Total number of updated bookings"
)

backend_bookings_cancelled_total = Counter(
    "backend_bookings_cancelled_total",
    "Total number of cancelled bookings"
)

backend_booking_duration_hours = Histogram(
    "backend_booking_duration_hours",
    "Histogram of booking durations in hours",
    buckets=[0.5, 1, 2, 3, 4, 6, 8, 12, 24, 48, 72, 168]
)

# --- Resource Management ---
backend_auditoriums_managed_total = Counter(
    "backend_auditoriums_managed_total",
    "Auditorium management operations",
    ["operation"] # "create", "update", "delete"
)

backend_equipment_managed_total = Counter(
    "backend_equipment_managed_total",
    "Equipment management operations",
    ["operation"] # "create", "update", "delete"
)

backend_availability_slots_managed_total = Counter(
    "backend_availability_slots_managed_total",
    "Availability slot management operations",
    ["operation"] # "create", "update", "delete"
)

# --- Views & Searches ---
backend_calendar_views_total = Counter(
    "backend_calendar_views_total",
    "Total number of auditorium calendar views"
)

backend_auditorium_searches_total = Counter(
    "backend_auditorium_searches_total",
    "Total number of auditorium searches/list views",
    ["filtered_by"] # "capacity", "equipment", "both", "none"
)