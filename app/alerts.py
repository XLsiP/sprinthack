"""Expiration tracking: status buckets and who to alert.

Run `python -m app.alerts` to print the alerts that would be sent today.
"""
from datetime import date

from . import db

CRITICAL_DAYS = 30
WARNING_DAYS = 90


def status_for(expires_on, today=None):
    """Return (status, days_left) for an ISO expiration date."""
    today = today or date.today()
    days_left = (date.fromisoformat(expires_on) - today).days
    if days_left < 0:
        return "expired", days_left
    if days_left <= CRITICAL_DAYS:
        return "critical", days_left
    if days_left <= WARNING_DAYS:
        return "warning", days_left
    return "ok", days_left


def list_credentials(conn, today=None):
    rows = conn.execute(
        """
        SELECT c.*, s.name AS staff_name, s.role AS staff_role,
               s.email AS staff_email, s.manager_email
        FROM credentials c JOIN staff s ON s.id = c.staff_id
        ORDER BY c.expires_on
        """
    ).fetchall()
    out = []
    for row in rows:
        cred = dict(row)
        cred["status"], cred["days_left"] = status_for(cred["expires_on"], today)
        out.append(cred)
    return out


def build_alerts(conn, within_days=WARNING_DAYS, today=None):
    """Credentials that are expired or expire within `within_days`, with recipients."""
    alerts = []
    for cred in list_credentials(conn, today):
        if cred["days_left"] > within_days:
            continue
        if cred["days_left"] < 0:
            when = "expired %d days ago" % -cred["days_left"]
        else:
            when = "expires in %d days" % cred["days_left"]
        alerts.append(
            {
                "credential_id": cred["id"],
                "status": cred["status"],
                "recipients": [e for e in (cred["staff_email"], cred["manager_email"]) if e],
                "message": "%s: %s %s (%s)"
                % (cred["staff_name"], cred["type"], when, cred["expires_on"]),
            }
        )
    return alerts


def send(alert):
    # TODO: replace with real delivery (SMTP, Slack webhook, SMS...)
    print("[%s] to %s: %s" % (alert["status"].upper(), ", ".join(alert["recipients"]) or "nobody", alert["message"]))


if __name__ == "__main__":
    db.init_db()
    conn = db.connect()
    for alert in build_alerts(conn):
        send(alert)
