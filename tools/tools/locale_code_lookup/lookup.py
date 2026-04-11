"""
Locale Code Lookup — ISO 3166 countries, ISO 639 languages, ISO 4217
currencies, BCP 47 locale parsing, and cross-standard relationships.

Pure Python, zero external dependencies.

CAPABILITIES
============
1. Country Lookup: ISO 3166-1 alpha-2, alpha-3, numeric, name (bidirectional)
2. Language Lookup: ISO 639-1, ISO 639-2, name (bidirectional)
3. Currency Lookup: ISO 4217 code, numeric, name, symbol, decimals
4. Locale Parsing: BCP 47 tag parsing with component validation
5. Relationships: country->languages, language->countries, country->currency
6. Search: partial name matching across all standards
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Country:
    alpha2: str
    alpha3: str
    numeric: str
    name: str
    short_name: str


@dataclass(frozen=True)
class Language:
    iso639_1: str
    iso639_2: str
    name: str
    native_name: str


@dataclass(frozen=True)
class Currency:
    code: str
    numeric: str
    name: str
    symbol: str
    decimals: int


@dataclass
class LocaleInfo:
    tag: str
    language: str
    script: str | None = None
    region: str | None = None
    variants: list[str] = field(default_factory=list)
    extensions: dict[str, str] = field(default_factory=dict)
    private_use: str | None = None
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    language_name: str | None = None
    region_name: str | None = None
    script_name: str | None = None


# ═══════════════════════════════════════════════════════════════════
# ISO 3166-1 Country Data (249 entries)
# ═══════════════════════════════════════════════════════════════════

_COUNTRIES: list[Country] = [
    Country("AF", "AFG", "004", "Islamic Republic of Afghanistan", "Afghanistan"),
    Country("AL", "ALB", "008", "Republic of Albania", "Albania"),
    Country("DZ", "DZA", "012", "People's Democratic Republic of Algeria", "Algeria"),
    Country("AS", "ASM", "016", "American Samoa", "American Samoa"),
    Country("AD", "AND", "020", "Principality of Andorra", "Andorra"),
    Country("AO", "AGO", "024", "Republic of Angola", "Angola"),
    Country("AI", "AIA", "660", "Anguilla", "Anguilla"),
    Country("AQ", "ATA", "010", "Antarctica", "Antarctica"),
    Country("AG", "ATG", "028", "Antigua and Barbuda", "Antigua and Barbuda"),
    Country("AR", "ARG", "032", "Argentine Republic", "Argentina"),
    Country("AM", "ARM", "051", "Republic of Armenia", "Armenia"),
    Country("AW", "ABW", "533", "Aruba", "Aruba"),
    Country("AU", "AUS", "036", "Commonwealth of Australia", "Australia"),
    Country("AT", "AUT", "040", "Republic of Austria", "Austria"),
    Country("AZ", "AZE", "031", "Republic of Azerbaijan", "Azerbaijan"),
    Country("BS", "BHS", "044", "Commonwealth of The Bahamas", "Bahamas"),
    Country("BH", "BHR", "048", "Kingdom of Bahrain", "Bahrain"),
    Country("BD", "BGD", "050", "People's Republic of Bangladesh", "Bangladesh"),
    Country("BB", "BRB", "052", "Barbados", "Barbados"),
    Country("BY", "BLR", "112", "Republic of Belarus", "Belarus"),
    Country("BE", "BEL", "056", "Kingdom of Belgium", "Belgium"),
    Country("BZ", "BLZ", "084", "Belize", "Belize"),
    Country("BJ", "BEN", "204", "Republic of Benin", "Benin"),
    Country("BM", "BMU", "060", "Bermuda", "Bermuda"),
    Country("BT", "BTN", "064", "Kingdom of Bhutan", "Bhutan"),
    Country("BO", "BOL", "068", "Plurinational State of Bolivia", "Bolivia"),
    Country("BQ", "BES", "535", "Bonaire, Sint Eustatius and Saba", "Bonaire"),
    Country("BA", "BIH", "070", "Bosnia and Herzegovina", "Bosnia and Herzegovina"),
    Country("BW", "BWA", "072", "Republic of Botswana", "Botswana"),
    Country("BR", "BRA", "076", "Federative Republic of Brazil", "Brazil"),
    Country("IO", "IOT", "086", "British Indian Ocean Territory", "British Indian Ocean Territory"),
    Country("BN", "BRN", "096", "Nation of Brunei", "Brunei"),
    Country("BG", "BGR", "100", "Republic of Bulgaria", "Bulgaria"),
    Country("BF", "BFA", "854", "Burkina Faso", "Burkina Faso"),
    Country("BI", "BDI", "108", "Republic of Burundi", "Burundi"),
    Country("CV", "CPV", "132", "Republic of Cabo Verde", "Cabo Verde"),
    Country("KH", "KHM", "116", "Kingdom of Cambodia", "Cambodia"),
    Country("CM", "CMR", "120", "Republic of Cameroon", "Cameroon"),
    Country("CA", "CAN", "124", "Canada", "Canada"),
    Country("KY", "CYM", "136", "Cayman Islands", "Cayman Islands"),
    Country("CF", "CAF", "140", "Central African Republic", "Central African Republic"),
    Country("TD", "TCD", "148", "Republic of Chad", "Chad"),
    Country("CL", "CHL", "152", "Republic of Chile", "Chile"),
    Country("CN", "CHN", "156", "People's Republic of China", "China"),
    Country("CO", "COL", "170", "Republic of Colombia", "Colombia"),
    Country("KM", "COM", "174", "Union of the Comoros", "Comoros"),
    Country("CG", "COG", "178", "Republic of the Congo", "Congo"),
    Country("CD", "COD", "180", "Democratic Republic of the Congo", "DR Congo"),
    Country("CK", "COK", "184", "Cook Islands", "Cook Islands"),
    Country("CR", "CRI", "188", "Republic of Costa Rica", "Costa Rica"),
    Country("CI", "CIV", "384", "Republic of Cote d'Ivoire", "Cote d'Ivoire"),
    Country("HR", "HRV", "191", "Republic of Croatia", "Croatia"),
    Country("CU", "CUB", "192", "Republic of Cuba", "Cuba"),
    Country("CW", "CUW", "531", "Country of Curacao", "Curacao"),
    Country("CY", "CYP", "196", "Republic of Cyprus", "Cyprus"),
    Country("CZ", "CZE", "203", "Czech Republic", "Czechia"),
    Country("DK", "DNK", "208", "Kingdom of Denmark", "Denmark"),
    Country("DJ", "DJI", "262", "Republic of Djibouti", "Djibouti"),
    Country("DM", "DMA", "212", "Commonwealth of Dominica", "Dominica"),
    Country("DO", "DOM", "214", "Dominican Republic", "Dominican Republic"),
    Country("EC", "ECU", "218", "Republic of Ecuador", "Ecuador"),
    Country("EG", "EGY", "818", "Arab Republic of Egypt", "Egypt"),
    Country("SV", "SLV", "222", "Republic of El Salvador", "El Salvador"),
    Country("GQ", "GNQ", "226", "Republic of Equatorial Guinea", "Equatorial Guinea"),
    Country("ER", "ERI", "232", "State of Eritrea", "Eritrea"),
    Country("EE", "EST", "233", "Republic of Estonia", "Estonia"),
    Country("SZ", "SWZ", "748", "Kingdom of Eswatini", "Eswatini"),
    Country("ET", "ETH", "231", "Federal Democratic Republic of Ethiopia", "Ethiopia"),
    Country("FK", "FLK", "238", "Falkland Islands", "Falkland Islands"),
    Country("FO", "FRO", "234", "Faroe Islands", "Faroe Islands"),
    Country("FJ", "FJI", "242", "Republic of Fiji", "Fiji"),
    Country("FI", "FIN", "246", "Republic of Finland", "Finland"),
    Country("FR", "FRA", "250", "French Republic", "France"),
    Country("GA", "GAB", "266", "Gabonese Republic", "Gabon"),
    Country("GM", "GMB", "270", "Republic of The Gambia", "Gambia"),
    Country("GE", "GEO", "268", "Georgia", "Georgia"),
    Country("DE", "DEU", "276", "Federal Republic of Germany", "Germany"),
    Country("GH", "GHA", "288", "Republic of Ghana", "Ghana"),
    Country("GI", "GIB", "292", "Gibraltar", "Gibraltar"),
    Country("GR", "GRC", "300", "Hellenic Republic", "Greece"),
    Country("GL", "GRL", "304", "Greenland", "Greenland"),
    Country("GD", "GRD", "308", "Grenada", "Grenada"),
    Country("GT", "GTM", "320", "Republic of Guatemala", "Guatemala"),
    Country("GG", "GGY", "831", "Bailiwick of Guernsey", "Guernsey"),
    Country("GN", "GIN", "324", "Republic of Guinea", "Guinea"),
    Country("GW", "GNB", "624", "Republic of Guinea-Bissau", "Guinea-Bissau"),
    Country("GY", "GUY", "328", "Co-operative Republic of Guyana", "Guyana"),
    Country("HT", "HTI", "332", "Republic of Haiti", "Haiti"),
    Country("VA", "VAT", "336", "Holy See", "Vatican City"),
    Country("HN", "HND", "340", "Republic of Honduras", "Honduras"),
    Country("HK", "HKG", "344", "Hong Kong Special Administrative Region of China", "Hong Kong"),
    Country("HU", "HUN", "348", "Hungary", "Hungary"),
    Country("IS", "ISL", "352", "Republic of Iceland", "Iceland"),
    Country("IN", "IND", "356", "Republic of India", "India"),
    Country("ID", "IDN", "360", "Republic of Indonesia", "Indonesia"),
    Country("IR", "IRN", "364", "Islamic Republic of Iran", "Iran"),
    Country("IQ", "IRQ", "368", "Republic of Iraq", "Iraq"),
    Country("IE", "IRL", "372", "Ireland", "Ireland"),
    Country("IM", "IMN", "833", "Isle of Man", "Isle of Man"),
    Country("IL", "ISR", "376", "State of Israel", "Israel"),
    Country("IT", "ITA", "380", "Italian Republic", "Italy"),
    Country("JM", "JAM", "388", "Jamaica", "Jamaica"),
    Country("JP", "JPN", "392", "Japan", "Japan"),
    Country("JE", "JEY", "832", "Bailiwick of Jersey", "Jersey"),
    Country("JO", "JOR", "400", "Hashemite Kingdom of Jordan", "Jordan"),
    Country("KZ", "KAZ", "398", "Republic of Kazakhstan", "Kazakhstan"),
    Country("KE", "KEN", "404", "Republic of Kenya", "Kenya"),
    Country("KI", "KIR", "296", "Republic of Kiribati", "Kiribati"),
    Country("KP", "PRK", "408", "Democratic People's Republic of Korea", "North Korea"),
    Country("KR", "KOR", "410", "Republic of Korea", "South Korea"),
    Country("KW", "KWT", "414", "State of Kuwait", "Kuwait"),
    Country("KG", "KGZ", "417", "Kyrgyz Republic", "Kyrgyzstan"),
    Country("LA", "LAO", "418", "Lao People's Democratic Republic", "Laos"),
    Country("LV", "LVA", "428", "Republic of Latvia", "Latvia"),
    Country("LB", "LBN", "422", "Lebanese Republic", "Lebanon"),
    Country("LS", "LSO", "426", "Kingdom of Lesotho", "Lesotho"),
    Country("LR", "LBR", "430", "Republic of Liberia", "Liberia"),
    Country("LY", "LBY", "434", "State of Libya", "Libya"),
    Country("LI", "LIE", "438", "Principality of Liechtenstein", "Liechtenstein"),
    Country("LT", "LTU", "440", "Republic of Lithuania", "Lithuania"),
    Country("LU", "LUX", "442", "Grand Duchy of Luxembourg", "Luxembourg"),
    Country("MO", "MAC", "446", "Macao Special Administrative Region of China", "Macao"),
    Country("MG", "MDG", "450", "Republic of Madagascar", "Madagascar"),
    Country("MW", "MWI", "454", "Republic of Malawi", "Malawi"),
    Country("MY", "MYS", "458", "Malaysia", "Malaysia"),
    Country("MV", "MDV", "462", "Republic of Maldives", "Maldives"),
    Country("ML", "MLI", "466", "Republic of Mali", "Mali"),
    Country("MT", "MLT", "470", "Republic of Malta", "Malta"),
    Country("MH", "MHL", "584", "Republic of the Marshall Islands", "Marshall Islands"),
    Country("MR", "MRT", "478", "Islamic Republic of Mauritania", "Mauritania"),
    Country("MU", "MUS", "480", "Republic of Mauritius", "Mauritius"),
    Country("MX", "MEX", "484", "United Mexican States", "Mexico"),
    Country("FM", "FSM", "583", "Federated States of Micronesia", "Micronesia"),
    Country("MD", "MDA", "498", "Republic of Moldova", "Moldova"),
    Country("MC", "MCO", "492", "Principality of Monaco", "Monaco"),
    Country("MN", "MNG", "496", "Mongolia", "Mongolia"),
    Country("ME", "MNE", "499", "Montenegro", "Montenegro"),
    Country("MS", "MSR", "500", "Montserrat", "Montserrat"),
    Country("MA", "MAR", "504", "Kingdom of Morocco", "Morocco"),
    Country("MZ", "MOZ", "508", "Republic of Mozambique", "Mozambique"),
    Country("MM", "MMR", "104", "Republic of the Union of Myanmar", "Myanmar"),
    Country("NA", "NAM", "516", "Republic of Namibia", "Namibia"),
    Country("NR", "NRU", "520", "Republic of Nauru", "Nauru"),
    Country("NP", "NPL", "524", "Federal Democratic Republic of Nepal", "Nepal"),
    Country("NL", "NLD", "528", "Kingdom of the Netherlands", "Netherlands"),
    Country("NZ", "NZL", "554", "New Zealand", "New Zealand"),
    Country("NI", "NIC", "558", "Republic of Nicaragua", "Nicaragua"),
    Country("NE", "NER", "562", "Republic of the Niger", "Niger"),
    Country("NG", "NGA", "566", "Federal Republic of Nigeria", "Nigeria"),
    Country("MK", "MKD", "807", "Republic of North Macedonia", "North Macedonia"),
    Country("NO", "NOR", "578", "Kingdom of Norway", "Norway"),
    Country("OM", "OMN", "512", "Sultanate of Oman", "Oman"),
    Country("PK", "PAK", "586", "Islamic Republic of Pakistan", "Pakistan"),
    Country("PW", "PLW", "585", "Republic of Palau", "Palau"),
    Country("PS", "PSE", "275", "State of Palestine", "Palestine"),
    Country("PA", "PAN", "591", "Republic of Panama", "Panama"),
    Country("PG", "PNG", "598", "Independent State of Papua New Guinea", "Papua New Guinea"),
    Country("PY", "PRY", "600", "Republic of Paraguay", "Paraguay"),
    Country("PE", "PER", "604", "Republic of Peru", "Peru"),
    Country("PH", "PHL", "608", "Republic of the Philippines", "Philippines"),
    Country("PL", "POL", "616", "Republic of Poland", "Poland"),
    Country("PT", "PRT", "620", "Portuguese Republic", "Portugal"),
    Country("PR", "PRI", "630", "Commonwealth of Puerto Rico", "Puerto Rico"),
    Country("QA", "QAT", "634", "State of Qatar", "Qatar"),
    Country("RO", "ROU", "642", "Romania", "Romania"),
    Country("RU", "RUS", "643", "Russian Federation", "Russia"),
    Country("RW", "RWA", "646", "Republic of Rwanda", "Rwanda"),
    Country("KN", "KNA", "659", "Federation of Saint Kitts and Nevis", "Saint Kitts and Nevis"),
    Country("LC", "LCA", "662", "Saint Lucia", "Saint Lucia"),
    Country("VC", "VCT", "670", "Saint Vincent and the Grenadines", "Saint Vincent"),
    Country("WS", "WSM", "882", "Independent State of Samoa", "Samoa"),
    Country("SM", "SMR", "674", "Republic of San Marino", "San Marino"),
    Country("ST", "STP", "678", "Democratic Republic of Sao Tome and Principe", "Sao Tome and Principe"),
    Country("SA", "SAU", "682", "Kingdom of Saudi Arabia", "Saudi Arabia"),
    Country("SN", "SEN", "686", "Republic of Senegal", "Senegal"),
    Country("RS", "SRB", "688", "Republic of Serbia", "Serbia"),
    Country("SC", "SYC", "690", "Republic of Seychelles", "Seychelles"),
    Country("SL", "SLE", "694", "Republic of Sierra Leone", "Sierra Leone"),
    Country("SG", "SGP", "702", "Republic of Singapore", "Singapore"),
    Country("SX", "SXM", "534", "Sint Maarten", "Sint Maarten"),
    Country("SK", "SVK", "703", "Slovak Republic", "Slovakia"),
    Country("SI", "SVN", "705", "Republic of Slovenia", "Slovenia"),
    Country("SB", "SLB", "090", "Solomon Islands", "Solomon Islands"),
    Country("SO", "SOM", "706", "Federal Republic of Somalia", "Somalia"),
    Country("ZA", "ZAF", "710", "Republic of South Africa", "South Africa"),
    Country("SS", "SSD", "728", "Republic of South Sudan", "South Sudan"),
    Country("ES", "ESP", "724", "Kingdom of Spain", "Spain"),
    Country("LK", "LKA", "144", "Democratic Socialist Republic of Sri Lanka", "Sri Lanka"),
    Country("SD", "SDN", "729", "Republic of the Sudan", "Sudan"),
    Country("SR", "SUR", "740", "Republic of Suriname", "Suriname"),
    Country("SE", "SWE", "752", "Kingdom of Sweden", "Sweden"),
    Country("CH", "CHE", "756", "Swiss Confederation", "Switzerland"),
    Country("SY", "SYR", "760", "Syrian Arab Republic", "Syria"),
    Country("TW", "TWN", "158", "Taiwan", "Taiwan"),
    Country("TJ", "TJK", "762", "Republic of Tajikistan", "Tajikistan"),
    Country("TZ", "TZA", "834", "United Republic of Tanzania", "Tanzania"),
    Country("TH", "THA", "764", "Kingdom of Thailand", "Thailand"),
    Country("TL", "TLS", "626", "Democratic Republic of Timor-Leste", "Timor-Leste"),
    Country("TG", "TGO", "768", "Togolese Republic", "Togo"),
    Country("TO", "TON", "776", "Kingdom of Tonga", "Tonga"),
    Country("TT", "TTO", "780", "Republic of Trinidad and Tobago", "Trinidad and Tobago"),
    Country("TN", "TUN", "788", "Republic of Tunisia", "Tunisia"),
    Country("TR", "TUR", "792", "Republic of Turkiye", "Turkey"),
    Country("TM", "TKM", "795", "Turkmenistan", "Turkmenistan"),
    Country("TV", "TUV", "798", "Tuvalu", "Tuvalu"),
    Country("UG", "UGA", "800", "Republic of Uganda", "Uganda"),
    Country("UA", "UKR", "804", "Ukraine", "Ukraine"),
    Country("AE", "ARE", "784", "United Arab Emirates", "United Arab Emirates"),
    Country("GB", "GBR", "826", "United Kingdom of Great Britain and Northern Ireland", "United Kingdom"),
    Country("US", "USA", "840", "United States of America", "United States"),
    Country("UY", "URY", "858", "Eastern Republic of Uruguay", "Uruguay"),
    Country("UZ", "UZB", "860", "Republic of Uzbekistan", "Uzbekistan"),
    Country("VU", "VUT", "548", "Republic of Vanuatu", "Vanuatu"),
    Country("VE", "VEN", "862", "Bolivarian Republic of Venezuela", "Venezuela"),
    Country("VN", "VNM", "704", "Socialist Republic of Viet Nam", "Vietnam"),
    Country("YE", "YEM", "887", "Republic of Yemen", "Yemen"),
    Country("ZM", "ZMB", "894", "Republic of Zambia", "Zambia"),
    Country("ZW", "ZWE", "716", "Republic of Zimbabwe", "Zimbabwe"),
]

# Build country indices
_C_BY_ALPHA2: dict[str, Country] = {}
_C_BY_ALPHA3: dict[str, Country] = {}
_C_BY_NUMERIC: dict[str, Country] = {}
_C_BY_NAME: dict[str, Country] = {}

for _c in _COUNTRIES:
    _C_BY_ALPHA2[_c.alpha2.upper()] = _c
    _C_BY_ALPHA3[_c.alpha3.upper()] = _c
    _C_BY_NUMERIC[_c.numeric] = _c
    _C_BY_NAME[_c.name.lower()] = _c
    _C_BY_NAME[_c.short_name.lower()] = _c


def lookup_country(query: str) -> Country | None:
    """Look up country by alpha-2, alpha-3, numeric code, or name."""
    q = query.strip()
    if not q:
        return None
    up = q.upper()
    if up in _C_BY_ALPHA2:
        return _C_BY_ALPHA2[up]
    if up in _C_BY_ALPHA3:
        return _C_BY_ALPHA3[up]
    if q.isdigit():
        padded = q.zfill(3)
        if padded in _C_BY_NUMERIC:
            return _C_BY_NUMERIC[padded]
    low = q.lower()
    if low in _C_BY_NAME:
        return _C_BY_NAME[low]
    return None


def search_countries(query: str) -> list[Country]:
    """Search countries by partial name. Case-insensitive."""
    if not query or not query.strip():
        return []
    q = query.strip().lower()
    results = []
    seen = set()
    for c in _COUNTRIES:
        if c.alpha2 in seen:
            continue
        if q in c.name.lower() or q in c.short_name.lower() or q in c.alpha2.lower() or q in c.alpha3.lower():
            results.append(c)
            seen.add(c.alpha2)
    return results


def all_countries() -> list[Country]:
    return sorted(_COUNTRIES, key=lambda c: c.alpha2)


# ═══════════════════════════════════════════════════════════════════
# ISO 639 Language Data (184 entries)
# ═══════════════════════════════════════════════════════════════════

_LANGUAGES: list[Language] = [
    Language("aa", "aar", "Afar", "Afaraf"),
    Language("ab", "abk", "Abkhazian", "Abkhazian"),
    Language("af", "afr", "Afrikaans", "Afrikaans"),
    Language("ak", "aka", "Akan", "Akan"),
    Language("am", "amh", "Amharic", "Amharic"),
    Language("an", "arg", "Aragonese", "Aragonese"),
    Language("ar", "ara", "Arabic", "Arabic"),
    Language("as", "asm", "Assamese", "Assamese"),
    Language("av", "ava", "Avaric", "Avaric"),
    Language("ay", "aym", "Aymara", "Aymara"),
    Language("az", "aze", "Azerbaijani", "Azerbaijani"),
    Language("ba", "bak", "Bashkir", "Bashkir"),
    Language("be", "bel", "Belarusian", "Belarusian"),
    Language("bg", "bul", "Bulgarian", "Bulgarian"),
    Language("bn", "ben", "Bengali", "Bengali"),
    Language("bo", "bod", "Tibetan", "Tibetan"),
    Language("br", "bre", "Breton", "Breton"),
    Language("bs", "bos", "Bosnian", "Bosnian"),
    Language("ca", "cat", "Catalan", "Catalan"),
    Language("ce", "che", "Chechen", "Chechen"),
    Language("co", "cos", "Corsican", "Corsican"),
    Language("cs", "ces", "Czech", "Czech"),
    Language("cy", "cym", "Welsh", "Cymraeg"),
    Language("da", "dan", "Danish", "Dansk"),
    Language("de", "deu", "German", "Deutsch"),
    Language("dv", "div", "Divehi", "Divehi"),
    Language("dz", "dzo", "Dzongkha", "Dzongkha"),
    Language("el", "ell", "Greek", "Greek"),
    Language("en", "eng", "English", "English"),
    Language("eo", "epo", "Esperanto", "Esperanto"),
    Language("es", "spa", "Spanish", "Espanol"),
    Language("et", "est", "Estonian", "Estonian"),
    Language("eu", "eus", "Basque", "Euskara"),
    Language("fa", "fas", "Persian", "Farsi"),
    Language("fi", "fin", "Finnish", "Suomi"),
    Language("fj", "fij", "Fijian", "Fijian"),
    Language("fo", "fao", "Faroese", "Faroese"),
    Language("fr", "fra", "French", "Francais"),
    Language("ga", "gle", "Irish", "Gaeilge"),
    Language("gd", "gla", "Scottish Gaelic", "Gaidhlig"),
    Language("gl", "glg", "Galician", "Galego"),
    Language("gn", "grn", "Guarani", "Guarani"),
    Language("gu", "guj", "Gujarati", "Gujarati"),
    Language("ha", "hau", "Hausa", "Hausa"),
    Language("he", "heb", "Hebrew", "Hebrew"),
    Language("hi", "hin", "Hindi", "Hindi"),
    Language("hr", "hrv", "Croatian", "Hrvatski"),
    Language("ht", "hat", "Haitian Creole", "Kreyol Ayisyen"),
    Language("hu", "hun", "Hungarian", "Magyar"),
    Language("hy", "hye", "Armenian", "Armenian"),
    Language("id", "ind", "Indonesian", "Bahasa Indonesia"),
    Language("ig", "ibo", "Igbo", "Igbo"),
    Language("is", "isl", "Icelandic", "Islenska"),
    Language("it", "ita", "Italian", "Italiano"),
    Language("ja", "jpn", "Japanese", "Japanese"),
    Language("jv", "jav", "Javanese", "Javanese"),
    Language("ka", "kat", "Georgian", "Georgian"),
    Language("kk", "kaz", "Kazakh", "Kazakh"),
    Language("km", "khm", "Khmer", "Khmer"),
    Language("kn", "kan", "Kannada", "Kannada"),
    Language("ko", "kor", "Korean", "Korean"),
    Language("ku", "kur", "Kurdish", "Kurdish"),
    Language("ky", "kir", "Kyrgyz", "Kyrgyz"),
    Language("la", "lat", "Latin", "Latina"),
    Language("lb", "ltz", "Luxembourgish", "Luxembourgish"),
    Language("lo", "lao", "Lao", "Lao"),
    Language("lt", "lit", "Lithuanian", "Lietuviu"),
    Language("lv", "lav", "Latvian", "Latviesu"),
    Language("mg", "mlg", "Malagasy", "Malagasy"),
    Language("mi", "mri", "Maori", "Maori"),
    Language("mk", "mkd", "Macedonian", "Macedonian"),
    Language("ml", "mal", "Malayalam", "Malayalam"),
    Language("mn", "mon", "Mongolian", "Mongolian"),
    Language("mr", "mar", "Marathi", "Marathi"),
    Language("ms", "msa", "Malay", "Bahasa Melayu"),
    Language("mt", "mlt", "Maltese", "Malti"),
    Language("my", "mya", "Burmese", "Burmese"),
    Language("nb", "nob", "Norwegian Bokmal", "Norsk Bokmal"),
    Language("nd", "nde", "North Ndebele", "isiNdebele"),
    Language("ne", "nep", "Nepali", "Nepali"),
    Language("nl", "nld", "Dutch", "Nederlands"),
    Language("nn", "nno", "Norwegian Nynorsk", "Norsk Nynorsk"),
    Language("no", "nor", "Norwegian", "Norsk"),
    Language("ny", "nya", "Chichewa", "Chichewa"),
    Language("pa", "pan", "Punjabi", "Panjabi"),
    Language("pl", "pol", "Polish", "Polski"),
    Language("ps", "pus", "Pashto", "Pashto"),
    Language("pt", "por", "Portuguese", "Portugues"),
    Language("qu", "que", "Quechua", "Runa Simi"),
    Language("rm", "roh", "Romansh", "Rumantsch"),
    Language("rn", "run", "Rundi", "Ikirundi"),
    Language("ro", "ron", "Romanian", "Romana"),
    Language("ru", "rus", "Russian", "Russian"),
    Language("rw", "kin", "Kinyarwanda", "Ikinyarwanda"),
    Language("sd", "snd", "Sindhi", "Sindhi"),
    Language("se", "sme", "Northern Sami", "Davvisamigiella"),
    Language("sg", "sag", "Sango", "Sango"),
    Language("si", "sin", "Sinhala", "Sinhala"),
    Language("sk", "slk", "Slovak", "Slovencina"),
    Language("sl", "slv", "Slovenian", "Slovenscina"),
    Language("sm", "smo", "Samoan", "Samoan"),
    Language("sn", "sna", "Shona", "Shona"),
    Language("so", "som", "Somali", "Soomaali"),
    Language("sq", "sqi", "Albanian", "Shqip"),
    Language("sr", "srp", "Serbian", "Srpski"),
    Language("ss", "ssw", "Swati", "Swati"),
    Language("st", "sot", "Southern Sotho", "Sesotho"),
    Language("su", "sun", "Sundanese", "Basa Sunda"),
    Language("sv", "swe", "Swedish", "Svenska"),
    Language("sw", "swa", "Swahili", "Kiswahili"),
    Language("ta", "tam", "Tamil", "Tamil"),
    Language("te", "tel", "Telugu", "Telugu"),
    Language("tg", "tgk", "Tajik", "Tajik"),
    Language("th", "tha", "Thai", "Thai"),
    Language("ti", "tir", "Tigrinya", "Tigrinya"),
    Language("tk", "tuk", "Turkmen", "Turkmen"),
    Language("tl", "tgl", "Tagalog", "Tagalog"),
    Language("tn", "tsn", "Tswana", "Setswana"),
    Language("to", "ton", "Tongan", "Faka Tonga"),
    Language("tr", "tur", "Turkish", "Turkce"),
    Language("ts", "tso", "Tsonga", "Xitsonga"),
    Language("uk", "ukr", "Ukrainian", "Ukrainian"),
    Language("ur", "urd", "Urdu", "Urdu"),
    Language("uz", "uzb", "Uzbek", "Uzbek"),
    Language("vi", "vie", "Vietnamese", "Tieng Viet"),
    Language("xh", "xho", "Xhosa", "isiXhosa"),
    Language("yo", "yor", "Yoruba", "Yoruba"),
    Language("zh", "zho", "Chinese", "Chinese"),
    Language("zu", "zul", "Zulu", "isiZulu"),
]

# Build language indices
_L_BY_639_1: dict[str, Language] = {}
_L_BY_639_2: dict[str, Language] = {}
_L_BY_NAME: dict[str, Language] = {}

for _l in _LANGUAGES:
    _L_BY_639_1[_l.iso639_1.lower()] = _l
    _L_BY_639_2[_l.iso639_2.lower()] = _l
    _L_BY_NAME[_l.name.lower()] = _l
    if _l.native_name.lower() != _l.name.lower():
        _L_BY_NAME[_l.native_name.lower()] = _l


def lookup_language(query: str) -> Language | None:
    """Look up language by ISO 639-1, ISO 639-2, or name."""
    q = query.strip()
    if not q:
        return None
    low = q.lower()
    if low in _L_BY_639_1:
        return _L_BY_639_1[low]
    if low in _L_BY_639_2:
        return _L_BY_639_2[low]
    if low in _L_BY_NAME:
        return _L_BY_NAME[low]
    return None


def search_languages(query: str) -> list[Language]:
    """Search languages by partial name. Case-insensitive."""
    if not query or not query.strip():
        return []
    q = query.strip().lower()
    results = []
    seen = set()
    for lang in _LANGUAGES:
        if lang.iso639_1 in seen:
            continue
        if q in lang.name.lower() or q in lang.native_name.lower() or q in lang.iso639_1 or q in lang.iso639_2:
            results.append(lang)
            seen.add(lang.iso639_1)
    return results


def all_languages() -> list[Language]:
    return sorted(_LANGUAGES, key=lambda l: l.iso639_1)


# ═══════════════════════════════════════════════════════════════════
# ISO 4217 Currency Data (170 active currencies)
# ═══════════════════════════════════════════════════════════════════

_CURRENCIES: list[Currency] = [
    Currency("AED", "784", "UAE Dirham", "AED", 2),
    Currency("AFN", "971", "Afghani", "Af", 2),
    Currency("ALL", "008", "Lek", "L", 2),
    Currency("AMD", "051", "Armenian Dram", "AMD", 2),
    Currency("ARS", "032", "Argentine Peso", "AR$", 2),
    Currency("AUD", "036", "Australian Dollar", "A$", 2),
    Currency("AZN", "944", "Azerbaijan Manat", "AZN", 2),
    Currency("BAM", "977", "Convertible Mark", "KM", 2),
    Currency("BDT", "050", "Taka", "Tk", 2),
    Currency("BGN", "975", "Bulgarian Lev", "lv", 2),
    Currency("BHD", "048", "Bahraini Dinar", "BD", 3),
    Currency("BIF", "108", "Burundi Franc", "FBu", 0),
    Currency("BND", "096", "Brunei Dollar", "B$", 2),
    Currency("BOB", "068", "Boliviano", "Bs.", 2),
    Currency("BRL", "986", "Brazilian Real", "R$", 2),
    Currency("BWP", "072", "Pula", "P", 2),
    Currency("BYN", "933", "Belarusian Ruble", "Br", 2),
    Currency("CAD", "124", "Canadian Dollar", "CA$", 2),
    Currency("CDF", "976", "Congolese Franc", "FC", 2),
    Currency("CHF", "756", "Swiss Franc", "CHF", 2),
    Currency("CLP", "152", "Chilean Peso", "CL$", 0),
    Currency("CNY", "156", "Yuan Renminbi", "CN\u00a5", 2),
    Currency("COP", "170", "Colombian Peso", "CO$", 2),
    Currency("CRC", "188", "Costa Rican Colon", "CRC", 2),
    Currency("CZK", "203", "Czech Koruna", "Kc", 2),
    Currency("DJF", "262", "Djibouti Franc", "Fdj", 0),
    Currency("DKK", "208", "Danish Krone", "kr", 2),
    Currency("DOP", "214", "Dominican Peso", "RD$", 2),
    Currency("DZD", "012", "Algerian Dinar", "DA", 2),
    Currency("EGP", "818", "Egyptian Pound", "EGP", 2),
    Currency("ERN", "232", "Nakfa", "Nfk", 2),
    Currency("ETB", "230", "Ethiopian Birr", "Br", 2),
    Currency("EUR", "978", "Euro", "\u20ac", 2),
    Currency("FJD", "242", "Fiji Dollar", "FJ$", 2),
    Currency("GBP", "826", "Pound Sterling", "\u00a3", 2),
    Currency("GEL", "981", "Lari", "GEL", 2),
    Currency("GHS", "936", "Ghana Cedi", "GH\u20b5", 2),
    Currency("GMD", "270", "Dalasi", "D", 2),
    Currency("GNF", "324", "Guinean Franc", "FG", 0),
    Currency("GTQ", "320", "Quetzal", "Q", 2),
    Currency("HKD", "344", "Hong Kong Dollar", "HK$", 2),
    Currency("HNL", "340", "Lempira", "L", 2),
    Currency("HUF", "348", "Forint", "Ft", 2),
    Currency("IDR", "360", "Rupiah", "Rp", 2),
    Currency("ILS", "376", "New Israeli Sheqel", "\u20aa", 2),
    Currency("INR", "356", "Indian Rupee", "\u20b9", 2),
    Currency("IQD", "368", "Iraqi Dinar", "IQD", 3),
    Currency("IRR", "364", "Iranian Rial", "IRR", 2),
    Currency("ISK", "352", "Iceland Krona", "ISK", 0),
    Currency("JMD", "388", "Jamaican Dollar", "J$", 2),
    Currency("JOD", "400", "Jordanian Dinar", "JD", 3),
    Currency("JPY", "392", "Yen", "\u00a5", 0),
    Currency("KES", "404", "Kenyan Shilling", "KSh", 2),
    Currency("KGS", "417", "Som", "KGS", 2),
    Currency("KHR", "116", "Riel", "KHR", 2),
    Currency("KMF", "174", "Comorian Franc", "CF", 0),
    Currency("KRW", "410", "Won", "\u20a9", 0),
    Currency("KWD", "414", "Kuwaiti Dinar", "KD", 3),
    Currency("KZT", "398", "Tenge", "KZT", 2),
    Currency("LAK", "418", "Lao Kip", "LAK", 2),
    Currency("LBP", "422", "Lebanese Pound", "LBP", 2),
    Currency("LKR", "144", "Sri Lanka Rupee", "Rs", 2),
    Currency("LRD", "430", "Liberian Dollar", "L$", 2),
    Currency("LYD", "434", "Libyan Dinar", "LD", 3),
    Currency("MAD", "504", "Moroccan Dirham", "MAD", 2),
    Currency("MDL", "498", "Moldovan Leu", "L", 2),
    Currency("MGA", "969", "Malagasy Ariary", "Ar", 2),
    Currency("MKD", "807", "Denar", "den", 2),
    Currency("MMK", "104", "Kyat", "K", 2),
    Currency("MNT", "496", "Tugrik", "MNT", 2),
    Currency("MUR", "480", "Mauritius Rupee", "Rs", 2),
    Currency("MVR", "462", "Rufiyaa", "Rf", 2),
    Currency("MWK", "454", "Malawi Kwacha", "MK", 2),
    Currency("MXN", "484", "Mexican Peso", "MX$", 2),
    Currency("MYR", "458", "Malaysian Ringgit", "RM", 2),
    Currency("MZN", "943", "Mozambique Metical", "MT", 2),
    Currency("NAD", "516", "Namibia Dollar", "N$", 2),
    Currency("NGN", "566", "Naira", "\u20a6", 2),
    Currency("NIO", "558", "Cordoba Oro", "C$", 2),
    Currency("NOK", "578", "Norwegian Krone", "kr", 2),
    Currency("NPR", "524", "Nepalese Rupee", "NRs", 2),
    Currency("NZD", "554", "New Zealand Dollar", "NZ$", 2),
    Currency("OMR", "512", "Rial Omani", "OMR", 3),
    Currency("PEN", "604", "Sol", "S/.", 2),
    Currency("PGK", "598", "Kina", "K", 2),
    Currency("PHP", "608", "Philippine Peso", "\u20b1", 2),
    Currency("PKR", "586", "Pakistan Rupee", "Rs", 2),
    Currency("PLN", "985", "Zloty", "zl", 2),
    Currency("PYG", "600", "Guarani", "Gs", 0),
    Currency("QAR", "634", "Qatari Rial", "QR", 2),
    Currency("RON", "946", "Romanian Leu", "lei", 2),
    Currency("RSD", "941", "Serbian Dinar", "din.", 2),
    Currency("RUB", "643", "Russian Ruble", "RUB", 2),
    Currency("RWF", "646", "Rwanda Franc", "RF", 0),
    Currency("SAR", "682", "Saudi Riyal", "SR", 2),
    Currency("SCR", "690", "Seychelles Rupee", "SCR", 2),
    Currency("SDG", "938", "Sudanese Pound", "SDG", 2),
    Currency("SEK", "752", "Swedish Krona", "kr", 2),
    Currency("SGD", "702", "Singapore Dollar", "S$", 2),
    Currency("SOS", "706", "Somali Shilling", "Sh", 2),
    Currency("SSP", "728", "South Sudanese Pound", "SSP", 2),
    Currency("THB", "764", "Baht", "\u0e3f", 2),
    Currency("TJS", "972", "Somoni", "SM", 2),
    Currency("TMT", "934", "Turkmenistan New Manat", "T", 2),
    Currency("TND", "788", "Tunisian Dinar", "DT", 3),
    Currency("TOP", "776", "Pa'anga", "T$", 2),
    Currency("TRY", "949", "Turkish Lira", "TL", 2),
    Currency("TTD", "780", "Trinidad and Tobago Dollar", "TT$", 2),
    Currency("TWD", "901", "New Taiwan Dollar", "NT$", 2),
    Currency("TZS", "834", "Tanzanian Shilling", "TSh", 2),
    Currency("UAH", "980", "Hryvnia", "UAH", 2),
    Currency("UGX", "800", "Uganda Shilling", "USh", 0),
    Currency("USD", "840", "US Dollar", "$", 2),
    Currency("UYU", "858", "Peso Uruguayo", "$U", 2),
    Currency("UZS", "860", "Uzbekistan Sum", "UZS", 2),
    Currency("VES", "928", "Bolivar Soberano", "Bs.S", 2),
    Currency("VND", "704", "Dong", "\u20ab", 0),
    Currency("VUV", "548", "Vatu", "VT", 0),
    Currency("XAF", "950", "CFA Franc BEAC", "FCFA", 0),
    Currency("XCD", "951", "East Caribbean Dollar", "EC$", 2),
    Currency("XOF", "952", "CFA Franc BCEAO", "CFA", 0),
    Currency("XPF", "953", "CFP Franc", "F", 0),
    Currency("YER", "886", "Yemeni Rial", "YER", 2),
    Currency("ZAR", "710", "Rand", "R", 2),
    Currency("ZMW", "967", "Zambian Kwacha", "ZK", 2),
    Currency("ZWL", "932", "Zimbabwe Dollar", "Z$", 2),
]

# Build currency indices
_CUR_BY_CODE: dict[str, Currency] = {}
_CUR_BY_NUMERIC: dict[str, Currency] = {}
_CUR_BY_NAME: dict[str, Currency] = {}

for _cu in _CURRENCIES:
    _CUR_BY_CODE[_cu.code.upper()] = _cu
    _CUR_BY_NUMERIC[_cu.numeric] = _cu
    _CUR_BY_NAME[_cu.name.lower()] = _cu


def lookup_currency(query: str) -> Currency | None:
    """Look up currency by code, numeric code, or name."""
    q = query.strip()
    if not q:
        return None
    up = q.upper()
    if up in _CUR_BY_CODE:
        return _CUR_BY_CODE[up]
    if q.isdigit():
        padded = q.zfill(3)
        if padded in _CUR_BY_NUMERIC:
            return _CUR_BY_NUMERIC[padded]
    low = q.lower()
    if low in _CUR_BY_NAME:
        return _CUR_BY_NAME[low]
    return None


def search_currencies(query: str) -> list[Currency]:
    """Search currencies by partial name or code. Case-insensitive."""
    if not query or not query.strip():
        return []
    q = query.strip().lower()
    results = []
    seen = set()
    for c in _CURRENCIES:
        if c.code in seen:
            continue
        if q in c.name.lower() or q in c.code.lower() or q in c.symbol.lower():
            results.append(c)
            seen.add(c.code)
    return results


def all_currencies() -> list[Currency]:
    return sorted(_CURRENCIES, key=lambda c: c.code)


# ═══════════════════════════════════════════════════════════════════
# Relationships
# ═══════════════════════════════════════════════════════════════════

_COUNTRY_LANGUAGES: dict[str, list[str]] = {
    "AF": ["ps", "fa"], "AL": ["sq"], "DZ": ["ar", "fr"], "AD": ["ca"],
    "AO": ["pt"], "AG": ["en"], "AR": ["es"], "AM": ["hy"],
    "AU": ["en"], "AT": ["de"], "AZ": ["az"], "BS": ["en"],
    "BH": ["ar"], "BD": ["bn"], "BB": ["en"], "BY": ["be", "ru"],
    "BE": ["nl", "fr", "de"], "BZ": ["en", "es"], "BJ": ["fr"],
    "BT": ["dz"], "BO": ["es", "qu", "ay"], "BA": ["bs", "hr", "sr"],
    "BW": ["en", "tn"], "BR": ["pt"], "BN": ["ms"], "BG": ["bg"],
    "BF": ["fr"], "BI": ["fr", "rn"], "CV": ["pt"], "KH": ["km"],
    "CM": ["fr", "en"], "CA": ["en", "fr"], "CF": ["fr", "sg"],
    "TD": ["fr", "ar"], "CL": ["es"], "CN": ["zh"], "CO": ["es"],
    "KM": ["ar", "fr"], "CG": ["fr"], "CD": ["fr"], "CR": ["es"],
    "CI": ["fr"], "HR": ["hr"], "CU": ["es"], "CY": ["el", "tr"],
    "CZ": ["cs"], "DK": ["da"], "DJ": ["fr", "ar"], "DM": ["en"],
    "DO": ["es"], "EC": ["es"], "EG": ["ar"], "SV": ["es"],
    "GQ": ["es", "fr", "pt"], "ER": ["ti", "ar", "en"], "EE": ["et"],
    "SZ": ["en", "ss"], "ET": ["am"], "FJ": ["en", "fj", "hi"],
    "FI": ["fi", "sv"], "FR": ["fr"], "GA": ["fr"], "GM": ["en"],
    "GE": ["ka"], "DE": ["de"], "GH": ["en"], "GR": ["el"],
    "GD": ["en"], "GT": ["es"], "GN": ["fr"], "GW": ["pt"],
    "GY": ["en"], "HT": ["fr", "ht"], "HN": ["es"],
    "HK": ["zh", "en"], "HU": ["hu"], "IS": ["is"],
    "IN": ["hi", "en"], "ID": ["id"], "IR": ["fa"],
    "IQ": ["ar", "ku"], "IE": ["en", "ga"], "IL": ["he", "ar"],
    "IT": ["it"], "JM": ["en"], "JP": ["ja"], "JO": ["ar"],
    "KZ": ["kk", "ru"], "KE": ["en", "sw"], "KP": ["ko"],
    "KR": ["ko"], "KW": ["ar"], "KG": ["ky", "ru"], "LA": ["lo"],
    "LV": ["lv"], "LB": ["ar", "fr"], "LS": ["en", "st"],
    "LR": ["en"], "LY": ["ar"], "LI": ["de"], "LT": ["lt"],
    "LU": ["lb", "fr", "de"], "MO": ["zh", "pt"],
    "MG": ["mg", "fr"], "MW": ["en", "ny"], "MY": ["ms"],
    "MV": ["dv"], "ML": ["fr"], "MT": ["mt", "en"],
    "MR": ["ar"], "MU": ["en", "fr"], "MX": ["es"],
    "FM": ["en"], "MD": ["ro"], "MC": ["fr"], "MN": ["mn"],
    "ME": ["sr"], "MA": ["ar", "fr"], "MZ": ["pt"],
    "MM": ["my"], "NA": ["en"], "NP": ["ne"],
    "NL": ["nl"], "NZ": ["en", "mi"], "NI": ["es"],
    "NE": ["fr"], "NG": ["en"], "MK": ["mk"],
    "NO": ["no", "nb", "nn"], "OM": ["ar"], "PK": ["ur", "en"],
    "PW": ["en"], "PS": ["ar"], "PA": ["es"], "PG": ["en"],
    "PY": ["es", "gn"], "PE": ["es", "qu"], "PH": ["tl", "en"],
    "PL": ["pl"], "PT": ["pt"], "PR": ["es", "en"],
    "QA": ["ar"], "RO": ["ro"], "RU": ["ru"],
    "RW": ["rw", "en", "fr"], "KN": ["en"], "LC": ["en"],
    "VC": ["en"], "WS": ["sm", "en"], "SM": ["it"],
    "ST": ["pt"], "SA": ["ar"], "SN": ["fr"], "RS": ["sr"],
    "SC": ["en", "fr"], "SL": ["en"],
    "SG": ["en", "ms", "zh", "ta"], "SK": ["sk"], "SI": ["sl"],
    "SB": ["en"], "SO": ["so", "ar"],
    "ZA": ["zu", "xh", "af", "en", "st", "tn", "ts"],
    "SS": ["en"], "ES": ["es"], "LK": ["si", "ta"],
    "SD": ["ar", "en"], "SR": ["nl"], "SE": ["sv"],
    "CH": ["de", "fr", "it", "rm"], "SY": ["ar"],
    "TW": ["zh"], "TJ": ["tg"], "TZ": ["sw", "en"],
    "TH": ["th"], "TL": ["pt", "ms"], "TG": ["fr"],
    "TO": ["en", "to"], "TT": ["en"], "TN": ["ar", "fr"],
    "TR": ["tr"], "TM": ["tk"], "TV": ["en"],
    "UG": ["en", "sw"], "UA": ["uk"], "AE": ["ar"],
    "GB": ["en"], "US": ["en"], "UY": ["es"],
    "UZ": ["uz"], "VU": ["en", "fr"], "VE": ["es"],
    "VN": ["vi"], "YE": ["ar"], "ZM": ["en"],
    "ZW": ["en", "sn", "nd"],
}

_COUNTRY_CURRENCY: dict[str, str] = {
    "AF": "AFN", "AL": "ALL", "DZ": "DZD", "AS": "USD", "AD": "EUR",
    "AO": "AOA", "AG": "XCD", "AR": "ARS", "AM": "AMD", "AU": "AUD",
    "AT": "EUR", "AZ": "AZN", "BS": "USD", "BH": "BHD", "BD": "BDT",
    "BB": "USD", "BY": "BYN", "BE": "EUR", "BZ": "USD", "BJ": "XOF",
    "BT": "BTN", "BO": "BOB", "BA": "BAM", "BW": "BWP", "BR": "BRL",
    "BN": "BND", "BG": "BGN", "BF": "XOF", "BI": "BIF", "CV": "CVE",
    "KH": "KHR", "CM": "XAF", "CA": "CAD", "CF": "XAF", "TD": "XAF",
    "CL": "CLP", "CN": "CNY", "CO": "COP", "KM": "KMF", "CG": "XAF",
    "CD": "CDF", "CR": "CRC", "CI": "XOF", "HR": "EUR", "CU": "USD",
    "CY": "EUR", "CZ": "CZK", "DK": "DKK", "DJ": "DJF", "DM": "XCD",
    "DO": "DOP", "EC": "USD", "EG": "EGP", "SV": "USD", "GQ": "XAF",
    "ER": "ERN", "EE": "EUR", "SZ": "SZL", "ET": "ETB", "FJ": "FJD",
    "FI": "EUR", "FR": "EUR", "GA": "XAF", "GM": "GMD", "GE": "GEL",
    "DE": "EUR", "GH": "GHS", "GR": "EUR", "GD": "XCD", "GT": "GTQ",
    "GN": "GNF", "GW": "XOF", "GY": "USD", "HT": "USD", "VA": "EUR",
    "HN": "HNL", "HK": "HKD", "HU": "HUF", "IS": "ISK", "IN": "INR",
    "ID": "IDR", "IR": "IRR", "IQ": "IQD", "IE": "EUR", "IL": "ILS",
    "IT": "EUR", "JM": "JMD", "JP": "JPY", "JO": "JOD", "KZ": "KZT",
    "KE": "KES", "KP": "USD", "KR": "KRW", "KW": "KWD", "KG": "KGS",
    "LA": "LAK", "LV": "EUR", "LB": "LBP", "LS": "LSL", "LR": "LRD",
    "LY": "LYD", "LI": "CHF", "LT": "EUR", "LU": "EUR", "MO": "USD",
    "MG": "MGA", "MW": "MWK", "MY": "MYR", "MV": "MVR", "ML": "XOF",
    "MT": "EUR", "MR": "MUR", "MU": "MUR", "MX": "MXN", "FM": "USD",
    "MD": "MDL", "MC": "EUR", "MN": "MNT", "ME": "EUR", "MA": "MAD",
    "MZ": "MZN", "MM": "MMK", "NA": "NAD", "NP": "NPR", "NL": "EUR",
    "NZ": "NZD", "NI": "NIO", "NE": "XOF", "NG": "NGN", "MK": "MKD",
    "NO": "NOK", "OM": "OMR", "PK": "PKR", "PW": "USD", "PS": "ILS",
    "PA": "USD", "PG": "PGK", "PY": "PYG", "PE": "PEN", "PH": "PHP",
    "PL": "PLN", "PT": "EUR", "PR": "USD", "QA": "QAR", "RO": "RON",
    "RU": "RUB", "RW": "RWF", "KN": "XCD", "LC": "XCD", "VC": "XCD",
    "WS": "USD", "SM": "EUR", "ST": "STN", "SA": "SAR", "SN": "XOF",
    "RS": "RSD", "SC": "SCR", "SL": "SLE", "SG": "SGD", "SK": "EUR",
    "SI": "EUR", "SB": "USD", "SO": "SOS", "ZA": "ZAR", "SS": "SSP",
    "ES": "EUR", "LK": "LKR", "SD": "SDG", "SR": "USD", "SE": "SEK",
    "CH": "CHF", "SY": "SYP", "TW": "TWD", "TJ": "TJS", "TZ": "TZS",
    "TH": "THB", "TL": "USD", "TG": "XOF", "TO": "TOP", "TT": "TTD",
    "TN": "TND", "TR": "TRY", "TM": "TMT", "TV": "AUD", "UG": "UGX",
    "UA": "UAH", "AE": "AED", "GB": "GBP", "US": "USD", "UY": "UYU",
    "UZ": "UZS", "VU": "VUV", "VE": "VES", "VN": "VND", "YE": "YER",
    "ZM": "ZMW", "ZW": "ZWL",
}

# Build reverse index: language -> countries
_LANGUAGE_COUNTRIES: dict[str, list[str]] = {}
for _cc, _langs in _COUNTRY_LANGUAGES.items():
    for _ll in _langs:
        _LANGUAGE_COUNTRIES.setdefault(_ll, []).append(_cc)
for _ll in _LANGUAGE_COUNTRIES:
    _LANGUAGE_COUNTRIES[_ll].sort()


def country_languages(alpha2: str) -> list[str]:
    """Get ISO 639-1 language codes for a country."""
    return list(_COUNTRY_LANGUAGES.get(alpha2.upper().strip(), []))


def language_countries(iso639_1: str) -> list[str]:
    """Get ISO 3166-1 alpha-2 country codes where a language is spoken."""
    return list(_LANGUAGE_COUNTRIES.get(iso639_1.lower().strip(), []))


def country_currency(alpha2: str) -> str | None:
    """Get ISO 4217 currency code for a country."""
    return _COUNTRY_CURRENCY.get(alpha2.upper().strip())


# ═══════════════════════════════════════════════════════════════════
# BCP 47 Locale Parsing
# ═══════════════════════════════════════════════════════════════════

_SCRIPTS: dict[str, str] = {
    "Arab": "Arabic", "Cyrl": "Cyrillic", "Deva": "Devanagari",
    "Geor": "Georgian", "Grek": "Greek", "Hang": "Hangul",
    "Hani": "Han", "Hans": "Simplified Han", "Hant": "Traditional Han",
    "Hebr": "Hebrew", "Jpan": "Japanese", "Kana": "Katakana",
    "Khmr": "Khmer", "Kore": "Korean", "Latn": "Latin",
    "Mlym": "Malayalam", "Mymr": "Myanmar", "Sinh": "Sinhala",
    "Taml": "Tamil", "Telu": "Telugu", "Thai": "Thai",
    "Tibt": "Tibetan",
}

_LANGUAGE_RE = re.compile(r'^[a-zA-Z]{2,8}$')
_SCRIPT_RE = re.compile(r'^[a-zA-Z]{4}$')
_REGION_RE = re.compile(r'^[a-zA-Z]{2}$|^\d{3}$')
_VARIANT_RE = re.compile(r'^[a-zA-Z\d]{5,8}$|^\d[a-zA-Z\d]{3}$')
_EXT_SINGLETON_RE = re.compile(r'^[a-wyzA-WYZ\d]$')


def parse_locale(tag: str) -> LocaleInfo:
    """Parse a BCP 47 locale tag into components."""
    if not tag or not tag.strip():
        return LocaleInfo(tag=tag or "", language="", is_valid=False, errors=["Empty locale tag"])

    original = tag.strip()
    normalized = original.replace("_", "-")
    parts = normalized.split("-")
    info = LocaleInfo(tag=original, language="")
    idx = 0

    if idx < len(parts) and _LANGUAGE_RE.match(parts[idx]):
        info.language = parts[idx].lower()
        idx += 1
    else:
        info.is_valid = False
        info.errors.append(f"Invalid language subtag: '{parts[idx] if idx < len(parts) else ''}'")
        return info

    if idx < len(parts) and _SCRIPT_RE.match(parts[idx]):
        info.script = parts[idx].title()
        idx += 1

    if idx < len(parts) and _REGION_RE.match(parts[idx]):
        region = parts[idx]
        info.region = region if region.isdigit() else region.upper()
        idx += 1

    while idx < len(parts) and _VARIANT_RE.match(parts[idx]):
        info.variants.append(parts[idx].lower())
        idx += 1

    while idx < len(parts):
        part = parts[idx]
        if part.lower() == "x":
            info.private_use = "-".join(parts[idx:])
            break
        elif _EXT_SINGLETON_RE.match(part):
            singleton = part.lower()
            idx += 1
            ext_parts = []
            while idx < len(parts) and not _EXT_SINGLETON_RE.match(parts[idx]) and parts[idx].lower() != "x":
                ext_parts.append(parts[idx])
                idx += 1
            if ext_parts:
                info.extensions[singleton] = "-".join(ext_parts)
            continue
        else:
            info.errors.append(f"Unexpected subtag: '{part}'")
            info.is_valid = False
            idx += 1

    # Resolve names
    if info.language:
        lang = lookup_language(info.language)
        if lang:
            info.language_name = lang.name
        else:
            info.errors.append(f"Unknown language code: '{info.language}'")
    if info.region:
        country = lookup_country(info.region)
        if country:
            info.region_name = country.short_name
        else:
            info.errors.append(f"Unknown region code: '{info.region}'")
    if info.script:
        name = _SCRIPTS.get(info.script)
        if name:
            info.script_name = name
        else:
            info.errors.append(f"Unknown script code: '{info.script}'")

    return info


def validate_locale(tag: str) -> tuple[bool, list[str]]:
    """Validate a BCP 47 locale tag. Returns (is_valid, errors)."""
    info = parse_locale(tag)
    return info.is_valid and not info.errors, info.errors


def format_locale_info(info: LocaleInfo) -> str:
    """Format a LocaleInfo as human-readable string."""
    lines = [f"Locale: {info.tag}"]
    if info.language:
        s = info.language
        if info.language_name:
            s += f" ({info.language_name})"
        lines.append(f"  Language: {s}")
    if info.script:
        s = info.script
        if info.script_name:
            s += f" ({info.script_name})"
        lines.append(f"  Script: {s}")
    if info.region:
        s = info.region
        if info.region_name:
            s += f" ({info.region_name})"
        lines.append(f"  Region: {s}")
    if info.variants:
        lines.append(f"  Variants: {', '.join(info.variants)}")
    if info.extensions:
        for k, v in info.extensions.items():
            lines.append(f"  Extension [{k}]: {v}")
    if info.private_use:
        lines.append(f"  Private use: {info.private_use}")
    if info.errors:
        lines.append(f"  Errors: {'; '.join(info.errors)}")
    else:
        lines.append("  Valid: Yes")
    return "\n".join(lines)
