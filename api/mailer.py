"""Email delivery for alerts through the Resend HTTP API.

With no RESEND_API_KEY nothing is sent and every alert stays in the outbox. With a key, each
recipient gets one digest email per sweep listing their newly due alerts.

Environment:
  RESEND_API_KEY           Enables sending.
  ALERT_EMAIL_FROM         Sender. Default is Resend's test sender.
  ALERT_EMAIL_OVERRIDE_TO  Send every digest to this one address instead (demo / testing).
  ALERT_EMAIL_MAX_PER_RUN  Most emails per sweep. Default 10; the rest stay in the outbox.
  APP_URL                  Base URL for links in the email. Default http://localhost:3000.
  RESEND_API_URL           Resend endpoint; only changed in tests.
"""
import logging
import os
import time
from collections import Counter
from html import escape

import httpx

from models import Alert, Credential

log = logging.getLogger(__name__)

DEFAULT_FROM = "Credentialing Tracker <onboarding@resend.dev>"
DEFAULT_API_URL = "https://api.resend.com/emails"
PACE_SECONDS = 0.6  # Resend allows about two requests a second
MAX_ROWS = 50  # rows listed in one digest; the rest are summarized
# Addresses that can never receive mail (RFC 2606 / 6761). Seed data uses example.org.
RESERVED_DOMAINS = {"example.org", "example.com", "example.net", "localhost"}
RESERVED_TLDS = {"test", "example", "invalid", "localhost"}

# Most urgent first, with the label and the status color used across the app.
THRESHOLDS = {
    "excluded": ("On the OIG exclusion list", "#b91c1c"),
    "expired": ("Expired", "#b91c1c"),
    "30": ("Expires within 30 days", "#c2410c"),
    "60": ("Expires within 60 days", "#a16207"),
    "90": ("Expires within 90 days", "#a16207"),
}

Item = tuple[Alert, Credential]


def is_configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY", "").strip())


def is_reserved(address: str) -> bool:
    domain = address.rsplit("@", 1)[-1].strip().lower()
    if domain.rsplit(".", 1)[-1] in RESERVED_TLDS:
        return True
    return any(domain == reserved or domain.endswith("." + reserved) for reserved in RESERVED_DOMAINS)


def render_digest(recipient: str, items: list[Item], override: bool = False) -> tuple[str, str]:
    """Subject and HTML body for one recipient's newly due alerts, most urgent first."""
    app_url = os.environ.get("APP_URL", "http://localhost:3000").rstrip("/")
    order = list(THRESHOLDS)
    items = sorted(items, key=lambda item: (order.index(item[0].threshold), item[1].associate.name))
    count = len(items)
    subject = "Credential alert: %d credential%s need%s attention" % (
        count, "" if count == 1 else "s", "s" if count == 1 else ""
    )
    if override:
        subject += " (for %s)" % recipient

    cell = 'style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:left"'
    rows = []
    for alert, credential in items[:MAX_ROWS]:
        label, color = THRESHOLDS[alert.threshold]
        expires = credential.expires_date.isoformat() if credential.expires_date else "Does not expire"
        rows.append(
            "<tr>"
            '<td %s><a href="%s/associates/%d" style="color:#1d4ed8">%s</a><br>'
            '<span style="color:#6b7280;font-size:12px">%s · %s</span></td>'
            "<td %s>%s</td>"
            '<td %s><strong style="color:%s">%s</strong></td>'
            "<td %s>%s</td>"
            "</tr>"
            % (
                cell, app_url, credential.associate_id, escape(credential.associate.name),
                escape(credential.associate.department), escape(credential.associate.facility),
                cell, escape(credential.credential_type.name),
                cell, color, label,
                cell, expires,
            )
        )
    more = (
        '<p style="color:#6b7280">And %d more. <a href="%s" style="color:#1d4ed8">Open the dashboard</a> '
        "to see them all.</p>" % (count - MAX_ROWS, app_url)
        if count > MAX_ROWS else ""
    )
    intended = (
        '<p style="color:#6b7280;font-size:12px">Test delivery. Intended recipient: %s</p>' % escape(recipient)
        if override else ""
    )
    html = (
        '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#111827;max-width:720px">'
        "%s"
        '<h2 style="margin:0 0 4px">Credentials needing attention</h2>'
        '<p style="margin:0 0 16px;color:#374151">%d credential%s reached an alert threshold.</p>'
        '<table style="border-collapse:collapse;width:100%%;font-size:14px">'
        "<thead><tr><th %s>Associate</th><th %s>Credential</th><th %s>Alert</th><th %s>Expires</th></tr></thead>"
        "<tbody>%s</tbody></table>"
        "%s"
        '<p style="margin-top:24px;color:#6b7280;font-size:12px">Sent by the Credentialing Tracker. '
        "Each alert is sent once per credential and threshold.</p>"
        "</div>"
    ) % (intended, count, "" if count == 1 else "s", cell, cell, cell, cell, "".join(rows), more)
    return subject, html


def send(to: str, subject: str, html: str) -> None:
    """Send one email through Resend. Raises httpx.HTTPError on any failure."""
    response = httpx.post(
        os.environ.get("RESEND_API_URL", DEFAULT_API_URL),
        headers={"Authorization": "Bearer %s" % os.environ["RESEND_API_KEY"].strip()},
        json={
            "from": os.environ.get("ALERT_EMAIL_FROM", DEFAULT_FROM),
            "to": [to],
            "subject": subject,
            "html": html,
        },
        timeout=10,
    )
    response.raise_for_status()


def deliver(items: list[Item], hr_email: str) -> dict[str, int]:
    """Email each recipient a digest of their new alerts and mark those rows `channel="email"`.

    Returns how many alert rows ended up in each channel. Anything not emailed (no API key, reserved
    test address, over the per-run cap, or a failed send) stays in the outbox, so nothing is lost.
    """
    by_recipient: dict[str, list[Item]] = {}
    for item in items:
        by_recipient.setdefault(item[0].sent_to, []).append(item)

    if is_configured():
        override_to = os.environ.get("ALERT_EMAIL_OVERRIDE_TO", "").strip()
        remaining = int(os.environ.get("ALERT_EMAIL_MAX_PER_RUN", "10"))
        # HR first, then the managers with the most to act on.
        recipients = sorted(by_recipient, key=lambda r: (r != hr_email, -len(by_recipient[r]), r))
        for recipient in recipients:
            if remaining <= 0:
                break
            if not override_to and is_reserved(recipient):
                continue
            remaining -= 1  # failed attempts count too, so one sweep is always bounded
            subject, html = render_digest(recipient, by_recipient[recipient], override=bool(override_to))
            try:
                send(override_to or recipient, subject, html)
            except httpx.HTTPError as exc:
                log.warning("Alert email for %s failed and stays in the outbox: %s", recipient, type(exc).__name__)
                continue
            for alert, _ in by_recipient[recipient]:
                alert.channel = "email"
            if remaining > 0:
                time.sleep(PACE_SECONDS)

    channels = Counter(alert.channel for alert, _ in items)
    return {"email": channels["email"], "outbox": channels["outbox"]}


def render_credential_contact(credential: Credential, follow_up: bool, override: bool = False) -> tuple[str, str]:
    """Subject and HTML body for an individual credential-expiry notice."""
    app_url = os.environ.get("APP_URL", "http://localhost:3000").rstrip("/")
    associate = escape(credential.associate.name)
    credential_name = escape(credential.credential_type.name)
    expires = credential.expires_date.isoformat() if credential.expires_date else "Does not expire"
    subject = "%s: %s credential %s" % (
        "Follow-up" if follow_up else "Credential expiring",
        associate,
        "requires attention" if follow_up else "is approaching expiry",
    )
    intended = (
        '<p style="color:#6b7280;font-size:12px">Test delivery. Intended recipient: %s</p>'
        % escape(credential.associate.manager_email)
        if override else ""
    )
    html = (
        '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#111827">'
        "%s"
        "<p>Hello,</p>"
        "<p>This is a %s regarding <strong>%s</strong>'s %s credential, which expires on %s.</p>"
        '<p><a href="%s/associates/%d" style="color:#1d4ed8">View credential details</a></p>'
        "<p>Credentialing Tracker</p>"
        "</div>"
    ) % (
        intended,
        "follow-up" if follow_up else "notification",
        associate,
        credential_name,
        escape(expires),
        app_url,
        credential.associate_id,
    )
    return subject, html


def deliver_credential_contact(credential: Credential, follow_up: bool) -> str:
    """Send an individual notice or leave it in the outbox when delivery is unavailable."""
    recipient = credential.associate.manager_email
    override_to = os.environ.get("ALERT_EMAIL_OVERRIDE_TO", "").strip()
    if not is_configured() or (not override_to and is_reserved(recipient)):
        return "outbox"

    subject, html = render_credential_contact(credential, follow_up, override=bool(override_to))
    try:
        send(override_to or recipient, subject, html)
    except httpx.HTTPError as exc:
        log.warning("Credential contact for %s failed and stays in the outbox: %s", recipient, type(exc).__name__)
        return "outbox"
    return "email"
