"""Shared calculations.

Everything else that used to live here (validate_email, sanitize_string,
generate_id, log_action, parse_date, is_valid_color, process_task_data, and the
constant block) had zero callers and was removed (F-014). Validation now lives in
validators.py, which is actually wired into the request path.
"""


def calculate_percentage(part, total):
    """Single owner of the percentage rule (F-011), previously inlined at 3 sites."""
    if not total:
        return 0
    return round((part / total) * 100, 2)
