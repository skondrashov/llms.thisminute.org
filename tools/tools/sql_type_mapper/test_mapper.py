"""
Tests for SQL Type Mapper.

These tests ARE the spec -- if an LLM regenerates the mapper in any
language, these cases define correctness.
"""

import subprocess
import sys
from pathlib import Path

import pytest

_TOOL_DIR = str(Path(__file__).parent)

from mapper import (
    DIALECTS,
    GOTCHAS,
    REGISTRY,
    CompareResult,
    Gotcha,
    MappingResult,
    ParsedType,
    TypeInfo,
    compare_type,
    get_all_type_names,
    get_gotchas,
    get_gotchas_for_mapping,
    get_type_info,
    list_types,
    map_type,
    normalize_type_name,
    parse_type,
)


# ============================================================
# 1. Type parser
# ============================================================


class TestParseSimple:
    def test_simple_int(self):
        p = parse_type("INT")
        assert p.base_type == "INT"
        assert p.params == []
        assert p.unsigned is False
        assert p.array_dims == 0

    def test_uppercase_normalization(self):
        p = parse_type("varchar")
        assert p.base_type == "VARCHAR"

    def test_preserves_raw(self):
        p = parse_type("  varchar(255)  ")
        assert p.raw == "varchar(255)"


class TestParseParameterized:
    def test_varchar_length(self):
        p = parse_type("VARCHAR(255)")
        assert p.base_type == "VARCHAR"
        assert p.params == ["255"]
        assert p.length == 255

    def test_decimal_precision_scale(self):
        p = parse_type("DECIMAL(10,2)")
        assert p.base_type == "DECIMAL"
        assert p.params == ["10", "2"]
        assert p.precision == 10
        assert p.scale == 2

    def test_decimal_with_spaces(self):
        p = parse_type("DECIMAL( 10 , 2 )")
        assert p.params == ["10", "2"]

    def test_no_params_gives_none(self):
        p = parse_type("INT")
        assert p.length is None
        assert p.precision is None
        assert p.scale is None

    def test_max_keyword(self):
        p = parse_type("VARCHAR(MAX)")
        assert p.has_max is True
        assert p.params == ["MAX"]

    def test_nvarchar_max(self):
        p = parse_type("NVARCHAR(MAX)")
        assert p.base_type == "NVARCHAR"
        assert p.has_max is True


class TestParseUnsigned:
    def test_int_unsigned(self):
        p = parse_type("INT UNSIGNED")
        assert p.base_type == "INT"
        assert p.unsigned is True

    def test_bigint_unsigned(self):
        p = parse_type("BIGINT UNSIGNED")
        assert p.base_type == "BIGINT"
        assert p.unsigned is True

    def test_signed_stripped(self):
        p = parse_type("INT SIGNED")
        assert p.base_type == "INT"
        assert p.unsigned is False


class TestParseArrays:
    def test_single_dimension(self):
        p = parse_type("INTEGER[]")
        assert p.base_type == "INTEGER"
        assert p.array_dims == 1

    def test_two_dimensions(self):
        p = parse_type("TEXT[][]")
        assert p.base_type == "TEXT"
        assert p.array_dims == 2

    def test_three_dimensions(self):
        p = parse_type("INT[][][]")
        assert p.base_type == "INT"
        assert p.array_dims == 3


class TestParseMultiWord:
    def test_double_precision(self):
        p = parse_type("DOUBLE PRECISION")
        assert p.base_type == "DOUBLE PRECISION"

    def test_character_varying(self):
        p = parse_type("CHARACTER VARYING(255)")
        assert p.base_type == "CHARACTER VARYING"
        assert p.params == ["255"]

    def test_timestamp_with_time_zone(self):
        p = parse_type("TIMESTAMP WITH TIME ZONE")
        assert p.base_type == "TIMESTAMP WITH TIME ZONE"

    def test_timestamp_without_time_zone(self):
        p = parse_type("TIMESTAMP WITHOUT TIME ZONE")
        assert p.base_type == "TIMESTAMP WITHOUT TIME ZONE"

    def test_time_with_time_zone(self):
        p = parse_type("TIME WITH TIME ZONE")
        assert p.base_type == "TIME WITH TIME ZONE"

    def test_interval_year_to_month(self):
        p = parse_type("INTERVAL YEAR TO MONTH")
        assert p.base_type == "INTERVAL YEAR TO MONTH"

    def test_interval_day_to_second(self):
        p = parse_type("INTERVAL DAY TO SECOND")
        assert p.base_type == "INTERVAL DAY TO SECOND"

    def test_long_raw(self):
        p = parse_type("LONG RAW")
        assert p.base_type == "LONG RAW"

    def test_bit_varying(self):
        p = parse_type("BIT VARYING(32)")
        assert p.base_type == "BIT VARYING"
        assert p.params == ["32"]

    def test_timestamp_with_local_tz(self):
        p = parse_type("TIMESTAMP WITH LOCAL TIME ZONE")
        assert p.base_type == "TIMESTAMP WITH LOCAL TIME ZONE"


class TestFullName:
    def test_simple(self):
        assert parse_type("INT").full_name == "INT"

    def test_with_params(self):
        assert parse_type("VARCHAR(255)").full_name == "VARCHAR(255)"

    def test_with_unsigned(self):
        assert parse_type("INT UNSIGNED").full_name == "INT UNSIGNED"

    def test_with_array(self):
        assert parse_type("INTEGER[]").full_name == "INTEGER[]"

    def test_complex(self):
        p = parse_type("DECIMAL(10,2)")
        assert p.full_name == "DECIMAL(10,2)"


class TestNormalize:
    def test_varchar(self):
        assert normalize_type_name("varchar(255)") == "VARCHAR"

    def test_int_unsigned(self):
        assert normalize_type_name("int unsigned") == "INT"


# ============================================================
# 2. Type registry
# ============================================================


class TestRegistry:
    def test_all_dialects_present(self):
        for d in DIALECTS:
            assert d in REGISTRY
            assert len(REGISTRY[d]) > 0

    def test_postgres_has_expected_types(self):
        expected = ["INTEGER", "TEXT", "BOOLEAN", "TIMESTAMP", "JSONB", "UUID",
                    "BYTEA", "SERIAL", "CHARACTER VARYING"]
        for t in expected:
            assert get_type_info("postgres", t) is not None, f"Missing: {t}"

    def test_mysql_has_expected_types(self):
        expected = ["INT", "VARCHAR", "TINYINT", "MEDIUMINT", "LONGTEXT",
                    "DATETIME", "TIMESTAMP", "ENUM", "SET", "JSON"]
        for t in expected:
            assert get_type_info("mysql", t) is not None, f"Missing: {t}"

    def test_sqlite_has_expected_types(self):
        expected = ["INTEGER", "REAL", "TEXT", "BLOB", "NUMERIC"]
        for t in expected:
            assert get_type_info("sqlite", t) is not None, f"Missing: {t}"

    def test_sqlserver_has_expected_types(self):
        expected = ["INT", "NVARCHAR", "DATETIME2", "BIT", "UNIQUEIDENTIFIER",
                    "VARBINARY", "MONEY"]
        for t in expected:
            assert get_type_info("sqlserver", t) is not None, f"Missing: {t}"

    def test_oracle_has_expected_types(self):
        expected = ["NUMBER", "VARCHAR2", "CLOB", "BLOB", "DATE", "TIMESTAMP",
                    "XMLTYPE", "SDO_GEOMETRY"]
        for t in expected:
            assert get_type_info("oracle", t) is not None, f"Missing: {t}"


class TestAliases:
    def test_pg_int_alias(self):
        info = get_type_info("postgres", "INT")
        assert info is not None
        assert info.name == "INTEGER"

    def test_pg_bool_alias(self):
        info = get_type_info("postgres", "BOOL")
        assert info is not None
        assert info.name == "BOOLEAN"

    def test_pg_varchar_alias(self):
        info = get_type_info("postgres", "VARCHAR")
        assert info is not None
        assert info.name == "CHARACTER VARYING"

    def test_pg_char_alias(self):
        info = get_type_info("postgres", "CHAR")
        assert info is not None
        assert info.name == "CHARACTER"

    def test_mysql_integer_alias(self):
        info = get_type_info("mysql", "INTEGER")
        assert info is not None
        assert info.name == "INT"

    def test_mysql_numeric_alias(self):
        info = get_type_info("mysql", "NUMERIC")
        assert info is not None
        assert info.name == "DECIMAL"

    def test_mysql_bool_alias(self):
        info = get_type_info("mysql", "BOOL")
        assert info is not None
        assert info.name == "BOOLEAN"

    def test_oracle_varchar_alias(self):
        info = get_type_info("oracle", "VARCHAR")
        assert info is not None
        assert info.name == "VARCHAR2"

    def test_pg_timestamptz_alias(self):
        info = get_type_info("postgres", "TIMESTAMPTZ")
        assert info is not None
        assert info.name == "TIMESTAMP WITH TIME ZONE"

    def test_sqlserver_integer_alias(self):
        info = get_type_info("sqlserver", "INTEGER")
        assert info is not None
        assert info.name == "INT"

    def test_unknown_type_returns_none(self):
        assert get_type_info("postgres", "FAKETYPE") is None

    def test_unknown_dialect_returns_none(self):
        assert get_type_info("fakediaelct", "INT") is None


class TestListTypes:
    def test_list_all_postgres(self):
        types = list_types("postgres")
        assert len(types) > 10

    def test_list_by_category(self):
        numerics = list_types("postgres", "numeric")
        assert len(numerics) > 0
        assert all(t.category == "numeric" for t in numerics)

    def test_list_unknown_dialect(self):
        assert list_types("fake") == []


class TestGetAllTypeNames:
    def test_includes_aliases(self):
        names = get_all_type_names("postgres")
        assert "INT" in names  # alias
        assert "INTEGER" in names  # canonical
        assert "BOOL" in names  # alias
        assert "BOOLEAN" in names  # canonical


# ============================================================
# 3. Type mappings: all dialect pairs
# ============================================================


class TestPostgresToOthers:
    """PostgreSQL -> every other dialect."""

    def test_integer_to_mysql(self):
        r = map_type("INTEGER", "postgres", "mysql")
        assert r.target_type == "INT"
        assert r.confidence == "high"

    def test_integer_to_sqlite(self):
        r = map_type("INTEGER", "postgres", "sqlite")
        assert r.target_type == "INTEGER"

    def test_integer_to_sqlserver(self):
        r = map_type("INTEGER", "postgres", "sqlserver")
        assert r.target_type == "INT"

    def test_integer_to_oracle(self):
        r = map_type("INTEGER", "postgres", "oracle")
        assert r.target_type == "NUMBER(10)"

    def test_varchar_to_mysql(self):
        r = map_type("VARCHAR(255)", "postgres", "mysql")
        assert "VARCHAR" in r.target_type
        assert "255" in r.target_type

    def test_varchar_to_sqlserver(self):
        r = map_type("VARCHAR(100)", "postgres", "sqlserver")
        assert "NVARCHAR" in r.target_type

    def test_varchar_to_oracle(self):
        r = map_type("VARCHAR(100)", "postgres", "oracle")
        assert "VARCHAR2" in r.target_type

    def test_text_to_mysql(self):
        r = map_type("TEXT", "postgres", "mysql")
        assert r.target_type == "LONGTEXT"

    def test_text_to_sqlserver(self):
        r = map_type("TEXT", "postgres", "sqlserver")
        assert "NVARCHAR" in r.target_type and "MAX" in r.target_type

    def test_text_to_oracle(self):
        r = map_type("TEXT", "postgres", "oracle")
        assert r.target_type == "CLOB"

    def test_boolean_to_mysql(self):
        r = map_type("BOOLEAN", "postgres", "mysql")
        assert "TINYINT" in r.target_type

    def test_boolean_to_sqlserver(self):
        r = map_type("BOOLEAN", "postgres", "sqlserver")
        assert r.target_type == "BIT"

    def test_boolean_to_oracle(self):
        r = map_type("BOOLEAN", "postgres", "oracle")
        assert "NUMBER(1)" in r.target_type

    def test_jsonb_to_mysql(self):
        r = map_type("JSONB", "postgres", "mysql")
        assert r.target_type == "JSON"

    def test_jsonb_to_sqlserver(self):
        r = map_type("JSONB", "postgres", "sqlserver")
        assert "NVARCHAR" in r.target_type

    def test_uuid_to_mysql(self):
        r = map_type("UUID", "postgres", "mysql")
        assert "CHAR(36)" in r.target_type

    def test_uuid_to_sqlserver(self):
        r = map_type("UUID", "postgres", "sqlserver")
        assert r.target_type == "UNIQUEIDENTIFIER"

    def test_bytea_to_mysql(self):
        r = map_type("BYTEA", "postgres", "mysql")
        assert r.target_type == "LONGBLOB"

    def test_timestamp_to_mysql(self):
        r = map_type("TIMESTAMP", "postgres", "mysql")
        assert "DATETIME" in r.target_type

    def test_timestamptz_to_sqlserver(self):
        r = map_type("TIMESTAMP WITH TIME ZONE", "postgres", "sqlserver")
        assert "DATETIMEOFFSET" in r.target_type

    def test_serial_to_mysql(self):
        r = map_type("SERIAL", "postgres", "mysql")
        assert "AUTO_INCREMENT" in r.target_type

    def test_serial_to_sqlserver(self):
        r = map_type("SERIAL", "postgres", "sqlserver")
        assert "IDENTITY" in r.target_type

    def test_decimal_params_transferred(self):
        r = map_type("DECIMAL(10,2)", "postgres", "mysql")
        assert "DECIMAL" in r.target_type
        assert "10" in r.target_type
        assert "2" in r.target_type

    def test_interval_to_mysql(self):
        r = map_type("INTERVAL", "postgres", "mysql")
        assert "VARCHAR" in r.target_type

    def test_inet_to_mysql(self):
        r = map_type("INET", "postgres", "mysql")
        assert "VARCHAR" in r.target_type

    def test_money_to_mysql(self):
        r = map_type("MONEY", "postgres", "mysql")
        assert "DECIMAL(19,4)" in r.target_type


class TestMySQLToOthers:
    """MySQL -> every other dialect."""

    def test_int_to_postgres(self):
        r = map_type("INT", "mysql", "postgres")
        assert r.target_type == "INTEGER"

    def test_tinyint_to_postgres(self):
        r = map_type("TINYINT", "mysql", "postgres")
        assert r.target_type == "SMALLINT"

    def test_mediumint_to_postgres(self):
        r = map_type("MEDIUMINT", "mysql", "postgres")
        assert r.target_type == "INTEGER"

    def test_varchar_to_postgres(self):
        r = map_type("VARCHAR(255)", "mysql", "postgres")
        assert "CHARACTER VARYING" in r.target_type

    def test_longtext_to_postgres(self):
        r = map_type("LONGTEXT", "mysql", "postgres")
        assert r.target_type == "TEXT"

    def test_enum_to_postgres(self):
        r = map_type("ENUM", "mysql", "postgres")
        assert "VARCHAR" in r.target_type

    def test_datetime_to_postgres(self):
        r = map_type("DATETIME", "mysql", "postgres")
        assert "TIMESTAMP" in r.target_type

    def test_timestamp_to_postgres(self):
        r = map_type("TIMESTAMP", "mysql", "postgres")
        assert "TIMESTAMP WITH TIME ZONE" in r.target_type

    def test_year_to_postgres(self):
        r = map_type("YEAR", "mysql", "postgres")
        assert r.target_type == "SMALLINT"

    def test_json_to_postgres(self):
        r = map_type("JSON", "mysql", "postgres")
        assert r.target_type == "JSONB"

    def test_boolean_to_postgres(self):
        r = map_type("BOOLEAN", "mysql", "postgres")
        assert r.target_type == "BOOLEAN"

    def test_blob_to_postgres(self):
        r = map_type("BLOB", "mysql", "postgres")
        assert r.target_type == "BYTEA"

    def test_int_to_sqlite(self):
        r = map_type("INT", "mysql", "sqlite")
        assert r.target_type == "INTEGER"

    def test_int_to_sqlserver(self):
        r = map_type("INT", "mysql", "sqlserver")
        assert r.target_type == "INT"

    def test_int_to_oracle(self):
        r = map_type("INT", "mysql", "oracle")
        assert "NUMBER(10)" in r.target_type

    def test_double_to_postgres(self):
        r = map_type("DOUBLE", "mysql", "postgres")
        assert r.target_type == "DOUBLE PRECISION"

    def test_set_to_postgres(self):
        r = map_type("SET", "mysql", "postgres")
        assert "VARCHAR" in r.target_type


class TestSQLiteToOthers:
    """SQLite -> every other dialect."""

    def test_integer_to_postgres(self):
        r = map_type("INTEGER", "sqlite", "postgres")
        assert r.target_type == "BIGINT"

    def test_integer_to_mysql(self):
        r = map_type("INTEGER", "sqlite", "mysql")
        assert r.target_type == "BIGINT"

    def test_text_to_postgres(self):
        r = map_type("TEXT", "sqlite", "postgres")
        assert r.target_type == "TEXT"

    def test_text_to_mysql(self):
        r = map_type("TEXT", "sqlite", "mysql")
        assert r.target_type == "LONGTEXT"

    def test_blob_to_postgres(self):
        r = map_type("BLOB", "sqlite", "postgres")
        assert r.target_type == "BYTEA"

    def test_real_to_postgres(self):
        r = map_type("REAL", "sqlite", "postgres")
        assert r.target_type == "DOUBLE PRECISION"

    def test_numeric_to_postgres(self):
        r = map_type("NUMERIC", "sqlite", "postgres")
        assert r.target_type == "NUMERIC"

    def test_integer_to_sqlserver(self):
        r = map_type("INTEGER", "sqlite", "sqlserver")
        assert r.target_type == "BIGINT"

    def test_integer_to_oracle(self):
        r = map_type("INTEGER", "sqlite", "oracle")
        assert "NUMBER(19)" in r.target_type

    def test_text_to_sqlserver(self):
        r = map_type("TEXT", "sqlite", "sqlserver")
        assert "NVARCHAR" in r.target_type and "MAX" in r.target_type

    def test_text_to_oracle(self):
        r = map_type("TEXT", "sqlite", "oracle")
        assert r.target_type == "CLOB"


class TestSQLServerToOthers:
    """SQL Server -> every other dialect."""

    def test_int_to_postgres(self):
        r = map_type("INT", "sqlserver", "postgres")
        assert r.target_type == "INTEGER"

    def test_nvarchar_to_postgres(self):
        r = map_type("NVARCHAR(100)", "sqlserver", "postgres")
        assert "CHARACTER VARYING" in r.target_type

    def test_nvarchar_to_mysql(self):
        r = map_type("NVARCHAR(100)", "sqlserver", "mysql")
        assert "VARCHAR" in r.target_type

    def test_bit_to_postgres(self):
        r = map_type("BIT", "sqlserver", "postgres")
        assert r.target_type == "BOOLEAN"

    def test_bit_to_mysql(self):
        r = map_type("BIT", "sqlserver", "mysql")
        assert "TINYINT" in r.target_type

    def test_datetime2_to_postgres(self):
        r = map_type("DATETIME2", "sqlserver", "postgres")
        assert "TIMESTAMP" in r.target_type

    def test_datetimeoffset_to_postgres(self):
        r = map_type("DATETIMEOFFSET", "sqlserver", "postgres")
        assert "TIMESTAMP WITH TIME ZONE" in r.target_type

    def test_uniqueidentifier_to_postgres(self):
        r = map_type("UNIQUEIDENTIFIER", "sqlserver", "postgres")
        assert r.target_type == "UUID"

    def test_uniqueidentifier_to_mysql(self):
        r = map_type("UNIQUEIDENTIFIER", "sqlserver", "mysql")
        assert "CHAR(36)" in r.target_type

    def test_money_to_mysql(self):
        r = map_type("MONEY", "sqlserver", "mysql")
        assert "DECIMAL(19,4)" in r.target_type

    def test_varbinary_to_postgres(self):
        r = map_type("VARBINARY", "sqlserver", "postgres")
        assert r.target_type == "BYTEA"

    def test_xml_to_postgres(self):
        r = map_type("XML", "sqlserver", "postgres")
        assert r.target_type == "XML"

    def test_tinyint_to_mysql(self):
        r = map_type("TINYINT", "sqlserver", "mysql")
        assert "TINYINT UNSIGNED" in r.target_type

    def test_geography_to_postgres(self):
        r = map_type("GEOGRAPHY", "sqlserver", "postgres")
        assert "GEOGRAPHY" in r.target_type

    def test_int_to_oracle(self):
        r = map_type("INT", "sqlserver", "oracle")
        assert "NUMBER(10)" in r.target_type


class TestOracleToOthers:
    """Oracle -> every other dialect."""

    def test_number_to_postgres(self):
        r = map_type("NUMBER", "oracle", "postgres")
        assert "NUMERIC" in r.target_type

    def test_number_with_params_to_postgres(self):
        r = map_type("NUMBER(10,2)", "oracle", "postgres")
        assert "NUMERIC" in r.target_type

    def test_varchar2_to_postgres(self):
        r = map_type("VARCHAR2(100)", "oracle", "postgres")
        assert "CHARACTER VARYING" in r.target_type

    def test_varchar2_to_mysql(self):
        r = map_type("VARCHAR2(100)", "oracle", "mysql")
        assert "VARCHAR" in r.target_type

    def test_clob_to_postgres(self):
        r = map_type("CLOB", "oracle", "postgres")
        assert r.target_type == "TEXT"

    def test_clob_to_mysql(self):
        r = map_type("CLOB", "oracle", "mysql")
        assert r.target_type == "LONGTEXT"

    def test_date_to_postgres(self):
        r = map_type("DATE", "oracle", "postgres")
        # Oracle DATE includes time, so it should map to TIMESTAMP
        assert "TIMESTAMP" in r.target_type

    def test_date_to_mysql(self):
        r = map_type("DATE", "oracle", "mysql")
        assert "DATETIME" in r.target_type

    def test_blob_to_postgres(self):
        r = map_type("BLOB", "oracle", "postgres")
        assert r.target_type == "BYTEA"

    def test_xmltype_to_postgres(self):
        r = map_type("XMLTYPE", "oracle", "postgres")
        assert r.target_type == "XML"

    def test_sdo_geometry_to_postgres(self):
        r = map_type("SDO_GEOMETRY", "oracle", "postgres")
        assert "GEOMETRY" in r.target_type

    def test_binary_float_to_postgres(self):
        r = map_type("BINARY_FLOAT", "oracle", "postgres")
        assert r.target_type == "REAL"

    def test_binary_double_to_postgres(self):
        r = map_type("BINARY_DOUBLE", "oracle", "postgres")
        assert r.target_type == "DOUBLE PRECISION"

    def test_nvarchar2_to_postgres(self):
        r = map_type("NVARCHAR2(100)", "oracle", "postgres")
        assert "CHARACTER VARYING" in r.target_type

    def test_timestamp_tz_to_postgres(self):
        r = map_type("TIMESTAMP WITH TIME ZONE", "oracle", "postgres")
        assert "TIMESTAMP WITH TIME ZONE" in r.target_type

    def test_interval_year_to_postgres(self):
        r = map_type("INTERVAL YEAR TO MONTH", "oracle", "postgres")
        assert "INTERVAL" in r.target_type

    def test_raw_to_postgres(self):
        r = map_type("RAW", "oracle", "postgres")
        assert r.target_type == "BYTEA"

    def test_long_raw_to_postgres(self):
        r = map_type("LONG RAW", "oracle", "postgres")
        assert r.target_type == "BYTEA"

    def test_number_to_oracle_self(self):
        r = map_type("NUMBER(10,2)", "oracle", "oracle")
        assert r.target_type == "NUMBER(10,2)"
        assert r.confidence == "high"


# ============================================================
# 4. Self-mapping (same dialect)
# ============================================================


class TestSelfMapping:
    def test_postgres_to_postgres(self):
        r = map_type("INTEGER", "postgres", "postgres")
        assert r.target_type == "INTEGER"
        assert r.confidence == "high"

    def test_mysql_to_mysql(self):
        r = map_type("VARCHAR(255)", "mysql", "mysql")
        assert r.target_type == "VARCHAR(255)"

    def test_sqlite_to_sqlite(self):
        r = map_type("TEXT", "sqlite", "sqlite")
        assert r.target_type == "TEXT"


# ============================================================
# 5. Array type handling
# ============================================================


class TestArrayMapping:
    def test_int_array_to_mysql(self):
        r = map_type("INTEGER[]", "postgres", "mysql")
        assert r.target_type == "JSON"
        assert any("Array" in w or "array" in w for w in r.warnings)

    def test_int_array_to_postgres(self):
        r = map_type("INTEGER[]", "postgres", "postgres")
        assert "[]" in r.target_type

    def test_text_array_to_sqlite(self):
        r = map_type("TEXT[]", "postgres", "sqlite")
        assert r.target_type == "TEXT"

    def test_multi_dim_array_to_sqlserver(self):
        r = map_type("INTEGER[][]", "postgres", "sqlserver")
        assert r.target_type == "TEXT"


# ============================================================
# 6. Unsigned modifier handling
# ============================================================


class TestUnsignedMapping:
    def test_unsigned_to_postgres_warns(self):
        r = map_type("INT UNSIGNED", "mysql", "postgres")
        assert any("UNSIGNED" in w or "unsigned" in w.lower() for w in r.warnings)

    def test_unsigned_to_mysql_no_warn(self):
        r = map_type("INT UNSIGNED", "mysql", "mysql")
        assert "UNSIGNED" in r.target_type

    def test_unsigned_to_sqlserver_warns(self):
        r = map_type("BIGINT UNSIGNED", "mysql", "sqlserver")
        assert any("UNSIGNED" in w or "unsigned" in w.lower() for w in r.warnings)


# ============================================================
# 7. Unknown types and dialects
# ============================================================


class TestErrorHandling:
    def test_unknown_source_dialect(self):
        r = map_type("INT", "mongodb", "postgres")
        assert r.target_type == "UNKNOWN"
        assert r.confidence == "low"
        assert any("dialect" in w.lower() for w in r.warnings)

    def test_unknown_target_dialect(self):
        r = map_type("INT", "postgres", "mongodb")
        assert r.target_type == "UNKNOWN"
        assert r.confidence == "low"

    def test_unknown_type(self):
        r = map_type("FAKETYPE", "postgres", "mysql")
        assert r.target_type == "UNKNOWN"
        assert r.confidence == "low"
        assert any("not found" in w.lower() for w in r.warnings)


# ============================================================
# 8. Gotchas database
# ============================================================


class TestGotchas:
    def test_gotchas_not_empty(self):
        assert len(GOTCHAS) > 0

    def test_all_gotchas_have_required_fields(self):
        for g in GOTCHAS:
            assert g.id
            assert g.title
            assert g.description
            assert g.source_dialect
            assert g.target_dialect
            assert g.severity in ("info", "warning", "danger")

    def test_filter_by_source_dialect(self):
        mysql_gotchas = get_gotchas(source_dialect="mysql")
        assert len(mysql_gotchas) > 0
        for g in mysql_gotchas:
            assert g.source_dialect in ("mysql", "any")

    def test_filter_by_target_dialect(self):
        pg_gotchas = get_gotchas(target_dialect="postgres")
        assert len(pg_gotchas) > 0
        for g in pg_gotchas:
            assert g.target_dialect in ("postgres", "any")

    def test_filter_by_type(self):
        varchar_gotchas = get_gotchas(type_name="VARCHAR")
        assert len(varchar_gotchas) > 0

    def test_oracle_date_gotcha_exists(self):
        gotchas = get_gotchas(source_dialect="oracle", type_name="DATE")
        assert any("time" in g.title.lower() for g in gotchas)

    def test_mysql_unsigned_gotcha_exists(self):
        gotchas = get_gotchas(source_dialect="mysql", type_name="UNSIGNED")
        assert len(gotchas) > 0

    def test_mysql_enum_gotcha_exists(self):
        gotchas = get_gotchas(source_dialect="mysql", type_name="ENUM")
        assert len(gotchas) > 0

    def test_sqlite_dynamic_typing_gotcha(self):
        gotchas = get_gotchas(source_dialect="sqlite")
        assert any("dynamic" in g.title.lower() for g in gotchas)

    def test_gotcha_severity_levels(self):
        severities = {g.severity for g in GOTCHAS}
        assert "info" in severities
        assert "warning" in severities
        assert "danger" in severities


class TestGotchaInMappings:
    def test_oracle_date_mapping_has_gotcha(self):
        r = map_type("DATE", "oracle", "postgres")
        assert len(r.gotchas) > 0

    def test_mysql_timestamp_mapping_has_gotcha(self):
        r = map_type("TIMESTAMP", "mysql", "postgres")
        assert len(r.gotchas) > 0

    def test_boolean_to_oracle_has_gotcha(self):
        r = map_type("BOOLEAN", "postgres", "oracle")
        assert len(r.gotchas) > 0

    def test_danger_gotcha_lowers_confidence(self):
        r = map_type("DATE", "oracle", "postgres")
        danger = any(g.severity == "danger" for g in r.gotchas)
        if danger:
            assert r.confidence == "low"


# ============================================================
# 9. Compare across all dialects
# ============================================================


class TestCompare:
    def test_compare_integer(self):
        result = compare_type("INTEGER", "postgres")
        assert isinstance(result, CompareResult)
        assert len(result.mappings) == len(DIALECTS)
        # Self-mapping should have high confidence
        assert result.mappings["postgres"].confidence == "high"

    def test_compare_varchar(self):
        result = compare_type("VARCHAR(255)", "mysql")
        assert len(result.mappings) == len(DIALECTS)
        # Every mapping should have a target_type
        for dialect, mapping in result.mappings.items():
            assert mapping.target_type != ""

    def test_compare_auto_detect_pg(self):
        result = compare_type("JSONB")
        assert result.mappings["postgres"].notes == "Source dialect"

    def test_compare_auto_detect_mysql(self):
        result = compare_type("TINYINT")
        assert result.mappings["mysql"].notes == "Source dialect"

    def test_compare_auto_detect_sqlserver(self):
        result = compare_type("NVARCHAR")
        assert result.mappings["sqlserver"].notes == "Source dialect"

    def test_compare_auto_detect_oracle(self):
        result = compare_type("VARCHAR2")
        assert result.mappings["oracle"].notes == "Source dialect"


# ============================================================
# 10. Size/precision warnings
# ============================================================


class TestSizeWarnings:
    def test_large_varchar_mysql_to_sqlserver(self):
        # MySQL VARCHAR can be up to 65535, SQL Server max is 8000
        r = map_type("VARCHAR(10000)", "mysql", "sqlserver")
        assert any("exceeds" in w.lower() or "length" in w.lower() for w in r.warnings)

    def test_large_decimal_mysql_to_sqlserver(self):
        # MySQL DECIMAL max precision is 65, SQL Server is 38
        r = map_type("DECIMAL(50,20)", "mysql", "sqlserver")
        assert any("exceeds" in w.lower() or "precision" in w.lower() for w in r.warnings)


# ============================================================
# 11. Every dialect pair has mappings
# ============================================================


class TestAllDialectPairs:
    """Verify common types can be mapped between all 20 dialect pairs."""

    @pytest.mark.parametrize("source,target", [
        (s, t) for s in DIALECTS for t in DIALECTS if s != t
    ])
    def test_integer_type_maps(self, source, target):
        """Every dialect should be able to map its integer type to every other."""
        # Pick the canonical integer type for each dialect
        int_types = {
            "postgres": "INTEGER",
            "mysql": "INT",
            "sqlite": "INTEGER",
            "sqlserver": "INT",
            "oracle": "INTEGER",
        }
        r = map_type(int_types[source], source, target)
        assert r.target_type != "UNKNOWN", f"{source}->{target}: {r.warnings}"


# ============================================================
# 12. CLI
# ============================================================


class TestCLI:
    def test_basic_mapping(self):
        result = subprocess.run(
            [sys.executable, "mapper.py", "INTEGER", "--from", "postgres", "--to", "mysql"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "Source:" in result.stdout
        assert "Target:" in result.stdout
        assert "INT" in result.stdout

    def test_parameterized_type(self):
        result = subprocess.run(
            [sys.executable, "mapper.py", "VARCHAR(255)", "--from", "mysql", "--to", "postgres"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "CHARACTER VARYING" in result.stdout

    def test_unknown_type(self):
        result = subprocess.run(
            [sys.executable, "mapper.py", "FAKETYPE", "--from", "postgres", "--to", "mysql"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "UNKNOWN" in result.stdout


# ============================================================
# 13. New types: HSTORE, MACADDR8, HIERARCHYID
# ============================================================


class TestNewTypes:
    def test_hstore_exists(self):
        info = get_type_info("postgres", "HSTORE")
        assert info is not None
        assert info.name == "HSTORE"

    def test_hstore_to_mysql(self):
        r = map_type("HSTORE", "postgres", "mysql")
        assert r.target_type == "JSON"

    def test_hstore_to_sqlserver(self):
        r = map_type("HSTORE", "postgres", "sqlserver")
        assert "NVARCHAR" in r.target_type

    def test_macaddr8_exists(self):
        info = get_type_info("postgres", "MACADDR8")
        assert info is not None
        assert info.name == "MACADDR8"

    def test_macaddr8_to_mysql(self):
        r = map_type("MACADDR8", "postgres", "mysql")
        assert "VARCHAR" in r.target_type

    def test_hierarchyid_exists(self):
        info = get_type_info("sqlserver", "HIERARCHYID")
        assert info is not None
        assert info.name == "HIERARCHYID"

    def test_hierarchyid_to_postgres(self):
        r = map_type("HIERARCHYID", "sqlserver", "postgres")
        assert "VARCHAR" in r.target_type

    def test_hierarchyid_to_mysql(self):
        r = map_type("HIERARCHYID", "sqlserver", "mysql")
        assert "VARCHAR" in r.target_type


# ============================================================
# 14. New gotchas: HSTORE, spatial, HIERARCHYID
# ============================================================


class TestNewGotchas:
    def test_hstore_gotcha_exists(self):
        gotchas = get_gotchas(source_dialect="postgres", type_name="HSTORE")
        assert len(gotchas) > 0
        assert any("hstore" in g.title.lower() for g in gotchas)

    def test_spatial_gotcha_exists(self):
        gotchas = get_gotchas(type_name="GEOMETRY")
        assert any("spatial" in g.title.lower() for g in gotchas)

    def test_hierarchyid_gotcha_exists(self):
        gotchas = get_gotchas(source_dialect="sqlserver", type_name="HIERARCHYID")
        assert len(gotchas) > 0
        assert any("hierarchyid" in g.title.lower() for g in gotchas)

    def test_hierarchyid_gotcha_is_danger(self):
        gotchas = get_gotchas(source_dialect="sqlserver", type_name="HIERARCHYID")
        assert any(g.severity == "danger" for g in gotchas)

    def test_total_gotchas_increased(self):
        # Should have more gotchas than before
        assert len(GOTCHAS) >= 30


# ============================================================
# 15. FLOAT alias in MySQL
# ============================================================


class TestFloatAlias:
    def test_mysql_float_to_postgres(self):
        r = map_type("FLOAT", "mysql", "postgres")
        assert r.target_type == "REAL"

    def test_mysql_double_real_alias(self):
        """REAL is an alias for DOUBLE in MySQL."""
        info = get_type_info("mysql", "REAL")
        assert info is not None
        assert info.name == "DOUBLE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
