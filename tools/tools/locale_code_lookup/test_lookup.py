"""
Tests for Locale Code Lookup.

These tests ARE the spec — country codes (ISO 3166), language codes (ISO 639),
currency codes (ISO 4217), BCP 47 locale parsing, and cross-standard relationships.
"""

import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from lookup import (
    Country, Language, Currency, LocaleInfo,
    lookup_country, search_countries, all_countries,
    lookup_language, search_languages, all_languages,
    lookup_currency, search_currencies, all_currencies,
    parse_locale, validate_locale, format_locale_info,
    country_languages, language_countries, country_currency,
)


# ═══════════════════════════════════════════════════════════════════
# 1. Country Lookup (ISO 3166-1)
# ═══════════════════════════════════════════════════════════════════

class TestCountryByAlpha2:
    def test_us(self):
        c = lookup_country("US")
        assert c is not None and c.alpha2 == "US" and c.alpha3 == "USA"
        assert c.numeric == "840" and "United States" in c.name

    def test_gb(self):
        c = lookup_country("GB")
        assert c.short_name == "United Kingdom"

    def test_jp(self):
        assert lookup_country("JP").alpha3 == "JPN"

    def test_de(self):
        assert lookup_country("DE").short_name == "Germany"

    def test_case_insensitive(self):
        assert lookup_country("us") == lookup_country("US")


class TestCountryByAlpha3:
    def test_usa(self):
        assert lookup_country("USA").alpha2 == "US"

    def test_gbr(self):
        assert lookup_country("GBR").alpha2 == "GB"

    def test_jpn(self):
        assert lookup_country("JPN").alpha2 == "JP"

    def test_deu(self):
        assert lookup_country("DEU").alpha2 == "DE"


class TestCountryByNumeric:
    def test_840(self):
        assert lookup_country("840").alpha2 == "US"

    def test_826(self):
        assert lookup_country("826").alpha2 == "GB"

    def test_leading_zeros(self):
        assert lookup_country("004").alpha2 == "AF"

    def test_no_leading_zeros(self):
        assert lookup_country("4").alpha2 == "AF"


class TestCountryByName:
    def test_full_name(self):
        assert lookup_country("United States of America").alpha2 == "US"

    def test_short_name(self):
        assert lookup_country("United States").alpha2 == "US"

    def test_case_insensitive(self):
        assert lookup_country("japan").alpha2 == "JP"


class TestCountryNotFound:
    def test_unknown(self):
        assert lookup_country("XX") is None

    def test_empty(self):
        assert lookup_country("") is None

    def test_whitespace(self):
        assert lookup_country("  ") is None


class TestSearchCountries:
    def test_united(self):
        names = [c.short_name for c in search_countries("united")]
        assert "United States" in names and "United Kingdom" in names

    def test_empty(self):
        assert search_countries("") == []


MAJOR_COUNTRIES = [
    ("US", "USA", "840"), ("GB", "GBR", "826"), ("JP", "JPN", "392"),
    ("DE", "DEU", "276"), ("FR", "FRA", "250"), ("CN", "CHN", "156"),
    ("IN", "IND", "356"), ("BR", "BRA", "076"), ("AU", "AUS", "036"),
    ("CA", "CAN", "124"), ("RU", "RUS", "643"), ("KR", "KOR", "410"),
]


class TestMajorCountries:
    @pytest.mark.parametrize("a2,a3,num", MAJOR_COUNTRIES)
    def test_alpha2(self, a2, a3, num):
        assert lookup_country(a2).alpha3 == a3

    @pytest.mark.parametrize("a2,a3,num", MAJOR_COUNTRIES)
    def test_alpha3(self, a2, a3, num):
        assert lookup_country(a3).alpha2 == a2

    @pytest.mark.parametrize("a2,a3,num", MAJOR_COUNTRIES)
    def test_numeric(self, a2, a3, num):
        assert lookup_country(num).alpha2 == a2


class TestAllCountries:
    def test_count(self):
        assert len(all_countries()) > 200

    def test_sorted(self):
        codes = [c.alpha2 for c in all_countries()]
        assert codes == sorted(codes)

    def test_fields(self):
        for c in all_countries():
            assert len(c.alpha2) == 2 and len(c.alpha3) == 3 and len(c.numeric) == 3


# ═══════════════════════════════════════════════════════════════════
# 2. Language Lookup (ISO 639)
# ═══════════════════════════════════════════════════════════════════

class TestLanguageByCode:
    def test_en_639_1(self):
        l = lookup_language("en")
        assert l.iso639_2 == "eng" and l.name == "English"

    def test_eng_639_2(self):
        assert lookup_language("eng").iso639_1 == "en"

    def test_fr(self):
        assert lookup_language("fr").name == "French"

    def test_zh(self):
        assert lookup_language("zh").name == "Chinese"

    def test_case_insensitive(self):
        assert lookup_language("EN") == lookup_language("en")


class TestLanguageByName:
    def test_english(self):
        assert lookup_language("English").iso639_1 == "en"

    def test_french(self):
        assert lookup_language("French").iso639_1 == "fr"


class TestLanguageNotFound:
    def test_unknown(self):
        assert lookup_language("xx") is None

    def test_empty(self):
        assert lookup_language("") is None


MAJOR_LANGUAGES = [
    ("en", "eng", "English"), ("fr", "fra", "French"), ("es", "spa", "Spanish"),
    ("zh", "zho", "Chinese"), ("ja", "jpn", "Japanese"), ("de", "deu", "German"),
    ("ar", "ara", "Arabic"), ("hi", "hin", "Hindi"), ("pt", "por", "Portuguese"),
    ("ru", "rus", "Russian"), ("ko", "kor", "Korean"), ("it", "ita", "Italian"),
]


class TestMajorLanguages:
    @pytest.mark.parametrize("c1,c2,name", MAJOR_LANGUAGES)
    def test_639_1(self, c1, c2, name):
        assert lookup_language(c1).name == name

    @pytest.mark.parametrize("c1,c2,name", MAJOR_LANGUAGES)
    def test_639_2(self, c1, c2, name):
        assert lookup_language(c2).iso639_1 == c1

    @pytest.mark.parametrize("c1,c2,name", MAJOR_LANGUAGES)
    def test_name(self, c1, c2, name):
        assert lookup_language(name).iso639_1 == c1


class TestAllLanguages:
    def test_count(self):
        assert len(all_languages()) > 100

    def test_sorted(self):
        codes = [l.iso639_1 for l in all_languages()]
        assert codes == sorted(codes)


# ═══════════════════════════════════════════════════════════════════
# 3. Currency Lookup (ISO 4217)
# ═══════════════════════════════════════════════════════════════════

class TestCurrencyByCode:
    def test_usd(self):
        c = lookup_currency("USD")
        assert c.name == "US Dollar" and c.symbol == "$" and c.decimals == 2

    def test_eur(self):
        assert lookup_currency("EUR").name == "Euro"

    def test_gbp(self):
        assert lookup_currency("GBP").name == "Pound Sterling"

    def test_jpy(self):
        assert lookup_currency("JPY").decimals == 0

    def test_case_insensitive(self):
        assert lookup_currency("usd") == lookup_currency("USD")


class TestCurrencyByNumeric:
    def test_840(self):
        assert lookup_currency("840").code == "USD"

    def test_978(self):
        assert lookup_currency("978").code == "EUR"


class TestCurrencyByName:
    def test_us_dollar(self):
        assert lookup_currency("US Dollar").code == "USD"

    def test_euro(self):
        assert lookup_currency("Euro").code == "EUR"


class TestCurrencyNotFound:
    def test_unknown(self):
        assert lookup_currency("XXX") is None

    def test_empty(self):
        assert lookup_currency("") is None


class TestCurrencyDecimals:
    def test_jpy_zero(self):
        assert lookup_currency("JPY").decimals == 0

    def test_krw_zero(self):
        assert lookup_currency("KRW").decimals == 0

    def test_bhd_three(self):
        assert lookup_currency("BHD").decimals == 3

    def test_kwd_three(self):
        assert lookup_currency("KWD").decimals == 3


class TestSearchCurrencies:
    def test_dollar(self):
        codes = [c.code for c in search_currencies("dollar")]
        assert "USD" in codes and "AUD" in codes and "CAD" in codes


MAJOR_CURRENCIES = [
    ("USD", "840"), ("EUR", "978"), ("GBP", "826"), ("JPY", "392"),
    ("CNY", "156"), ("INR", "356"), ("AUD", "036"), ("CAD", "124"),
    ("CHF", "756"), ("BRL", "986"),
]


class TestMajorCurrencies:
    @pytest.mark.parametrize("code,numeric", MAJOR_CURRENCIES)
    def test_code(self, code, numeric):
        assert lookup_currency(code) is not None

    @pytest.mark.parametrize("code,numeric", MAJOR_CURRENCIES)
    def test_numeric(self, code, numeric):
        assert lookup_currency(numeric).code == code


# ═══════════════════════════════════════════════════════════════════
# 4. BCP 47 Locale Parsing
# ═══════════════════════════════════════════════════════════════════

class TestParseLocaleBasic:
    def test_language_only(self):
        info = parse_locale("en")
        assert info.language == "en" and info.language_name == "English"

    def test_language_region(self):
        info = parse_locale("en-US")
        assert info.language == "en" and info.region == "US"
        assert info.language_name == "English" and info.region_name == "United States"

    def test_language_script_region(self):
        info = parse_locale("zh-Hans-CN")
        assert info.language == "zh" and info.script == "Hans" and info.region == "CN"
        assert info.script_name == "Simplified Han"

    def test_sr_latn_rs(self):
        info = parse_locale("sr-Latn-RS")
        assert info.language == "sr" and info.script == "Latn" and info.region == "RS"

    def test_underscore_separator(self):
        info = parse_locale("en_US")
        assert info.language == "en" and info.region == "US"


class TestParseLocaleInvalid:
    def test_empty(self):
        info = parse_locale("")
        assert info.is_valid is False

    def test_unknown_language(self):
        valid, errors = validate_locale("xx-US")
        assert valid is False


COMMON_LOCALES = [
    ("en-US", "en", None, "US"), ("en-GB", "en", None, "GB"),
    ("fr-FR", "fr", None, "FR"), ("de-DE", "de", None, "DE"),
    ("es-ES", "es", None, "ES"), ("it-IT", "it", None, "IT"),
    ("pt-BR", "pt", None, "BR"), ("ja-JP", "ja", None, "JP"),
    ("ko-KR", "ko", None, "KR"), ("zh-CN", "zh", None, "CN"),
    ("zh-TW", "zh", None, "TW"), ("ar-SA", "ar", None, "SA"),
    ("hi-IN", "hi", None, "IN"), ("ru-RU", "ru", None, "RU"),
    ("zh-Hans-CN", "zh", "Hans", "CN"), ("zh-Hant-TW", "zh", "Hant", "TW"),
]


class TestCommonLocales:
    @pytest.mark.parametrize("tag,lang,script,region", COMMON_LOCALES)
    def test_parse(self, tag, lang, script, region):
        info = parse_locale(tag)
        assert info.language == lang and info.script == script and info.region == region

    @pytest.mark.parametrize("tag,lang,script,region", COMMON_LOCALES)
    def test_valid(self, tag, lang, script, region):
        valid, errors = validate_locale(tag)
        assert valid is True


class TestFormatLocaleInfo:
    def test_en_us(self):
        text = format_locale_info(parse_locale("en-US"))
        assert "English" in text and "United States" in text and "Valid: Yes" in text


# ═══════════════════════════════════════════════════════════════════
# 5. Cross-Standard Relationships
# ═══════════════════════════════════════════════════════════════════

class TestCountryLanguages:
    def test_us(self):
        assert "en" in country_languages("US")

    def test_switzerland(self):
        langs = country_languages("CH")
        assert set(["de", "fr", "it", "rm"]).issubset(set(langs))

    def test_belgium(self):
        langs = country_languages("BE")
        assert "nl" in langs and "fr" in langs and "de" in langs

    def test_canada(self):
        langs = country_languages("CA")
        assert "en" in langs and "fr" in langs

    def test_singapore(self):
        langs = country_languages("SG")
        assert "en" in langs and "zh" in langs and "ms" in langs and "ta" in langs

    def test_unknown(self):
        assert country_languages("XX") == []


class TestLanguageCountries:
    def test_english(self):
        c = language_countries("en")
        assert "US" in c and "GB" in c and "AU" in c and "CA" in c

    def test_french(self):
        c = language_countries("fr")
        assert "FR" in c and "CA" in c and "BE" in c and "CH" in c

    def test_spanish(self):
        c = language_countries("es")
        assert "ES" in c and "MX" in c and "AR" in c

    def test_sorted(self):
        assert language_countries("en") == sorted(language_countries("en"))

    def test_unknown(self):
        assert language_countries("xx") == []


class TestCountryCurrency:
    def test_us(self):
        assert country_currency("US") == "USD"

    def test_gb(self):
        assert country_currency("GB") == "GBP"

    def test_jp(self):
        assert country_currency("JP") == "JPY"

    def test_eurozone(self):
        for cc in ["DE", "FR", "IT", "ES", "NL", "BE", "AT", "FI", "IE", "PT"]:
            assert country_currency(cc) == "EUR", f"{cc} should use EUR"

    def test_unknown(self):
        assert country_currency("XX") is None


CFA_BEAC = ["CM", "CF", "TD", "CG", "GQ", "GA"]
CFA_BCEAO = ["BJ", "BF", "CI", "GW", "ML", "NE", "SN"]


class TestCFAFrancZone:
    @pytest.mark.parametrize("cc", CFA_BEAC)
    def test_beac(self, cc):
        assert country_currency(cc) == "XAF"

    @pytest.mark.parametrize("cc", CFA_BCEAO)
    def test_bceao(self, cc):
        assert country_currency(cc) == "XOF"


class TestBidirectionalConsistency:
    def test_country_to_language_reverse(self):
        """Every country->language must appear in language->countries."""
        from lookup import _COUNTRY_LANGUAGES
        for cc, langs in _COUNTRY_LANGUAGES.items():
            for lang in langs:
                assert cc in language_countries(lang), \
                    f"Country {cc} not in language_countries('{lang}')"

    def test_language_to_country_reverse(self):
        """Every language->country must appear in country->languages."""
        from lookup import _LANGUAGE_COUNTRIES
        for lang, countries in _LANGUAGE_COUNTRIES.items():
            for cc in countries:
                assert lang in country_languages(cc), \
                    f"Language {lang} not in country_languages('{cc}')"
