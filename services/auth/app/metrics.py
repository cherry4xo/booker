# services/auth/app/metrics.py
from prometheus_client import Counter

# --- Auth Metrics ---
auth_logins_total = Counter(
    "auth_logins_total",
    "Total number of login attempts (access token request)",
    ["status"]  # Метки: "success", "failure"
)

auth_token_refreshes_total = Counter(
    "auth_token_refreshes_total",
    "Total number of token refresh attempts",
    ["status"]  # Метки: "success", "failure"
)

auth_token_validations_total = Counter(
    "auth_token_validations_total",
    "Total number of token validation requests",
    ["status"]  # Метки: "success", "failure"
)

# Счетчик для endpoint /refresh-token (если он имеет отдельный смысл)
# Если он делает то же, что и /access-token, можно использовать auth_logins_total
auth_refresh_token_logins_total = Counter(
    "auth_refresh_token_logins_total",
    "Total number of logins requesting only refresh token",
    ["status"] # Метки: "success", "failure"
)