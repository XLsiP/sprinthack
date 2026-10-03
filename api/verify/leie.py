"""REAL: OIG LEIE exclusion lookup against a local CSV download.

Place the current UPDATED.csv file in api/data/. It is loaded once per process
and should be refreshed by deployment or operations procedures.
"""
import csv
from functools import lru_cache
from pathlib import Path
from typing import Optional

from models import Associate, Credential
from verify.base import VerificationResult

LEIE_CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "UPDATED.csv"
REQUIRED_COLUMNS = {"FIRSTNAME", "LASTNAME", "NPI", "EXCLTYPE", "EXCLDATE"}


@lru_cache(maxsize=1)
def load_leie_records() -> tuple[dict[str, str], ...]:
    """Read and cache the current LEIE CSV; missing or invalid files raise explicitly."""
    with LEIE_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        columns = set(reader.fieldnames or ())
        missing_columns = REQUIRED_COLUMNS - columns
        if missing_columns:
            raise ValueError("LEIE CSV is missing required columns: %s" % ", ".join(sorted(missing_columns)))
        return tuple(
            {key: value or "" for key, value in row.items() if key is not None}
            for row in reader
        )


def _norm(value: Optional[str]) -> str:
    return "".join(character for character in (value or "").upper() if character.isalnum())


def _usable_npi(value: Optional[str]) -> str:
    npi = _norm(value)
    return npi if len(npi) == 10 and npi != "0000000000" else ""


def _name_matches(associate_name: str, row: dict[str, str]) -> bool:
    parts = [_norm(part) for part in associate_name.split() if _norm(part)]
    if len(parts) < 2:
        return False
    return parts[0] == _norm(row.get("FIRSTNAME")) and parts[-1] == _norm(row.get("LASTNAME"))


def _find_match(
    associate: Associate, records: tuple[dict[str, str], ...]
) -> tuple[Optional[dict[str, str]], Optional[str], bool]:
    associate_npi = _usable_npi(associate.npi)
    name_mismatch = False
    for row in records:
        matches_name = _name_matches(associate.name, row)
        row_npi = _usable_npi(row.get("NPI"))
        if associate_npi and row_npi:
            if associate_npi == row_npi:
                if matches_name:
                    return row, "name_and_npi", False
                name_mismatch = True
            continue

        if matches_name:
            return row, "name_only", False

    return None, None, name_mismatch


class LeieVerifier:
    source = "OIG LEIE"

    def verify(self, associate: Associate, credential: Credential) -> VerificationResult:
        try:
            records = load_leie_records()
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            return VerificationResult(
                "error",
                self.source,
                {"reason": "Unable to load LEIE CSV: %s" % exc, "csv_path": str(LEIE_CSV_PATH)},
            )

        match, matched_by, npi_name_mismatch = _find_match(associate, records)
        if match is not None:
            details = {
                "matched_by": matched_by,
                "exclusion_type": match.get("EXCLTYPE") or None,
                "exclusion_date": match.get("EXCLDATE") or None,
            }
            if matched_by == "name_only":
                details["match_warning"] = "Matched by name because a usable NPI was unavailable"
            return VerificationResult("excluded", self.source, details)

        if npi_name_mismatch:
            return VerificationResult(
                "mismatch",
                self.source,
                {"reason": "LEIE NPI matches but the listed name does not match the associate"},
            )
        return VerificationResult("verified", self.source, {"source_status": "No exclusion found"})
