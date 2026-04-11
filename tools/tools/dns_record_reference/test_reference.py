"""
Tests for DNS Record Reference & Validator.

These tests ARE the spec -- if an LLM regenerates the tool in any
language, these cases define correctness.
"""

import subprocess
import sys

import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from reference import (
    get_record_type,
    list_record_types,
    search_record_types,
    validate_spf,
    validate_dkim,
    validate_dmarc,
    validate_a,
    validate_mx,
    validate_tlsa,
    validate_record,
    ValidationResult,
    generate_a,
    generate_aaaa,
    generate_mx,
    generate_spf,
    generate_dmarc,
    generate_ptr,
    explain_record,
)


# ============================================================
# 1. Registry — record type lookup
# ============================================================

class TestRegistry:
    def test_a_record(self):
        rt = get_record_type("A")
        assert rt is not None
        assert rt.code == 1
        assert "IPv4" in rt.description

    def test_aaaa_record(self):
        rt = get_record_type("AAAA")
        assert rt is not None
        assert rt.code == 28

    def test_cname_record(self):
        rt = get_record_type("CNAME")
        assert rt is not None
        assert "alias" in rt.description.lower()

    def test_mx_record(self):
        rt = get_record_type("MX")
        assert rt is not None
        assert "mail" in rt.description.lower()

    def test_txt_record(self):
        rt = get_record_type("TXT")
        assert rt is not None
        assert rt.code == 16

    def test_srv_record(self):
        rt = get_record_type("SRV")
        assert rt is not None
        assert "service" in rt.description.lower()

    def test_soa_record(self):
        rt = get_record_type("SOA")
        assert rt is not None

    def test_ns_record(self):
        rt = get_record_type("NS")
        assert rt is not None

    def test_ptr_record(self):
        rt = get_record_type("PTR")
        assert rt is not None

    def test_caa_record(self):
        rt = get_record_type("CAA")
        assert rt is not None
        assert rt.code == 257

    def test_tlsa_record(self):
        rt = get_record_type("TLSA")
        assert rt is not None
        assert rt.code == 52

    def test_case_insensitive(self):
        assert get_record_type("a") is not None
        assert get_record_type("Mx") is not None

    def test_unknown(self):
        assert get_record_type("UNKNOWN") is None

    def test_list_all(self):
        types = list_record_types()
        assert len(types) >= 12

    def test_list_common(self):
        common = list_record_types(common_only=True)
        assert all(rt.common for rt in common)

    def test_list_by_category(self):
        addr = list_record_types(category="address")
        assert all(rt.category == "address" for rt in addr)
        assert len(addr) >= 2

    def test_search_mail(self):
        results = search_record_types("mail")
        assert any(rt.name == "MX" for rt in results)

    def test_search_ipv4(self):
        results = search_record_types("IPv4")
        assert any(rt.name == "A" for rt in results)

    def test_search_no_results(self):
        assert len(search_record_types("xyznonexistent")) == 0

    def test_all_types_have_examples(self):
        for rt in list_record_types():
            assert rt.examples, f"{rt.name} has no examples"


# ============================================================
# 2. SPF Validator
# ============================================================

class TestSPFValid:
    def test_minimal(self):
        r = validate_spf("v=spf1 -all")
        assert r.valid
        assert r.parsed["mechanisms"][0]["mechanism"] == "all"
        assert r.parsed["mechanisms"][0]["qualifier"] == "-"

    def test_google(self):
        r = validate_spf("v=spf1 include:_spf.google.com ~all")
        assert r.valid
        assert r.parsed["dns_lookups"] == 1

    def test_complex(self):
        r = validate_spf(
            "v=spf1 ip4:192.168.1.0/24 ip4:10.0.0.1 "
            "include:_spf.google.com include:sendgrid.net a mx -all"
        )
        assert r.valid
        assert r.parsed["dns_lookups"] == 4

    def test_softfail(self):
        r = validate_spf("v=spf1 ~all")
        assert r.valid

    def test_neutral(self):
        r = validate_spf("v=spf1 ?all")
        assert r.valid

    def test_pass(self):
        r = validate_spf("v=spf1 +all")
        assert r.valid

    def test_redirect(self):
        r = validate_spf("v=spf1 redirect=_spf.example.com")
        assert r.valid
        assert r.parsed["modifiers"]["redirect"] == "_spf.example.com"

    def test_ip6(self):
        r = validate_spf("v=spf1 ip6:2001:db8::1 -all")
        assert r.valid

    def test_quoted(self):
        r = validate_spf('"v=spf1 -all"')
        assert r.valid

    def test_ip4_cidr(self):
        r = validate_spf("v=spf1 ip4:192.168.1.0/24 -all")
        assert r.valid


class TestSPFInvalid:
    def test_no_version(self):
        r = validate_spf("include:example.com -all")
        assert not r.valid

    def test_wrong_version(self):
        r = validate_spf("v=spf2 -all")
        assert not r.valid

    def test_unknown_mechanism(self):
        r = validate_spf("v=spf1 bogus -all")
        assert not r.valid

    def test_invalid_ip4(self):
        r = validate_spf("v=spf1 ip4:999.999.999.999 -all")
        assert not r.valid

    def test_invalid_ip6(self):
        r = validate_spf("v=spf1 ip6:not-an-ipv6 -all")
        assert not r.valid

    def test_include_no_domain(self):
        r = validate_spf("v=spf1 include: -all")
        assert not r.valid

    def test_ip4_no_arg(self):
        r = validate_spf("v=spf1 ip4 -all")
        assert not r.valid

    def test_too_many_lookups(self):
        includes = " ".join(f"include:spf{i}.example.com" for i in range(11))
        r = validate_spf(f"v=spf1 {includes} -all")
        assert not r.valid
        assert any("Too many" in e for e in r.errors)

    def test_ip4_invalid_cidr(self):
        r = validate_spf("v=spf1 ip4:192.168.1.0/33 -all")
        assert not r.valid

    def test_all_with_arg(self):
        r = validate_spf("v=spf1 all:foo")
        assert not r.valid


class TestSPFRedirectCounting:
    """SPF redirect modifier counts as a DNS lookup per RFC 7208 Section 4.6.4."""

    def test_redirect_counts_as_lookup(self):
        r = validate_spf("v=spf1 redirect=_spf.example.com")
        assert r.valid
        assert r.parsed["dns_lookups"] == 1

    def test_redirect_plus_includes_counted(self):
        includes = " ".join(f"include:spf{i}.example.com" for i in range(9))
        r = validate_spf(f"v=spf1 {includes} redirect=_spf.other.com")
        # 9 includes + 1 redirect = 10 lookups (at the limit)
        assert r.valid
        assert r.parsed["dns_lookups"] == 10

    def test_redirect_pushes_over_limit(self):
        includes = " ".join(f"include:spf{i}.example.com" for i in range(10))
        r = validate_spf(f"v=spf1 {includes} redirect=_spf.other.com")
        # 10 includes + 1 redirect = 11 lookups (over the limit)
        assert not r.valid
        assert any("Too many" in e for e in r.errors)


class TestSPFWarnings:
    def test_ptr_discouraged(self):
        r = validate_spf("v=spf1 ptr -all")
        assert r.valid
        assert any("discouraged" in w.lower() for w in r.warnings)

    def test_all_not_last(self):
        r = validate_spf("v=spf1 -all include:example.com")
        assert any("last" in w.lower() for w in r.warnings)

    def test_no_all_no_redirect(self):
        r = validate_spf("v=spf1 include:example.com")
        assert any("no 'all'" in w.lower() for w in r.warnings)


# ============================================================
# 3. DKIM Validator
# ============================================================

class TestDKIMValid:
    def test_minimal(self):
        r = validate_dkim("v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ==")
        assert r.valid

    def test_without_version(self):
        r = validate_dkim("k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ==")
        assert r.valid

    def test_ed25519(self):
        r = validate_dkim("v=DKIM1; k=ed25519; p=base64keydata==")
        assert r.valid
        assert r.parsed["key_type"] == "ed25519"

    def test_quoted(self):
        r = validate_dkim('"v=DKIM1; k=rsa; p=MIGfMA0GCS=="')
        assert r.valid


class TestDKIMInvalid:
    def test_wrong_version(self):
        r = validate_dkim("v=DKIM2; p=key==")
        assert not r.valid

    def test_no_key(self):
        r = validate_dkim("v=DKIM1; k=rsa")
        assert not r.valid

    def test_invalid_key_type(self):
        r = validate_dkim("v=DKIM1; k=dsa; p=key==")
        assert not r.valid

    def test_invalid_base64(self):
        r = validate_dkim("v=DKIM1; k=rsa; p=!!!not-base64!!!")
        assert not r.valid

    def test_invalid_hash(self):
        r = validate_dkim("v=DKIM1; k=rsa; h=md5; p=key==")
        assert not r.valid


class TestDKIMRevoked:
    def test_empty_key(self):
        r = validate_dkim("v=DKIM1; p=")
        assert r.valid
        assert r.parsed.get("revoked") is True

    def test_testing_flag(self):
        r = validate_dkim("v=DKIM1; k=rsa; t=y; p=MIGfMA0GCS==")
        assert r.valid
        assert any("testing" in w.lower() for w in r.warnings)


# ============================================================
# 4. DMARC Validator
# ============================================================

class TestDMARCValid:
    def test_minimal(self):
        r = validate_dmarc("v=DMARC1; p=none")
        assert r.valid
        assert r.parsed["policy"] == "none"

    def test_reject(self):
        r = validate_dmarc("v=DMARC1; p=reject")
        assert r.valid

    def test_quarantine(self):
        r = validate_dmarc("v=DMARC1; p=quarantine")
        assert r.valid

    def test_full(self):
        r = validate_dmarc(
            "v=DMARC1; p=reject; sp=quarantine; "
            "rua=mailto:dmarc@example.com; ruf=mailto:forensics@example.com; "
            "adkim=s; aspf=r; pct=100; fo=1"
        )
        assert r.valid
        assert r.parsed["policy"] == "reject"
        assert r.parsed["subdomain_policy"] == "quarantine"
        assert r.parsed["adkim"] == "s"
        assert r.parsed["aspf"] == "r"
        assert r.parsed["pct"] == 100


class TestDMARCInvalid:
    def test_no_version(self):
        r = validate_dmarc("p=reject")
        assert not r.valid

    def test_wrong_version(self):
        r = validate_dmarc("v=DMARC2; p=reject")
        assert not r.valid

    def test_no_policy(self):
        r = validate_dmarc("v=DMARC1")
        assert not r.valid

    def test_invalid_policy(self):
        r = validate_dmarc("v=DMARC1; p=block")
        assert not r.valid

    def test_invalid_rua(self):
        r = validate_dmarc("v=DMARC1; p=none; rua=http://example.com")
        assert not r.valid

    def test_invalid_pct(self):
        r = validate_dmarc("v=DMARC1; p=none; pct=200")
        assert not r.valid

    def test_invalid_adkim(self):
        r = validate_dmarc("v=DMARC1; p=none; adkim=x")
        assert not r.valid

    def test_v_not_first(self):
        r = validate_dmarc("p=reject; v=DMARC1")
        assert not r.valid


class TestDMARCWarnings:
    def test_none_policy(self):
        r = validate_dmarc("v=DMARC1; p=none")
        assert any("monitor" in w.lower() for w in r.warnings)

    def test_no_rua(self):
        r = validate_dmarc("v=DMARC1; p=reject")
        assert any("rua" in w.lower() for w in r.warnings)

    def test_partial_pct(self):
        r = validate_dmarc("v=DMARC1; p=reject; pct=50; rua=mailto:a@b.com")
        assert any("50%" in w for w in r.warnings)


# ============================================================
# 5. A Record Validator
# ============================================================

class TestValidateA:
    def test_valid(self):
        r = validate_a("93.184.216.34")
        assert r.valid

    def test_private(self):
        r = validate_a("192.168.1.1")
        assert r.valid
        assert any("private" in w.lower() for w in r.warnings)

    def test_loopback(self):
        r = validate_a("127.0.0.1")
        assert r.valid
        assert any("loopback" in w.lower() for w in r.warnings)

    def test_invalid(self):
        r = validate_a("not-an-ip")
        assert not r.valid

    def test_out_of_range(self):
        r = validate_a("256.1.1.1")
        assert not r.valid


# ============================================================
# 6. MX Record Validator
# ============================================================

class TestValidateMX:
    def test_valid(self):
        r = validate_mx("10 mail.example.com.")
        assert r.valid
        assert r.parsed["priority"] == 10

    def test_null_mx(self):
        r = validate_mx("0 .")
        assert r.valid
        assert any("does not accept" in w.lower() or "null" in w.lower()
                    for w in r.warnings)

    def test_missing_server(self):
        r = validate_mx("10")
        assert not r.valid

    def test_ip_rejected(self):
        r = validate_mx("10 192.168.1.1")
        assert not r.valid


# ============================================================
# 6b. TLSA Validator
# ============================================================

class TestTLSAValid:
    def test_dane_ee_sha256(self):
        r = validate_tlsa("3 1 1 " + "a" * 64)
        assert r.valid
        assert r.parsed["usage"] == 3
        assert r.parsed["selector"] == 1
        assert r.parsed["matching_type"] == 1

    def test_ca_constraint(self):
        r = validate_tlsa("0 0 1 " + "b" * 64)
        assert r.valid
        assert r.parsed["usage"] == 0

    def test_full_cert(self):
        r = validate_tlsa("1 0 0 " + "c" * 100)
        assert r.valid
        assert r.parsed["matching_type"] == 0

    def test_sha512(self):
        r = validate_tlsa("3 1 2 " + "d" * 128)
        assert r.valid
        assert r.parsed["matching_type"] == 2


class TestTLSAInvalid:
    def test_too_few_fields(self):
        r = validate_tlsa("3 1")
        assert not r.valid

    def test_invalid_usage(self):
        r = validate_tlsa("5 1 1 " + "a" * 64)
        assert not r.valid

    def test_invalid_selector(self):
        r = validate_tlsa("3 5 1 " + "a" * 64)
        assert not r.valid

    def test_invalid_matching_type(self):
        r = validate_tlsa("3 1 5 " + "a" * 64)
        assert not r.valid

    def test_invalid_hex_data(self):
        r = validate_tlsa("3 1 1 not-hex-data!")
        assert not r.valid


class TestTLSAWarnings:
    def test_sha256_wrong_length(self):
        r = validate_tlsa("3 1 1 " + "a" * 32)
        assert r.valid
        assert any("64 hex" in w for w in r.warnings)

    def test_sha512_wrong_length(self):
        r = validate_tlsa("3 1 2 " + "a" * 64)
        assert r.valid
        assert any("128 hex" in w for w in r.warnings)

    def test_dane_ee_rotation_warning(self):
        r = validate_tlsa("3 1 1 " + "a" * 64)
        assert any("rotating" in w.lower() for w in r.warnings)


# ============================================================
# 7. Unified validate_record
# ============================================================

class TestValidateRecord:
    def test_spf(self):
        r = validate_record("SPF", "v=spf1 -all")
        assert r.valid

    def test_dkim(self):
        r = validate_record("DKIM", "v=DKIM1; k=rsa; p=MIGfMA0GCS==")
        assert r.valid

    def test_dmarc(self):
        r = validate_record("DMARC", "v=DMARC1; p=reject")
        assert r.valid

    def test_a(self):
        r = validate_record("A", "93.184.216.34")
        assert r.valid

    def test_tlsa(self):
        r = validate_record("TLSA", "3 1 1 " + "a" * 64)
        assert r.valid

    def test_case_insensitive(self):
        r = validate_record("a", "93.184.216.34")
        assert r.valid

    def test_unknown(self):
        with pytest.raises(ValueError):
            validate_record("UNKNOWN", "value")


# ============================================================
# 8. Generators
# ============================================================

class TestGenerators:
    def test_generate_a(self):
        r = generate_a("example.com", "93.184.216.34")
        assert "IN A" in r
        assert "93.184.216.34" in r
        assert "example.com." in r

    def test_generate_aaaa(self):
        r = generate_aaaa("example.com", "2001:db8::1")
        assert "IN AAAA" in r

    def test_generate_mx(self):
        r = generate_mx("example.com", "mail.example.com", priority=20)
        assert "IN MX 20" in r

    def test_generate_spf(self):
        r = generate_spf("example.com", include=["_spf.google.com"])
        assert "v=spf1" in r
        assert "include:_spf.google.com" in r
        assert "~all" in r

    def test_generate_dmarc(self):
        r = generate_dmarc("example.com", policy="reject", rua="dmarc@example.com")
        assert "_dmarc.example.com." in r
        assert "p=reject" in r
        assert "rua=mailto:dmarc@example.com" in r

    def test_generate_ptr_ipv4(self):
        r = generate_ptr("93.184.216.34", "example.com")
        assert "34.216.184.93.in-addr.arpa." in r
        assert "IN PTR" in r

    def test_generate_ptr_ipv6(self):
        r = generate_ptr("2001:db8::1", "example.com")
        assert "ip6.arpa." in r

    def test_generate_a_invalid(self):
        with pytest.raises(Exception):
            generate_a("example.com", "not-an-ip")


# ============================================================
# 9. Explainer
# ============================================================

class TestExplainer:
    def test_explain_type(self):
        r = explain_record("A")
        assert "IPv4" in r
        assert "RFC 1035" in r

    def test_explain_unknown(self):
        r = explain_record("UNKNOWN")
        assert "Unknown" in r

    def test_explain_spf(self):
        r = explain_record("SPF", "v=spf1 include:_spf.google.com ~all")
        assert "SPF" in r
        assert "_spf.google.com" in r

    def test_explain_dmarc(self):
        r = explain_record("DMARC", "v=DMARC1; p=reject; rua=mailto:dmarc@example.com")
        assert "reject" in r.lower()
        assert "dmarc@example.com" in r


# ============================================================
# 10. ValidationResult
# ============================================================

class TestValidationResult:
    def test_str_valid(self):
        r = ValidationResult(valid=True, record_type="A")
        assert "VALID" in str(r)

    def test_str_invalid(self):
        r = ValidationResult(valid=False, record_type="A", errors=["bad"])
        assert "INVALID" in str(r)
        assert "bad" in str(r)

    def test_ok(self):
        assert ValidationResult(valid=True, record_type="A").ok
        assert not ValidationResult(valid=True, record_type="A", errors=["x"]).ok


# ============================================================
# 11. CLI
# ============================================================

class TestCLI:
    def test_lookup(self):
        r = subprocess.run(
            [sys.executable, "reference.py", "lookup", "A"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0
        assert "IPv4" in r.stdout

    def test_lookup_json(self):
        r = subprocess.run(
            [sys.executable, "reference.py", "lookup", "A", "--json"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0
        assert '"name": "A"' in r.stdout

    def test_list(self):
        r = subprocess.run(
            [sys.executable, "reference.py", "list"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0
        assert "A" in r.stdout
        assert "MX" in r.stdout

    def test_search(self):
        r = subprocess.run(
            [sys.executable, "reference.py", "search", "mail"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0
        assert "MX" in r.stdout

    def test_validate_spf(self):
        r = subprocess.run(
            [sys.executable, "reference.py", "validate", "SPF",
             "v=spf1 include:_spf.google.com ~all"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0
        assert "VALID" in r.stdout

    def test_validate_invalid(self):
        r = subprocess.run(
            [sys.executable, "reference.py", "validate", "SPF", "not-spf"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode != 0
        assert "INVALID" in r.stdout

    def test_explain(self):
        r = subprocess.run(
            [sys.executable, "reference.py", "explain", "A"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0
        assert "IPv4" in r.stdout

    def test_generate_a(self):
        r = subprocess.run(
            [sys.executable, "reference.py", "generate", "A",
             "example.com", "1.2.3.4"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0
        assert "IN A" in r.stdout
        assert "1.2.3.4" in r.stdout

    def test_no_command(self):
        r = subprocess.run(
            [sys.executable, "reference.py"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
