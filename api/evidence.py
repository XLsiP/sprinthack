"""Generate PDF evidence files for saved verification records."""
import json
from html import escape
from pathlib import Path

from models import Verification

EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"


def _render_pdf(document: str, output_path: Path) -> None:
    from weasyprint import HTML

    HTML(string=document).write_pdf(output_path)


def generate_evidence_pdf(verification: Verification) -> Path:
    """Render and save a PDF for a verification, returning its path."""
    associate = verification.credential.associate
    credential = verification.credential
    credential_type = credential.credential_type
    details = json.dumps(verification.details or {}, indent=2, sort_keys=True, default=str)
    values = {
        "Associate": associate.name,
        "NPI": associate.npi or "Not provided",
        "Credential": credential_type.name,
        "Credential number": credential.number or "Not provided",
        "Source": verification.source,
        "Checked at (UTC)": verification.checked_at.isoformat() + "Z",
        "Result": verification.result,
    }
    rows = "".join(
        "<tr><th>%s</th><td>%s</td></tr>" % (escape(label), escape(value))
        for label, value in values.items()
    )
    document = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <style>
      @page { size: letter; margin: 0.75in; }
      body { color: #17212b; font: 11pt sans-serif; }
      h1 { color: #173b57; font-size: 20pt; }
      table { border-collapse: collapse; width: 100%%; }
      th, td { border-bottom: 1px solid #d5dde4; padding: 8px; text-align: left; }
      th { color: #425466; width: 30%%; }
      pre { background: #f3f6f8; padding: 12px; white-space: pre-wrap; overflow-wrap: anywhere; }
    </style>
  </head>
  <body>
    <h1>Credential Verification Evidence</h1>
    <table>%s</table>
    <h2>Verification details</h2>
    <pre>%s</pre>
  </body>
</html>
""" % (rows, escape(details))

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EVIDENCE_DIR / ("verification-%d.pdf" % verification.id)
    _render_pdf(document, output_path)
    verification.evidence_path = str(output_path)
    return output_path
