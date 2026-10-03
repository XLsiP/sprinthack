from verify.base import VerificationResult


def test_verification_result_defaults():
    result = VerificationResult("verified", "NPPES")

    assert result.result == "verified"
    assert result.source == "NPPES"
    assert result.details == {}
    assert result.evidence_path is None


def test_verification_result_keeps_details_and_evidence_path():
    details = {"npi": "1234567893", "licenses": [{"license": "A1", "state": "IN"}]}
    result = VerificationResult("mismatch", "NPPES", details, "evidence/verification.pdf")

    assert result.result == "mismatch"
    assert result.details == details
    assert result.details is details
    assert result.evidence_path == "evidence/verification.pdf"


def test_verification_result_details_are_independent():
    first = VerificationResult("verified", "NPPES")
    second = VerificationResult("not_found", "NPPES")

    first.details["checked"] = True

    assert second.details == {}
