"""PII redaction: emails, phone numbers, addresses, profile links."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.security.pii import ADDRESS_TOKEN, EMAIL_TOKEN, LINK_TOKEN, PHONE_TOKEN, redact_pii


@pytest.mark.parametrize(
    "email", ["ananya.rao@krit.example", "first_last+tag@mail.co.in", "A.B@Sub.Domain.ORG"]
)
def test_emails_are_redacted(email):
    result = redact_pii(f"Contact: {email} for details")
    assert email not in result.text
    assert EMAIL_TOKEN in result.text and result.counts["email"] == 1


@pytest.mark.parametrize(
    "phone",
    ["+91 90000 12345", "9000054321", "+91-90000-67890", "091 9876543210", "98765 43210", "+919876543210", "0 98765 43210"],
)
def test_indian_mobile_numbers_are_redacted(phone):
    result = redact_pii(f"Phone: {phone}.")
    assert result.counts["phone"] == 1, phone
    assert PHONE_TOKEN in result.text
    assert not any(ch.isdigit() for ch in result.text.replace("Phone:", "")), result.text


@pytest.mark.parametrize(
    "text",
    ["CGPA: 7.8 (up to 6th semester)", "Class XII, 86 percent, 2023", "Solved 250+ problems", "2023 to 2027", "CTC 6.5 to 8.0 LPA", "Roll no 2023104512"],
)
def test_numbers_that_are_not_phones_are_kept(text):
    result = redact_pii(text)
    assert result.text == text and result.total == 0


@pytest.mark.parametrize(
    "line",
    [
        "Address: Flat 204, Lakeview Residency, 5th Cross, Vidyanagar, Mysuru, Karnataka 570017",
        "Permanent address - 12 Gandhi Road, Salem",
        "Residence: near the bus stand, Hosur",
        "No. 18, Temple Street, Gandhipuram, Coimbatore, Tamil Nadu 641012",
        "Plot 42, Sahakar Nagar, Near Ganesh Temple, Pune, Maharashtra 411009",
    ],
)
def test_address_lines_are_redacted(line):
    result = redact_pii(f"NAME\n{line}\nSKILLS: Python")
    assert result.counts["address"] == 1
    assert ADDRESS_TOKEN in result.text
    assert "SKILLS: Python" in result.text and "NAME" in result.text


def test_profile_links_are_redacted():
    result = redact_pii("LinkedIn: linkedin.example/in/ananya-rao-demo\nGitHub: https://github.com/someone/repo")
    assert result.counts["link"] == 2
    assert "ananya-rao-demo" not in result.text and "someone" not in result.text
    assert LINK_TOKEN in result.text


@pytest.mark.parametrize("filename", ["ananya_rao.txt", "karthik_subramani.txt", "sneha_kulkarni.txt"])
def test_demo_resumes_have_no_contact_details_left(filename):
    raw = (get_settings().data_dir / "resumes" / filename).read_text(encoding="utf-8")
    result = redact_pii(raw)
    assert "@" not in result.text
    assert "9000" not in result.text
    for fragment in ("570017", "641012", "411009", "Karnataka", "Tamil Nadu", "Maharashtra"):
        assert fragment not in result.text
    assert result.counts["email"] == 1 and result.counts["phone"] == 1 and result.counts["address"] == 1
    # The useful content survives.
    assert "SKILLS" in result.text or "TECHNICAL SKILLS" in result.text
    assert "PROJECTS" in result.text


def test_empty_input():
    result = redact_pii("")
    assert result.text == "" and result.total == 0
