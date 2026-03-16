"""
SQL Type Mapper — Cross-Dialect SQL Type Conversion for Agents

Maps SQL types between PostgreSQL, MySQL, SQLite, SQL Server, and Oracle.
Parses type strings (VARCHAR(255), DECIMAL(10,2), INT UNSIGNED, INTEGER[]),
looks up equivalents in a comprehensive type registry, transfers parameters,
and flags known gotchas that cause real data-loss bugs in migrations.

Agents constantly generate DDL for multiple databases and need to know that
PostgreSQL TEXT != MySQL TEXT, Oracle DATE includes time, and MySQL TINYINT(1)
is secretly a boolean.

SUPPORTED DIALECTS
==================
  postgres, mysql, sqlite, sqlserver, oracle

FEATURES
========
  - 100+ type entries across 5 dialects with full cross-mapping
  - Alias resolution (INT -> INTEGER, BOOL -> BOOLEAN, VARCHAR -> CHARACTER VARYING)
  - Parameter handling: length, precision/scale, MAX keyword
  - Unsigned modifier support (MySQL)
  - Array type handling (PostgreSQL INTEGER[], TEXT[][])
  - 30+ gotchas database with severity levels and workarounds
  - Dialect auto-detection from type names
  - Size/precision limit warnings and truncation

Pure Python, no external dependencies.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ============================================================
# Type Registry
# ============================================================

@dataclass
class TypeInfo:
    """Information about a single SQL type in a specific dialect."""
    name: str
    aliases: list[str] = field(default_factory=list)
    category: str = "special"
    params: str = "none"  # none, length, precision_scale, length_optional
    max_size: Optional[int] = None
    precision_max: Optional[int] = None
    scale_max: Optional[int] = None
    unsigned: bool = False
    notes: str = ""
    mappings: dict[str, str] = field(default_factory=dict)


DIALECTS = ("postgres", "mysql", "sqlite", "sqlserver", "oracle")

CATEGORIES = (
    "numeric", "string", "temporal", "binary", "boolean",
    "json", "uuid", "geometric", "array", "xml",
    "monetary", "interval", "network", "special",
)


def _pg_types() -> dict[str, TypeInfo]:
    return {
        "SMALLINT": TypeInfo(name="SMALLINT", aliases=["INT2"], category="numeric",
            notes="2 bytes, -32768 to 32767",
            mappings={"mysql": "SMALLINT", "sqlite": "INTEGER", "sqlserver": "SMALLINT", "oracle": "NUMBER(5)"}),
        "INTEGER": TypeInfo(name="INTEGER", aliases=["INT", "INT4"], category="numeric",
            notes="4 bytes, -2147483648 to 2147483647",
            mappings={"mysql": "INT", "sqlite": "INTEGER", "sqlserver": "INT", "oracle": "NUMBER(10)"}),
        "BIGINT": TypeInfo(name="BIGINT", aliases=["INT8"], category="numeric",
            notes="8 bytes",
            mappings={"mysql": "BIGINT", "sqlite": "INTEGER", "sqlserver": "BIGINT", "oracle": "NUMBER(19)"}),
        "SMALLSERIAL": TypeInfo(name="SMALLSERIAL", aliases=["SERIAL2"], category="numeric",
            notes="Auto-incrementing 2-byte integer",
            mappings={"mysql": "SMALLINT AUTO_INCREMENT", "sqlite": "INTEGER", "sqlserver": "SMALLINT IDENTITY", "oracle": "NUMBER(5)"}),
        "SERIAL": TypeInfo(name="SERIAL", aliases=["SERIAL4"], category="numeric",
            notes="Auto-incrementing 4-byte integer",
            mappings={"mysql": "INT AUTO_INCREMENT", "sqlite": "INTEGER", "sqlserver": "INT IDENTITY", "oracle": "NUMBER(10)"}),
        "BIGSERIAL": TypeInfo(name="BIGSERIAL", aliases=["SERIAL8"], category="numeric",
            notes="Auto-incrementing 8-byte integer",
            mappings={"mysql": "BIGINT AUTO_INCREMENT", "sqlite": "INTEGER", "sqlserver": "BIGINT IDENTITY", "oracle": "NUMBER(19)"}),
        "DECIMAL": TypeInfo(name="DECIMAL", aliases=["NUMERIC"], category="numeric",
            params="precision_scale", precision_max=1000, scale_max=1000,
            notes="Variable precision, exact",
            mappings={"mysql": "DECIMAL", "sqlite": "NUMERIC", "sqlserver": "DECIMAL", "oracle": "NUMBER"}),
        "REAL": TypeInfo(name="REAL", aliases=["FLOAT4"], category="numeric",
            notes="4 bytes, 6 decimal digits precision",
            mappings={"mysql": "FLOAT", "sqlite": "REAL", "sqlserver": "REAL", "oracle": "BINARY_FLOAT"}),
        "DOUBLE PRECISION": TypeInfo(name="DOUBLE PRECISION", aliases=["FLOAT8"], category="numeric",
            notes="8 bytes, 15 decimal digits precision",
            mappings={"mysql": "DOUBLE", "sqlite": "REAL", "sqlserver": "FLOAT", "oracle": "BINARY_DOUBLE"}),
        "MONEY": TypeInfo(name="MONEY", category="monetary",
            notes="8 bytes, currency amount",
            mappings={"mysql": "DECIMAL(19,4)", "sqlite": "NUMERIC", "sqlserver": "MONEY", "oracle": "NUMBER(19,4)"}),
        "CHARACTER VARYING": TypeInfo(name="CHARACTER VARYING", aliases=["VARCHAR"], category="string",
            params="length", max_size=10485760, notes="Variable-length string",
            mappings={"mysql": "VARCHAR", "sqlite": "TEXT", "sqlserver": "NVARCHAR", "oracle": "VARCHAR2"}),
        "CHARACTER": TypeInfo(name="CHARACTER", aliases=["CHAR"], category="string",
            params="length", max_size=10485760, notes="Fixed-length string, blank padded",
            mappings={"mysql": "CHAR", "sqlite": "TEXT", "sqlserver": "NCHAR", "oracle": "CHAR"}),
        "TEXT": TypeInfo(name="TEXT", category="string",
            notes="Variable-length, unlimited",
            mappings={"mysql": "LONGTEXT", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)", "oracle": "CLOB"}),
        "NAME": TypeInfo(name="NAME", category="string",
            notes="63-byte internal type for identifiers",
            mappings={"mysql": "VARCHAR(63)", "sqlite": "TEXT", "sqlserver": "NVARCHAR(63)", "oracle": "VARCHAR2(63)"}),
        "DATE": TypeInfo(name="DATE", category="temporal",
            notes="Calendar date (year, month, day)",
            mappings={"mysql": "DATE", "sqlite": "TEXT", "sqlserver": "DATE", "oracle": "DATE"}),
        "TIME": TypeInfo(name="TIME", aliases=["TIME WITHOUT TIME ZONE"], category="temporal",
            params="precision_scale", precision_max=6, notes="Time of day without timezone",
            mappings={"mysql": "TIME", "sqlite": "TEXT", "sqlserver": "TIME", "oracle": "DATE"}),
        "TIME WITH TIME ZONE": TypeInfo(name="TIME WITH TIME ZONE", aliases=["TIMETZ"], category="temporal",
            params="precision_scale", precision_max=6, notes="Time of day with timezone",
            mappings={"mysql": "TIME", "sqlite": "TEXT", "sqlserver": "DATETIMEOFFSET", "oracle": "TIMESTAMP WITH TIME ZONE"}),
        "TIMESTAMP": TypeInfo(name="TIMESTAMP", aliases=["TIMESTAMP WITHOUT TIME ZONE"], category="temporal",
            params="precision_scale", precision_max=6, notes="Date and time without timezone",
            mappings={"mysql": "DATETIME", "sqlite": "TEXT", "sqlserver": "DATETIME2", "oracle": "TIMESTAMP"}),
        "TIMESTAMP WITH TIME ZONE": TypeInfo(name="TIMESTAMP WITH TIME ZONE", aliases=["TIMESTAMPTZ"], category="temporal",
            params="precision_scale", precision_max=6, notes="Date and time with timezone",
            mappings={"mysql": "DATETIME", "sqlite": "TEXT", "sqlserver": "DATETIMEOFFSET", "oracle": "TIMESTAMP WITH TIME ZONE"}),
        "INTERVAL": TypeInfo(name="INTERVAL", category="interval",
            notes="Time span",
            mappings={"mysql": "VARCHAR(255)", "sqlite": "TEXT", "sqlserver": "VARCHAR(255)", "oracle": "INTERVAL YEAR TO MONTH"}),
        "BYTEA": TypeInfo(name="BYTEA", category="binary",
            notes="Variable-length binary data",
            mappings={"mysql": "LONGBLOB", "sqlite": "BLOB", "sqlserver": "VARBINARY(MAX)", "oracle": "BLOB"}),
        "BOOLEAN": TypeInfo(name="BOOLEAN", aliases=["BOOL"], category="boolean",
            notes="TRUE/FALSE",
            mappings={"mysql": "TINYINT(1)", "sqlite": "INTEGER", "sqlserver": "BIT", "oracle": "NUMBER(1)"}),
        "JSON": TypeInfo(name="JSON", category="json",
            notes="JSON data, stored as text",
            mappings={"mysql": "JSON", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)", "oracle": "CLOB"}),
        "JSONB": TypeInfo(name="JSONB", category="json",
            notes="JSON data, stored in binary format",
            mappings={"mysql": "JSON", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)", "oracle": "CLOB"}),
        "UUID": TypeInfo(name="UUID", category="uuid",
            notes="128-bit UUID",
            mappings={"mysql": "CHAR(36)", "sqlite": "TEXT", "sqlserver": "UNIQUEIDENTIFIER", "oracle": "RAW(16)"}),
        "INET": TypeInfo(name="INET", category="network",
            notes="IPv4 or IPv6 host address",
            mappings={"mysql": "VARCHAR(45)", "sqlite": "TEXT", "sqlserver": "VARCHAR(45)", "oracle": "VARCHAR2(45)"}),
        "CIDR": TypeInfo(name="CIDR", category="network",
            notes="IPv4 or IPv6 network address",
            mappings={"mysql": "VARCHAR(45)", "sqlite": "TEXT", "sqlserver": "VARCHAR(45)", "oracle": "VARCHAR2(45)"}),
        "MACADDR": TypeInfo(name="MACADDR", category="network",
            notes="MAC address",
            mappings={"mysql": "VARCHAR(17)", "sqlite": "TEXT", "sqlserver": "VARCHAR(17)", "oracle": "VARCHAR2(17)"}),
        "XML": TypeInfo(name="XML", category="xml",
            notes="XML data",
            mappings={"mysql": "LONGTEXT", "sqlite": "TEXT", "sqlserver": "XML", "oracle": "XMLTYPE"}),
        "POINT": TypeInfo(name="POINT", category="geometric",
            notes="Geometric point (x,y)",
            mappings={"mysql": "POINT", "sqlite": "TEXT", "sqlserver": "GEOMETRY", "oracle": "SDO_GEOMETRY"}),
        "LINE": TypeInfo(name="LINE", category="geometric",
            notes="Infinite line",
            mappings={"mysql": "LINESTRING", "sqlite": "TEXT", "sqlserver": "GEOMETRY", "oracle": "SDO_GEOMETRY"}),
        "BOX": TypeInfo(name="BOX", category="geometric",
            notes="Rectangular box",
            mappings={"mysql": "POLYGON", "sqlite": "TEXT", "sqlserver": "GEOMETRY", "oracle": "SDO_GEOMETRY"}),
        "CIRCLE": TypeInfo(name="CIRCLE", category="geometric",
            notes="Circle",
            mappings={"mysql": "POLYGON", "sqlite": "TEXT", "sqlserver": "GEOMETRY", "oracle": "SDO_GEOMETRY"}),
        "POLYGON": TypeInfo(name="POLYGON", category="geometric",
            notes="Polygon",
            mappings={"mysql": "POLYGON", "sqlite": "TEXT", "sqlserver": "GEOMETRY", "oracle": "SDO_GEOMETRY"}),
        "PATH": TypeInfo(name="PATH", category="geometric",
            notes="Geometric path",
            mappings={"mysql": "LINESTRING", "sqlite": "TEXT", "sqlserver": "GEOMETRY", "oracle": "SDO_GEOMETRY"}),
        "ARRAY": TypeInfo(name="ARRAY", category="array",
            notes="Array of any type (e.g., INTEGER[])",
            mappings={"mysql": "JSON", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)", "oracle": "CLOB"}),
        "OID": TypeInfo(name="OID", category="special",
            notes="Object identifier",
            mappings={"mysql": "INT UNSIGNED", "sqlite": "INTEGER", "sqlserver": "INT", "oracle": "NUMBER(10)"}),
        "BIT": TypeInfo(name="BIT", category="binary", params="length",
            notes="Fixed-length bit string",
            mappings={"mysql": "BIT", "sqlite": "INTEGER", "sqlserver": "BINARY", "oracle": "RAW"}),
        "BIT VARYING": TypeInfo(name="BIT VARYING", aliases=["VARBIT"], category="binary",
            params="length", notes="Variable-length bit string",
            mappings={"mysql": "VARBINARY", "sqlite": "BLOB", "sqlserver": "VARBINARY", "oracle": "RAW"}),
        "TSVECTOR": TypeInfo(name="TSVECTOR", category="special",
            notes="Text search vector",
            mappings={"mysql": "LONGTEXT", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)", "oracle": "CLOB"}),
        "TSQUERY": TypeInfo(name="TSQUERY", category="special",
            notes="Text search query",
            mappings={"mysql": "VARCHAR(255)", "sqlite": "TEXT", "sqlserver": "NVARCHAR(255)", "oracle": "VARCHAR2(255)"}),
    }


def _mysql_types() -> dict[str, TypeInfo]:
    return {
        "TINYINT": TypeInfo(name="TINYINT", category="numeric", unsigned=True,
            notes="1 byte, -128 to 127 (signed) or 0 to 255 (unsigned)",
            mappings={"postgres": "SMALLINT", "sqlite": "INTEGER", "sqlserver": "TINYINT", "oracle": "NUMBER(3)"}),
        "SMALLINT": TypeInfo(name="SMALLINT", category="numeric", unsigned=True,
            notes="2 bytes, -32768 to 32767",
            mappings={"postgres": "SMALLINT", "sqlite": "INTEGER", "sqlserver": "SMALLINT", "oracle": "NUMBER(5)"}),
        "MEDIUMINT": TypeInfo(name="MEDIUMINT", category="numeric", unsigned=True,
            notes="3 bytes, -8388608 to 8388607",
            mappings={"postgres": "INTEGER", "sqlite": "INTEGER", "sqlserver": "INT", "oracle": "NUMBER(7)"}),
        "INT": TypeInfo(name="INT", aliases=["INTEGER"], category="numeric", unsigned=True,
            notes="4 bytes, -2147483648 to 2147483647",
            mappings={"postgres": "INTEGER", "sqlite": "INTEGER", "sqlserver": "INT", "oracle": "NUMBER(10)"}),
        "BIGINT": TypeInfo(name="BIGINT", category="numeric", unsigned=True,
            notes="8 bytes",
            mappings={"postgres": "BIGINT", "sqlite": "INTEGER", "sqlserver": "BIGINT", "oracle": "NUMBER(19)"}),
        "DECIMAL": TypeInfo(name="DECIMAL", aliases=["DEC", "NUMERIC", "FIXED"], category="numeric",
            params="precision_scale", precision_max=65, scale_max=30,
            notes="Exact fixed-point",
            mappings={"postgres": "DECIMAL", "sqlite": "NUMERIC", "sqlserver": "DECIMAL", "oracle": "NUMBER"}),
        "FLOAT": TypeInfo(name="FLOAT", category="numeric", params="precision_scale",
            notes="4 bytes, approximate",
            mappings={"postgres": "REAL", "sqlite": "REAL", "sqlserver": "REAL", "oracle": "BINARY_FLOAT"}),
        "DOUBLE": TypeInfo(name="DOUBLE", aliases=["DOUBLE PRECISION", "REAL"], category="numeric",
            notes="8 bytes, approximate",
            mappings={"postgres": "DOUBLE PRECISION", "sqlite": "REAL", "sqlserver": "FLOAT", "oracle": "BINARY_DOUBLE"}),
        "BIT": TypeInfo(name="BIT", category="numeric", params="length",
            notes="Bit-field type, BIT(1) to BIT(64)",
            mappings={"postgres": "BIT", "sqlite": "INTEGER", "sqlserver": "BINARY", "oracle": "RAW"}),
        "CHAR": TypeInfo(name="CHAR", aliases=["CHARACTER"], category="string",
            params="length", max_size=255, notes="Fixed-length string",
            mappings={"postgres": "CHARACTER", "sqlite": "TEXT", "sqlserver": "NCHAR", "oracle": "CHAR"}),
        "VARCHAR": TypeInfo(name="VARCHAR", aliases=["CHARACTER VARYING"], category="string",
            params="length", max_size=65535, notes="Variable-length string",
            mappings={"postgres": "CHARACTER VARYING", "sqlite": "TEXT", "sqlserver": "NVARCHAR", "oracle": "VARCHAR2"}),
        "TINYTEXT": TypeInfo(name="TINYTEXT", category="string", max_size=255,
            notes="Up to 255 bytes",
            mappings={"postgres": "TEXT", "sqlite": "TEXT", "sqlserver": "NVARCHAR(255)", "oracle": "VARCHAR2(255)"}),
        "TEXT": TypeInfo(name="TEXT", category="string", max_size=65535,
            notes="Up to 65,535 bytes",
            mappings={"postgres": "TEXT", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)", "oracle": "CLOB"}),
        "MEDIUMTEXT": TypeInfo(name="MEDIUMTEXT", category="string", max_size=16777215,
            notes="Up to 16,777,215 bytes",
            mappings={"postgres": "TEXT", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)", "oracle": "CLOB"}),
        "LONGTEXT": TypeInfo(name="LONGTEXT", category="string", max_size=4294967295,
            notes="Up to 4,294,967,295 bytes",
            mappings={"postgres": "TEXT", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)", "oracle": "CLOB"}),
        "ENUM": TypeInfo(name="ENUM", category="string",
            notes="Enumeration of string values",
            mappings={"postgres": "VARCHAR(255)", "sqlite": "TEXT", "sqlserver": "NVARCHAR(255)", "oracle": "VARCHAR2(255)"}),
        "SET": TypeInfo(name="SET", category="string",
            notes="Set of string values",
            mappings={"postgres": "VARCHAR(255)", "sqlite": "TEXT", "sqlserver": "NVARCHAR(255)", "oracle": "VARCHAR2(255)"}),
        "DATE": TypeInfo(name="DATE", category="temporal",
            notes="YYYY-MM-DD, range 1000-01-01 to 9999-12-31",
            mappings={"postgres": "DATE", "sqlite": "TEXT", "sqlserver": "DATE", "oracle": "DATE"}),
        "TIME": TypeInfo(name="TIME", category="temporal", params="precision_scale", precision_max=6,
            notes="HH:MM:SS, range -838:59:59 to 838:59:59",
            mappings={"postgres": "TIME", "sqlite": "TEXT", "sqlserver": "TIME", "oracle": "DATE"}),
        "DATETIME": TypeInfo(name="DATETIME", category="temporal", params="precision_scale", precision_max=6,
            notes="YYYY-MM-DD HH:MM:SS",
            mappings={"postgres": "TIMESTAMP", "sqlite": "TEXT", "sqlserver": "DATETIME2", "oracle": "TIMESTAMP"}),
        "TIMESTAMP": TypeInfo(name="TIMESTAMP", category="temporal", params="precision_scale", precision_max=6,
            notes="YYYY-MM-DD HH:MM:SS, auto-update capable, UTC stored",
            mappings={"postgres": "TIMESTAMP WITH TIME ZONE", "sqlite": "TEXT", "sqlserver": "DATETIMEOFFSET", "oracle": "TIMESTAMP WITH TIME ZONE"}),
        "YEAR": TypeInfo(name="YEAR", category="temporal",
            notes="YYYY, range 1901 to 2155",
            mappings={"postgres": "SMALLINT", "sqlite": "INTEGER", "sqlserver": "SMALLINT", "oracle": "NUMBER(4)"}),
        "BINARY": TypeInfo(name="BINARY", category="binary", params="length", max_size=255,
            notes="Fixed-length binary",
            mappings={"postgres": "BYTEA", "sqlite": "BLOB", "sqlserver": "BINARY", "oracle": "RAW"}),
        "VARBINARY": TypeInfo(name="VARBINARY", category="binary", params="length", max_size=65535,
            notes="Variable-length binary",
            mappings={"postgres": "BYTEA", "sqlite": "BLOB", "sqlserver": "VARBINARY", "oracle": "RAW"}),
        "TINYBLOB": TypeInfo(name="TINYBLOB", category="binary", max_size=255,
            notes="Up to 255 bytes",
            mappings={"postgres": "BYTEA", "sqlite": "BLOB", "sqlserver": "VARBINARY(255)", "oracle": "RAW(255)"}),
        "BLOB": TypeInfo(name="BLOB", category="binary", max_size=65535,
            notes="Up to 65,535 bytes",
            mappings={"postgres": "BYTEA", "sqlite": "BLOB", "sqlserver": "VARBINARY(MAX)", "oracle": "BLOB"}),
        "MEDIUMBLOB": TypeInfo(name="MEDIUMBLOB", category="binary", max_size=16777215,
            notes="Up to 16,777,215 bytes",
            mappings={"postgres": "BYTEA", "sqlite": "BLOB", "sqlserver": "VARBINARY(MAX)", "oracle": "BLOB"}),
        "LONGBLOB": TypeInfo(name="LONGBLOB", category="binary", max_size=4294967295,
            notes="Up to 4,294,967,295 bytes",
            mappings={"postgres": "BYTEA", "sqlite": "BLOB", "sqlserver": "VARBINARY(MAX)", "oracle": "BLOB"}),
        "BOOLEAN": TypeInfo(name="BOOLEAN", aliases=["BOOL"], category="boolean",
            notes="Alias for TINYINT(1)",
            mappings={"postgres": "BOOLEAN", "sqlite": "INTEGER", "sqlserver": "BIT", "oracle": "NUMBER(1)"}),
        "JSON": TypeInfo(name="JSON", category="json",
            notes="JSON document, validated on insert",
            mappings={"postgres": "JSONB", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)", "oracle": "CLOB"}),
        "GEOMETRY": TypeInfo(name="GEOMETRY", category="geometric",
            notes="Spatial geometry",
            mappings={"postgres": "GEOMETRY", "sqlite": "TEXT", "sqlserver": "GEOMETRY", "oracle": "SDO_GEOMETRY"}),
        "POINT": TypeInfo(name="POINT", category="geometric",
            notes="Spatial point",
            mappings={"postgres": "POINT", "sqlite": "TEXT", "sqlserver": "GEOMETRY", "oracle": "SDO_GEOMETRY"}),
        "LINESTRING": TypeInfo(name="LINESTRING", category="geometric",
            notes="Spatial line",
            mappings={"postgres": "PATH", "sqlite": "TEXT", "sqlserver": "GEOMETRY", "oracle": "SDO_GEOMETRY"}),
        "POLYGON": TypeInfo(name="POLYGON", category="geometric",
            notes="Spatial polygon",
            mappings={"postgres": "POLYGON", "sqlite": "TEXT", "sqlserver": "GEOMETRY", "oracle": "SDO_GEOMETRY"}),
    }


def _sqlite_types() -> dict[str, TypeInfo]:
    return {
        "INTEGER": TypeInfo(name="INTEGER",
            aliases=["INT", "TINYINT", "SMALLINT", "MEDIUMINT", "BIGINT", "INT2", "INT8"],
            category="numeric",
            notes="Dynamic: 1, 2, 3, 4, 6, or 8 bytes depending on value",
            mappings={"postgres": "BIGINT", "mysql": "BIGINT", "sqlserver": "BIGINT", "oracle": "NUMBER(19)"}),
        "REAL": TypeInfo(name="REAL", aliases=["DOUBLE", "DOUBLE PRECISION", "FLOAT"],
            category="numeric", notes="8-byte IEEE floating point",
            mappings={"postgres": "DOUBLE PRECISION", "mysql": "DOUBLE", "sqlserver": "FLOAT", "oracle": "BINARY_DOUBLE"}),
        "TEXT": TypeInfo(name="TEXT",
            aliases=["CHARACTER", "VARCHAR", "CHAR", "CLOB", "NCHAR", "NVARCHAR", "CHARACTER VARYING"],
            category="string", notes="Variable-length text, any length",
            mappings={"postgres": "TEXT", "mysql": "LONGTEXT", "sqlserver": "NVARCHAR(MAX)", "oracle": "CLOB"}),
        "BLOB": TypeInfo(name="BLOB", category="binary",
            notes="Binary data, stored as-is",
            mappings={"postgres": "BYTEA", "mysql": "LONGBLOB", "sqlserver": "VARBINARY(MAX)", "oracle": "BLOB"}),
        "NUMERIC": TypeInfo(name="NUMERIC",
            aliases=["DECIMAL", "BOOLEAN", "DATE", "DATETIME"],
            category="numeric", params="precision_scale",
            notes="May contain integer or real, affinity-based",
            mappings={"postgres": "NUMERIC", "mysql": "DECIMAL", "sqlserver": "DECIMAL", "oracle": "NUMBER"}),
    }


def _sqlserver_types() -> dict[str, TypeInfo]:
    return {
        "TINYINT": TypeInfo(name="TINYINT", category="numeric",
            notes="1 byte, 0 to 255 (unsigned only)",
            mappings={"postgres": "SMALLINT", "mysql": "TINYINT UNSIGNED", "sqlite": "INTEGER", "oracle": "NUMBER(3)"}),
        "SMALLINT": TypeInfo(name="SMALLINT", category="numeric",
            notes="2 bytes, -32768 to 32767",
            mappings={"postgres": "SMALLINT", "mysql": "SMALLINT", "sqlite": "INTEGER", "oracle": "NUMBER(5)"}),
        "INT": TypeInfo(name="INT", aliases=["INTEGER"], category="numeric",
            notes="4 bytes",
            mappings={"postgres": "INTEGER", "mysql": "INT", "sqlite": "INTEGER", "oracle": "NUMBER(10)"}),
        "BIGINT": TypeInfo(name="BIGINT", category="numeric",
            notes="8 bytes",
            mappings={"postgres": "BIGINT", "mysql": "BIGINT", "sqlite": "INTEGER", "oracle": "NUMBER(19)"}),
        "DECIMAL": TypeInfo(name="DECIMAL", aliases=["DEC", "NUMERIC"], category="numeric",
            params="precision_scale", precision_max=38, scale_max=38,
            notes="Exact numeric",
            mappings={"postgres": "DECIMAL", "mysql": "DECIMAL", "sqlite": "NUMERIC", "oracle": "NUMBER"}),
        "FLOAT": TypeInfo(name="FLOAT", category="numeric", params="length_optional",
            notes="Approximate, 8 bytes (53-bit precision by default)",
            mappings={"postgres": "DOUBLE PRECISION", "mysql": "DOUBLE", "sqlite": "REAL", "oracle": "BINARY_DOUBLE"}),
        "REAL": TypeInfo(name="REAL", category="numeric",
            notes="Approximate, 4 bytes (24-bit precision)",
            mappings={"postgres": "REAL", "mysql": "FLOAT", "sqlite": "REAL", "oracle": "BINARY_FLOAT"}),
        "MONEY": TypeInfo(name="MONEY", category="monetary",
            notes="8 bytes, -922337203685477.5808 to 922337203685477.5807",
            mappings={"postgres": "MONEY", "mysql": "DECIMAL(19,4)", "sqlite": "NUMERIC", "oracle": "NUMBER(19,4)"}),
        "SMALLMONEY": TypeInfo(name="SMALLMONEY", category="monetary",
            notes="4 bytes, -214748.3648 to 214748.3647",
            mappings={"postgres": "MONEY", "mysql": "DECIMAL(10,4)", "sqlite": "NUMERIC", "oracle": "NUMBER(10,4)"}),
        "CHAR": TypeInfo(name="CHAR", aliases=["CHARACTER"], category="string",
            params="length", max_size=8000, notes="Fixed-length non-Unicode",
            mappings={"postgres": "CHARACTER", "mysql": "CHAR", "sqlite": "TEXT", "oracle": "CHAR"}),
        "VARCHAR": TypeInfo(name="VARCHAR", aliases=["CHARACTER VARYING"], category="string",
            params="length", max_size=8000, notes="Variable-length non-Unicode (or MAX for up to 2GB)",
            mappings={"postgres": "CHARACTER VARYING", "mysql": "VARCHAR", "sqlite": "TEXT", "oracle": "VARCHAR2"}),
        "NCHAR": TypeInfo(name="NCHAR", category="string", params="length", max_size=4000,
            notes="Fixed-length Unicode",
            mappings={"postgres": "CHARACTER", "mysql": "CHAR", "sqlite": "TEXT", "oracle": "NCHAR"}),
        "NVARCHAR": TypeInfo(name="NVARCHAR", category="string", params="length", max_size=4000,
            notes="Variable-length Unicode (or MAX for up to 2GB)",
            mappings={"postgres": "CHARACTER VARYING", "mysql": "VARCHAR", "sqlite": "TEXT", "oracle": "NVARCHAR2"}),
        "TEXT": TypeInfo(name="TEXT", category="string",
            notes="Deprecated, use VARCHAR(MAX)",
            mappings={"postgres": "TEXT", "mysql": "LONGTEXT", "sqlite": "TEXT", "oracle": "CLOB"}),
        "NTEXT": TypeInfo(name="NTEXT", category="string",
            notes="Deprecated Unicode text, use NVARCHAR(MAX)",
            mappings={"postgres": "TEXT", "mysql": "LONGTEXT", "sqlite": "TEXT", "oracle": "NCLOB"}),
        "DATE": TypeInfo(name="DATE", category="temporal",
            notes="YYYY-MM-DD, 0001-01-01 to 9999-12-31",
            mappings={"postgres": "DATE", "mysql": "DATE", "sqlite": "TEXT", "oracle": "DATE"}),
        "TIME": TypeInfo(name="TIME", category="temporal", params="precision_scale", precision_max=7,
            notes="HH:MM:SS.nnnnnnn",
            mappings={"postgres": "TIME", "mysql": "TIME", "sqlite": "TEXT", "oracle": "DATE"}),
        "DATETIME": TypeInfo(name="DATETIME", category="temporal",
            notes="Legacy, 3.33ms accuracy, range 1753-01-01 to 9999-12-31",
            mappings={"postgres": "TIMESTAMP", "mysql": "DATETIME", "sqlite": "TEXT", "oracle": "TIMESTAMP"}),
        "DATETIME2": TypeInfo(name="DATETIME2", category="temporal",
            params="precision_scale", precision_max=7,
            notes="100ns accuracy, range 0001-01-01 to 9999-12-31",
            mappings={"postgres": "TIMESTAMP", "mysql": "DATETIME", "sqlite": "TEXT", "oracle": "TIMESTAMP"}),
        "SMALLDATETIME": TypeInfo(name="SMALLDATETIME", category="temporal",
            notes="1-minute accuracy, 1900-01-01 to 2079-06-06",
            mappings={"postgres": "TIMESTAMP", "mysql": "DATETIME", "sqlite": "TEXT", "oracle": "TIMESTAMP"}),
        "DATETIMEOFFSET": TypeInfo(name="DATETIMEOFFSET", category="temporal",
            params="precision_scale", precision_max=7,
            notes="Date+time with timezone offset",
            mappings={"postgres": "TIMESTAMP WITH TIME ZONE", "mysql": "DATETIME", "sqlite": "TEXT", "oracle": "TIMESTAMP WITH TIME ZONE"}),
        "BINARY": TypeInfo(name="BINARY", category="binary", params="length", max_size=8000,
            notes="Fixed-length binary",
            mappings={"postgres": "BYTEA", "mysql": "BINARY", "sqlite": "BLOB", "oracle": "RAW"}),
        "VARBINARY": TypeInfo(name="VARBINARY", category="binary", params="length", max_size=8000,
            notes="Variable-length binary (or MAX for up to 2GB)",
            mappings={"postgres": "BYTEA", "mysql": "LONGBLOB", "sqlite": "BLOB", "oracle": "BLOB"}),
        "IMAGE": TypeInfo(name="IMAGE", category="binary",
            notes="Deprecated, use VARBINARY(MAX)",
            mappings={"postgres": "BYTEA", "mysql": "LONGBLOB", "sqlite": "BLOB", "oracle": "BLOB"}),
        "BIT": TypeInfo(name="BIT", category="boolean",
            notes="0 or 1 (boolean equivalent)",
            mappings={"postgres": "BOOLEAN", "mysql": "TINYINT(1)", "sqlite": "INTEGER", "oracle": "NUMBER(1)"}),
        "UNIQUEIDENTIFIER": TypeInfo(name="UNIQUEIDENTIFIER", category="uuid",
            notes="16-byte GUID",
            mappings={"postgres": "UUID", "mysql": "CHAR(36)", "sqlite": "TEXT", "oracle": "RAW(16)"}),
        "XML": TypeInfo(name="XML", category="xml",
            notes="XML data with optional schema validation",
            mappings={"postgres": "XML", "mysql": "LONGTEXT", "sqlite": "TEXT", "oracle": "XMLTYPE"}),
        "GEOMETRY": TypeInfo(name="GEOMETRY", category="geometric",
            notes="Spatial geometry (planar)",
            mappings={"postgres": "GEOMETRY", "mysql": "GEOMETRY", "sqlite": "TEXT", "oracle": "SDO_GEOMETRY"}),
        "GEOGRAPHY": TypeInfo(name="GEOGRAPHY", category="geometric",
            notes="Spatial geography (geodetic)",
            mappings={"postgres": "GEOGRAPHY", "mysql": "GEOMETRY", "sqlite": "TEXT", "oracle": "SDO_GEOMETRY"}),
        "SQL_VARIANT": TypeInfo(name="SQL_VARIANT", category="special",
            notes="Stores values of various data types",
            mappings={"postgres": "TEXT", "mysql": "LONGTEXT", "sqlite": "TEXT", "oracle": "CLOB"}),
        "ROWVERSION": TypeInfo(name="ROWVERSION", aliases=["TIMESTAMP"], category="special",
            notes="Auto-generated binary(8), not a datetime",
            mappings={"postgres": "BYTEA", "mysql": "BINARY(8)", "sqlite": "BLOB", "oracle": "RAW(8)"}),
    }


def _oracle_types() -> dict[str, TypeInfo]:
    return {
        "NUMBER": TypeInfo(name="NUMBER", aliases=["NUMERIC", "DECIMAL", "DEC"], category="numeric",
            params="precision_scale", precision_max=38, scale_max=127,
            notes="Universal numeric type, precision 1-38",
            mappings={"postgres": "NUMERIC", "mysql": "DECIMAL", "sqlite": "NUMERIC", "sqlserver": "DECIMAL"}),
        "BINARY_FLOAT": TypeInfo(name="BINARY_FLOAT", category="numeric",
            notes="32-bit IEEE floating point",
            mappings={"postgres": "REAL", "mysql": "FLOAT", "sqlite": "REAL", "sqlserver": "REAL"}),
        "BINARY_DOUBLE": TypeInfo(name="BINARY_DOUBLE", category="numeric",
            notes="64-bit IEEE floating point",
            mappings={"postgres": "DOUBLE PRECISION", "mysql": "DOUBLE", "sqlite": "REAL", "sqlserver": "FLOAT"}),
        "INTEGER": TypeInfo(name="INTEGER", aliases=["INT", "SMALLINT"], category="numeric",
            notes="Alias for NUMBER(38), but typically used as NUMBER(10)",
            mappings={"postgres": "INTEGER", "mysql": "INT", "sqlite": "INTEGER", "sqlserver": "INT"}),
        "FLOAT": TypeInfo(name="FLOAT", category="numeric", params="length_optional",
            notes="ANSI float, actually NUMBER with binary precision",
            mappings={"postgres": "DOUBLE PRECISION", "mysql": "DOUBLE", "sqlite": "REAL", "sqlserver": "FLOAT"}),
        "VARCHAR2": TypeInfo(name="VARCHAR2", aliases=["VARCHAR"], category="string",
            params="length", max_size=32767,
            notes="Variable-length string (32767 in PL/SQL, 4000 in SQL)",
            mappings={"postgres": "CHARACTER VARYING", "mysql": "VARCHAR", "sqlite": "TEXT", "sqlserver": "NVARCHAR"}),
        "NVARCHAR2": TypeInfo(name="NVARCHAR2", aliases=["NVARCHAR"], category="string",
            params="length", max_size=16383, notes="Variable-length Unicode string",
            mappings={"postgres": "CHARACTER VARYING", "mysql": "VARCHAR", "sqlite": "TEXT", "sqlserver": "NVARCHAR"}),
        "CHAR": TypeInfo(name="CHAR", aliases=["CHARACTER"], category="string",
            params="length", max_size=2000, notes="Fixed-length string",
            mappings={"postgres": "CHARACTER", "mysql": "CHAR", "sqlite": "TEXT", "sqlserver": "CHAR"}),
        "NCHAR": TypeInfo(name="NCHAR", category="string", params="length", max_size=1000,
            notes="Fixed-length Unicode string",
            mappings={"postgres": "CHARACTER", "mysql": "CHAR", "sqlite": "TEXT", "sqlserver": "NCHAR"}),
        "CLOB": TypeInfo(name="CLOB", category="string",
            notes="Character Large Object, up to 4GB",
            mappings={"postgres": "TEXT", "mysql": "LONGTEXT", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)"}),
        "NCLOB": TypeInfo(name="NCLOB", category="string",
            notes="Unicode Character Large Object, up to 4GB",
            mappings={"postgres": "TEXT", "mysql": "LONGTEXT", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)"}),
        "LONG": TypeInfo(name="LONG", category="string",
            notes="Deprecated, up to 2GB character data",
            mappings={"postgres": "TEXT", "mysql": "LONGTEXT", "sqlite": "TEXT", "sqlserver": "NVARCHAR(MAX)"}),
        "DATE": TypeInfo(name="DATE", category="temporal",
            notes="Date AND time (to the second) - unlike other dialects",
            mappings={"postgres": "TIMESTAMP", "mysql": "DATETIME", "sqlite": "TEXT", "sqlserver": "DATETIME2"}),
        "TIMESTAMP": TypeInfo(name="TIMESTAMP", category="temporal",
            params="precision_scale", precision_max=9,
            notes="Date and time with fractional seconds",
            mappings={"postgres": "TIMESTAMP", "mysql": "DATETIME", "sqlite": "TEXT", "sqlserver": "DATETIME2"}),
        "TIMESTAMP WITH TIME ZONE": TypeInfo(name="TIMESTAMP WITH TIME ZONE", category="temporal",
            params="precision_scale", precision_max=9, notes="Timestamp with timezone info",
            mappings={"postgres": "TIMESTAMP WITH TIME ZONE", "mysql": "DATETIME", "sqlite": "TEXT", "sqlserver": "DATETIMEOFFSET"}),
        "TIMESTAMP WITH LOCAL TIME ZONE": TypeInfo(name="TIMESTAMP WITH LOCAL TIME ZONE", category="temporal",
            params="precision_scale", precision_max=9, notes="Stored as UTC, displayed in session timezone",
            mappings={"postgres": "TIMESTAMP WITH TIME ZONE", "mysql": "DATETIME", "sqlite": "TEXT", "sqlserver": "DATETIMEOFFSET"}),
        "INTERVAL YEAR TO MONTH": TypeInfo(name="INTERVAL YEAR TO MONTH", category="interval",
            notes="Year and month interval",
            mappings={"postgres": "INTERVAL", "mysql": "VARCHAR(255)", "sqlite": "TEXT", "sqlserver": "VARCHAR(255)"}),
        "INTERVAL DAY TO SECOND": TypeInfo(name="INTERVAL DAY TO SECOND", category="interval",
            notes="Day, hour, minute, second interval",
            mappings={"postgres": "INTERVAL", "mysql": "VARCHAR(255)", "sqlite": "TEXT", "sqlserver": "VARCHAR(255)"}),
        "RAW": TypeInfo(name="RAW", category="binary", params="length", max_size=32767,
            notes="Variable-length raw binary (32767 in PL/SQL, 2000 in SQL)",
            mappings={"postgres": "BYTEA", "mysql": "VARBINARY", "sqlite": "BLOB", "sqlserver": "VARBINARY"}),
        "LONG RAW": TypeInfo(name="LONG RAW", category="binary",
            notes="Deprecated, up to 2GB binary data",
            mappings={"postgres": "BYTEA", "mysql": "LONGBLOB", "sqlite": "BLOB", "sqlserver": "VARBINARY(MAX)"}),
        "BLOB": TypeInfo(name="BLOB", category="binary",
            notes="Binary Large Object, up to 4GB",
            mappings={"postgres": "BYTEA", "mysql": "LONGBLOB", "sqlite": "BLOB", "sqlserver": "VARBINARY(MAX)"}),
        "BFILE": TypeInfo(name="BFILE", category="binary",
            notes="Pointer to external binary file, up to 4GB",
            mappings={"postgres": "TEXT", "mysql": "VARCHAR(255)", "sqlite": "TEXT", "sqlserver": "VARCHAR(255)"}),
        "XMLTYPE": TypeInfo(name="XMLTYPE", category="xml",
            notes="XML data with XQuery support",
            mappings={"postgres": "XML", "mysql": "LONGTEXT", "sqlite": "TEXT", "sqlserver": "XML"}),
        "SDO_GEOMETRY": TypeInfo(name="SDO_GEOMETRY", category="geometric",
            notes="Oracle Spatial geometry object",
            mappings={"postgres": "GEOMETRY", "mysql": "GEOMETRY", "sqlite": "TEXT", "sqlserver": "GEOMETRY"}),
        "ROWID": TypeInfo(name="ROWID", category="special",
            notes="Physical row address",
            mappings={"postgres": "VARCHAR(18)", "mysql": "VARCHAR(18)", "sqlite": "TEXT", "sqlserver": "VARCHAR(18)"}),
        "UROWID": TypeInfo(name="UROWID", category="special",
            notes="Universal ROWID",
            mappings={"postgres": "VARCHAR(4000)", "mysql": "VARCHAR(4000)", "sqlite": "TEXT", "sqlserver": "VARCHAR(4000)"}),
    }


def build_registry() -> dict[str, dict[str, TypeInfo]]:
    return {
        "postgres": _pg_types(),
        "mysql": _mysql_types(),
        "sqlite": _sqlite_types(),
        "sqlserver": _sqlserver_types(),
        "oracle": _oracle_types(),
    }


REGISTRY = build_registry()


def get_type_info(dialect: str, type_name: str) -> TypeInfo | None:
    dialect = dialect.lower()
    type_name = type_name.upper().strip()
    if dialect not in REGISTRY:
        return None
    dialect_types = REGISTRY[dialect]
    if type_name in dialect_types:
        return dialect_types[type_name]
    for info in dialect_types.values():
        if type_name in info.aliases:
            return info
    return None


def list_types(dialect: str, category: str | None = None) -> list[TypeInfo]:
    dialect = dialect.lower()
    if dialect not in REGISTRY:
        return []
    types = list(REGISTRY[dialect].values())
    if category:
        types = [t for t in types if t.category == category.lower()]
    return types


def get_all_type_names(dialect: str) -> list[str]:
    dialect = dialect.lower()
    if dialect not in REGISTRY:
        return []
    names = []
    for info in REGISTRY[dialect].values():
        names.append(info.name)
        names.extend(info.aliases)
    return sorted(set(names))


# ============================================================
# Parser
# ============================================================

@dataclass
class ParsedType:
    """Result of parsing a SQL type string."""
    base_type: str
    params: list[str] = field(default_factory=list)
    unsigned: bool = False
    array_dims: int = 0
    raw: str = ""

    @property
    def param_str(self) -> str:
        if not self.params:
            return ""
        return "(" + ",".join(self.params) + ")"

    @property
    def full_name(self) -> str:
        result = self.base_type + self.param_str
        if self.unsigned:
            result += " UNSIGNED"
        if self.array_dims:
            result += "[]" * self.array_dims
        return result

    @property
    def length(self) -> Optional[int]:
        if self.params and self.params[0].isdigit():
            return int(self.params[0])
        return None

    @property
    def precision(self) -> Optional[int]:
        if self.params and self.params[0].isdigit():
            return int(self.params[0])
        return None

    @property
    def scale(self) -> Optional[int]:
        if len(self.params) > 1 and self.params[1].isdigit():
            return int(self.params[1])
        return None

    @property
    def has_max(self) -> bool:
        return bool(self.params) and self.params[0].upper() == "MAX"


_MULTI_WORD_TYPES = [
    "TIMESTAMP WITH LOCAL TIME ZONE",
    "TIMESTAMP WITH TIME ZONE",
    "TIMESTAMP WITHOUT TIME ZONE",
    "TIME WITH TIME ZONE",
    "TIME WITHOUT TIME ZONE",
    "INTERVAL YEAR TO MONTH",
    "INTERVAL DAY TO SECOND",
    "DOUBLE PRECISION",
    "CHARACTER VARYING",
    "BIT VARYING",
    "LONG RAW",
]

_PARAM_RE = re.compile(r"\(\s*([^)]+)\s*\)")
_ARRAY_RE = re.compile(r"(\[\])+$")


def parse_type(type_str: str) -> ParsedType:
    raw = type_str.strip()
    s = raw.upper()

    array_dims = 0
    array_match = _ARRAY_RE.search(s)
    if array_match:
        array_dims = array_match.group(0).count("[]")
        s = s[:array_match.start()].strip()

    params: list[str] = []
    param_match = _PARAM_RE.search(s)
    if param_match:
        param_str = param_match.group(1)
        params = [p.strip() for p in param_str.split(",")]
        s = s[:param_match.start()].strip() + s[param_match.end():].strip()

    unsigned = False
    if s.endswith(" UNSIGNED"):
        unsigned = True
        s = s[:-9].strip()
    elif s.endswith(" SIGNED"):
        s = s[:-7].strip()

    base_type = s.strip()
    for mw in _MULTI_WORD_TYPES:
        if base_type == mw or base_type.startswith(mw + " "):
            base_type = mw
            break

    return ParsedType(base_type=base_type, params=params, unsigned=unsigned,
                      array_dims=array_dims, raw=raw)


def normalize_type_name(type_str: str) -> str:
    return parse_type(type_str).base_type


# ============================================================
# Gotchas Database
# ============================================================

@dataclass
class Gotcha:
    id: str
    title: str
    description: str
    source_dialect: str
    target_dialect: str
    source_type: str
    target_type: str
    severity: str  # "info", "warning", "danger"
    workaround: str = ""


GOTCHAS: list[Gotcha] = [
    Gotcha(id="mysql-tinyint-bool", title="MySQL TINYINT(1) is used as BOOLEAN",
        description="MySQL's BOOLEAN/BOOL is just an alias for TINYINT(1). Values are 0/1, not TRUE/FALSE. ORMs often auto-convert TINYINT(1) columns to boolean fields, but the column can actually store -128 to 127.",
        source_dialect="mysql", target_dialect="postgres", source_type="TINYINT(1)", target_type="BOOLEAN", severity="warning",
        workaround="Add CHECK constraint to ensure only 0/1 values if needed."),
    Gotcha(id="mysql-tinyint-bool-sqlite", title="MySQL TINYINT(1) boolean to SQLite",
        description="SQLite has no native boolean type. MySQL TINYINT(1) columns used as booleans will map to INTEGER. Applications must handle 0/1 interpretation.",
        source_dialect="mysql", target_dialect="sqlite", source_type="TINYINT(1)", target_type="INTEGER", severity="info"),
    Gotcha(id="mysql-unsigned", title="MySQL UNSIGNED integers have no direct equivalent in PostgreSQL",
        description="PostgreSQL has no UNSIGNED integer types. A MySQL INT UNSIGNED (0 to 4294967295) needs BIGINT in PostgreSQL to preserve range. Using INTEGER loses the upper half of the range.",
        source_dialect="mysql", target_dialect="postgres", source_type="UNSIGNED", target_type="BIGINT", severity="warning",
        workaround="Use BIGINT in PostgreSQL or add CHECK (col >= 0) constraint."),
    Gotcha(id="mysql-unsigned-sqlserver", title="MySQL UNSIGNED integers in SQL Server",
        description="SQL Server has no UNSIGNED types. TINYINT is 0-255 (inherently unsigned), but SMALLINT/INT/BIGINT are all signed. Map carefully to preserve range.",
        source_dialect="mysql", target_dialect="sqlserver", source_type="UNSIGNED", target_type="INT", severity="warning"),
    Gotcha(id="mysql-enum", title="MySQL ENUM has no direct equivalent in most dialects",
        description="MySQL ENUM stores a predefined set of string values efficiently. PostgreSQL has CREATE TYPE ... AS ENUM, but other dialects need CHECK constraints or lookup tables.",
        source_dialect="mysql", target_dialect="any", source_type="ENUM", target_type="VARCHAR", severity="warning",
        workaround="Use CHECK constraint or lookup table in target dialect."),
    Gotcha(id="mysql-set", title="MySQL SET has no equivalent in other dialects",
        description="MySQL SET allows multiple values from a predefined list in one column. No other major dialect supports this. Typically requires a junction table or JSON column in the target.",
        source_dialect="mysql", target_dialect="any", source_type="SET", target_type="VARCHAR", severity="danger",
        workaround="Use a junction table or JSON array column."),
    Gotcha(id="mysql-timestamp-utc", title="MySQL TIMESTAMP auto-converts to UTC",
        description="MySQL TIMESTAMP stores values in UTC and converts to session timezone on retrieval. DATETIME does not. When migrating TIMESTAMP to PostgreSQL TIMESTAMP, decide whether you need TIMESTAMP or TIMESTAMPTZ.",
        source_dialect="mysql", target_dialect="postgres", source_type="TIMESTAMP", target_type="TIMESTAMP WITH TIME ZONE", severity="warning"),
    Gotcha(id="mysql-text-length", title="MySQL TEXT types have size limits; PostgreSQL TEXT is unlimited",
        description="MySQL TEXT is limited to 65,535 bytes. MEDIUMTEXT to 16MB. LONGTEXT to 4GB. PostgreSQL TEXT has no practical limit. Data that fits in PostgreSQL TEXT might need MEDIUMTEXT or LONGTEXT in MySQL.",
        source_dialect="postgres", target_dialect="mysql", source_type="TEXT", target_type="LONGTEXT", severity="warning",
        workaround="Choose the right MySQL TEXT variant based on expected data size."),
    Gotcha(id="mysql-year", title="MySQL YEAR has no equivalent in other dialects",
        description="MySQL YEAR type stores years 1901-2155 in a single byte. Other dialects use SMALLINT or similar. Range validation is lost.",
        source_dialect="mysql", target_dialect="any", source_type="YEAR", target_type="SMALLINT", severity="info"),
    Gotcha(id="pg-serial-not-type", title="PostgreSQL SERIAL is not a real type",
        description="SERIAL in PostgreSQL is shorthand that creates an INTEGER column + a sequence + a DEFAULT. It's not an actual data type. When migrating, you need the equivalent auto-increment mechanism, not just a type.",
        source_dialect="postgres", target_dialect="any", source_type="SERIAL", target_type="INT AUTO_INCREMENT", severity="warning"),
    Gotcha(id="pg-jsonb-vs-json", title="PostgreSQL JSONB vs JSON: binary vs text storage",
        description="PostgreSQL JSONB stores JSON in decomposed binary format for fast indexing and querying. JSON stores exact text. MySQL JSON is similar to JSONB (binary). Other dialects store JSON as text, losing query capabilities.",
        source_dialect="postgres", target_dialect="any", source_type="JSONB", target_type="JSON", severity="warning",
        workaround="Accept loss of binary JSON benefits, or use application-level JSON handling."),
    Gotcha(id="pg-array-no-equiv", title="PostgreSQL arrays have no equivalent in most dialects",
        description="PostgreSQL supports typed arrays (INTEGER[], TEXT[][]). No other major dialect has native array columns. Must use JSON, comma-separated text, or junction tables.",
        source_dialect="postgres", target_dialect="any", source_type="ARRAY", target_type="JSON", severity="danger",
        workaround="Use JSON column or junction table."),
    Gotcha(id="pg-money-locale", title="PostgreSQL MONEY type is locale-dependent",
        description="PostgreSQL MONEY type formatting depends on the lc_monetary locale setting. This can cause issues when migrating between servers or to other dialects. DECIMAL(19,4) is a safer alternative.",
        source_dialect="postgres", target_dialect="any", source_type="MONEY", target_type="DECIMAL(19,4)", severity="warning",
        workaround="Use DECIMAL(19,4) instead of MONEY for portability."),
    Gotcha(id="pg-interval", title="PostgreSQL INTERVAL has no equivalent in MySQL",
        description="PostgreSQL INTERVAL stores time spans with rich arithmetic. MySQL has INTERVAL syntax in expressions but no INTERVAL column type. Must store as VARCHAR or decompose into numeric fields.",
        source_dialect="postgres", target_dialect="mysql", source_type="INTERVAL", target_type="VARCHAR(255)", severity="danger",
        workaround="Store as VARCHAR or separate numeric columns (years, months, days, etc.)."),
    Gotcha(id="sqlite-dynamic-typing", title="SQLite uses dynamic typing (type affinity)",
        description="SQLite does not enforce column types. Any column can store any type of value. The declared type only influences the preferred storage class (type affinity). This means data that is 'correct' in SQLite might violate constraints in strictly-typed databases.",
        source_dialect="sqlite", target_dialect="any", source_type="ANY", target_type="ANY", severity="danger",
        workaround="Validate data types during migration. Clean data before inserting into target."),
    Gotcha(id="sqlite-integer-primary-key", title="SQLite INTEGER PRIMARY KEY is special",
        description="In SQLite, INTEGER PRIMARY KEY is the rowid alias and auto-increments. This is different from INT PRIMARY KEY (which does NOT alias the rowid). AUTOINCREMENT keyword adds monotonic guarantee but is slower.",
        source_dialect="sqlite", target_dialect="any", source_type="INTEGER", target_type="INT", severity="warning",
        workaround="Use target dialect's auto-increment mechanism (SERIAL, IDENTITY, etc.)."),
    Gotcha(id="sqlserver-nvarchar-unicode", title="SQL Server NVARCHAR vs VARCHAR: Unicode matters",
        description="SQL Server VARCHAR stores non-Unicode data (1 byte/char). NVARCHAR stores Unicode data (2 bytes/char). PostgreSQL and MySQL default to UTF-8, so VARCHAR there is already Unicode-capable. Mapping SQL Server VARCHAR to PostgreSQL VARCHAR may lose non-ASCII characters if the SQL Server column uses a non-UTF8 collation.",
        source_dialect="sqlserver", target_dialect="postgres", source_type="VARCHAR", target_type="CHARACTER VARYING", severity="warning",
        workaround="Use NVARCHAR in SQL Server or verify collation supports needed characters."),
    Gotcha(id="sqlserver-datetime-legacy", title="SQL Server DATETIME has limited precision",
        description="SQL Server DATETIME rounds to .000, .003, or .007 seconds (3.33ms). DATETIME2 has 100ns precision. Always prefer DATETIME2 for new columns.",
        source_dialect="sqlserver", target_dialect="any", source_type="DATETIME", target_type="TIMESTAMP", severity="info"),
    Gotcha(id="sqlserver-bit-boolean", title="SQL Server BIT is 0, 1, or NULL (not a bit field)",
        description="SQL Server BIT is a boolean type (0/1/NULL), not a variable-length bit field like PostgreSQL BIT or MySQL BIT(n). Multiple BIT columns in a row share storage bytes.",
        source_dialect="sqlserver", target_dialect="postgres", source_type="BIT", target_type="BOOLEAN", severity="info"),
    Gotcha(id="sqlserver-max-keyword", title="SQL Server MAX keyword has no direct equivalent",
        description="SQL Server uses VARCHAR(MAX), NVARCHAR(MAX), VARBINARY(MAX) for large data (up to 2GB). PostgreSQL uses TEXT/BYTEA. MySQL uses LONGTEXT/LONGBLOB. The 'MAX' keyword itself doesn't translate.",
        source_dialect="sqlserver", target_dialect="any", source_type="MAX", target_type="TEXT", severity="info"),
    Gotcha(id="sqlserver-rowversion", title="SQL Server ROWVERSION/TIMESTAMP is not a datetime",
        description="SQL Server's TIMESTAMP (alias ROWVERSION) is a binary counter for optimistic concurrency, NOT a date/time type. It auto-increments on row modification. No direct equivalent in other dialects.",
        source_dialect="sqlserver", target_dialect="any", source_type="ROWVERSION", target_type="BYTEA", severity="danger",
        workaround="Use trigger-based versioning or application-level concurrency control."),
    Gotcha(id="oracle-number-universal", title="Oracle NUMBER is the universal numeric type",
        description="Oracle uses NUMBER(p,s) for all exact numerics. NUMBER without precision is a floating-point number. NUMBER(10) is an integer. NUMBER(10,2) is a decimal. Mapping to specific types in other dialects requires examining the precision and scale.",
        source_dialect="oracle", target_dialect="any", source_type="NUMBER", target_type="DECIMAL", severity="warning",
        workaround="Map based on precision: NUMBER(5)->SMALLINT, NUMBER(10)->INT, NUMBER(19)->BIGINT, NUMBER(p,s)->DECIMAL(p,s)."),
    Gotcha(id="oracle-date-has-time", title="Oracle DATE includes time component",
        description="Unlike all other major dialects, Oracle DATE stores both date AND time (to the second). PostgreSQL/MySQL/SQL Server DATE is date-only. Migrating Oracle DATE to other dialects may lose the time component.",
        source_dialect="oracle", target_dialect="any", source_type="DATE", target_type="TIMESTAMP", severity="danger",
        workaround="Map Oracle DATE to TIMESTAMP or DATETIME, not DATE."),
    Gotcha(id="oracle-varchar2-byte-vs-char", title="Oracle VARCHAR2 length semantics: BYTE vs CHAR",
        description="Oracle VARCHAR2(100) can mean 100 bytes or 100 characters, depending on NLS_LENGTH_SEMANTICS. With multi-byte character sets, BYTE semantics can truncate data. Other dialects typically use character-length semantics.",
        source_dialect="oracle", target_dialect="any", source_type="VARCHAR2", target_type="VARCHAR", severity="warning",
        workaround="Use VARCHAR2(100 CHAR) explicitly in Oracle, or verify NLS_LENGTH_SEMANTICS."),
    Gotcha(id="oracle-no-boolean", title="Oracle has no BOOLEAN type in SQL (pre-23c)",
        description="Oracle SQL (before 23c) has no BOOLEAN type. The convention is to use NUMBER(1) with values 0/1, or CHAR(1) with 'Y'/'N'. Oracle 23c adds BOOLEAN.",
        source_dialect="any", target_dialect="oracle", source_type="BOOLEAN", target_type="NUMBER(1)", severity="warning",
        workaround="Use NUMBER(1) with CHECK constraint (0/1) in Oracle pre-23c."),
    Gotcha(id="oracle-empty-string-null", title="Oracle treats empty string as NULL",
        description="In Oracle, '' (empty string) is treated as NULL. This differs from every other dialect where '' and NULL are distinct. VARCHAR2 columns cannot store truly empty strings.",
        source_dialect="any", target_dialect="oracle", source_type="VARCHAR", target_type="VARCHAR2", severity="danger",
        workaround="Use a sentinel value or redesign to avoid empty strings."),
    Gotcha(id="varchar-max-length-varies", title="VARCHAR maximum length varies across dialects",
        description="VARCHAR max length: PostgreSQL=10MB, MySQL=65535 bytes (row limit), SQL Server=8000 (or MAX for 2GB), Oracle=4000 bytes (32767 in extended). A VARCHAR(8000) in SQL Server needs different treatment in MySQL.",
        source_dialect="any", target_dialect="any", source_type="VARCHAR", target_type="VARCHAR", severity="warning"),
    Gotcha(id="decimal-precision-varies", title="DECIMAL max precision varies across dialects",
        description="Max DECIMAL precision: PostgreSQL=1000, MySQL=65, SQL Server=38, Oracle=38. A DECIMAL(65,30) in MySQL cannot be represented in SQL Server or Oracle without truncation.",
        source_dialect="any", target_dialect="any", source_type="DECIMAL", target_type="DECIMAL", severity="warning"),
    Gotcha(id="timestamp-precision-varies", title="Timestamp fractional seconds precision varies",
        description="Fractional seconds: PostgreSQL=6 (microseconds), MySQL=6, SQL Server=7 (100ns), Oracle=9 (nanoseconds). Migrating from Oracle/SQL Server to PostgreSQL/MySQL may lose sub-microsecond precision.",
        source_dialect="any", target_dialect="any", source_type="TIMESTAMP", target_type="TIMESTAMP", severity="info"),
]


def get_gotchas(source_dialect: str | None = None, target_dialect: str | None = None,
                type_name: str | None = None) -> list[Gotcha]:
    results = []
    for g in GOTCHAS:
        if source_dialect:
            if g.source_dialect != "any" and g.source_dialect != source_dialect.lower():
                continue
        if target_dialect:
            if g.target_dialect != "any" and g.target_dialect != target_dialect.lower():
                continue
        if type_name:
            tn = type_name.upper()
            if tn not in g.source_type.upper() and tn not in g.target_type.upper():
                continue
        results.append(g)
    return results


def get_gotchas_for_mapping(source_dialect: str, target_dialect: str,
                            source_type: str, target_type: str) -> list[Gotcha]:
    results = []
    src = source_type.upper()
    tgt = target_type.upper()
    sd = source_dialect.lower()
    td = target_dialect.lower()
    for g in GOTCHAS:
        dialect_match = (
            (g.source_dialect == "any" or g.source_dialect == sd)
            and (g.target_dialect == "any" or g.target_dialect == td)
        )
        if not dialect_match:
            continue
        gsrc = g.source_type.upper()
        gsrc_base = gsrc.split("(")[0].strip()
        src_base = src.split("(")[0].strip()
        source_match = (
            gsrc == "ANY" or gsrc_base == src_base or gsrc in src or src.startswith(gsrc_base)
        )
        if not source_match:
            gtgt = g.target_type.upper()
            gtgt_base = gtgt.split("(")[0].strip()
            tgt_base = tgt.split("(")[0].strip()
            target_match = gtgt_base == tgt_base or gtgt in tgt
            if not target_match or gsrc_base != src_base:
                continue
        results.append(g)
    return results


# ============================================================
# Mapper
# ============================================================

@dataclass
class MappingResult:
    source_dialect: str
    target_dialect: str
    source_type: str
    source_parsed: ParsedType
    source_info: TypeInfo | None
    target_type: str
    target_info: TypeInfo | None
    warnings: list[str] = field(default_factory=list)
    gotchas: list[Gotcha] = field(default_factory=list)
    notes: str = ""
    confidence: str = "high"

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings) or bool(self.gotchas)


@dataclass
class CompareResult:
    type_name: str
    parsed: ParsedType
    mappings: dict[str, MappingResult]


def map_type(type_str: str, source_dialect: str, target_dialect: str) -> MappingResult:
    source_dialect = source_dialect.lower()
    target_dialect = target_dialect.lower()
    parsed = parse_type(type_str)
    warnings: list[str] = []

    if source_dialect not in DIALECTS:
        return MappingResult(source_dialect=source_dialect, target_dialect=target_dialect,
            source_type=type_str, source_parsed=parsed, source_info=None,
            target_type="UNKNOWN", target_info=None,
            warnings=[f"Unknown source dialect: {source_dialect}"], confidence="low")
    if target_dialect not in DIALECTS:
        return MappingResult(source_dialect=source_dialect, target_dialect=target_dialect,
            source_type=type_str, source_parsed=parsed, source_info=None,
            target_type="UNKNOWN", target_info=None,
            warnings=[f"Unknown target dialect: {target_dialect}"], confidence="low")

    if parsed.array_dims > 0:
        base_result = map_type(parsed.base_type + parsed.param_str, source_dialect, target_dialect)
        if target_dialect == "postgres":
            target_type = base_result.target_type + "[]" * parsed.array_dims
        else:
            target_type = "JSON" if target_dialect == "mysql" else "TEXT"
            warnings.append(f"Array type {parsed.full_name} has no native equivalent. Using {target_type} instead.")
        return MappingResult(source_dialect=source_dialect, target_dialect=target_dialect,
            source_type=type_str, source_parsed=parsed,
            source_info=base_result.source_info, target_type=target_type,
            target_info=base_result.target_info,
            warnings=base_result.warnings + warnings, gotchas=base_result.gotchas,
            confidence="medium" if warnings else base_result.confidence)

    source_info = get_type_info(source_dialect, parsed.base_type)
    if source_info is None:
        return MappingResult(source_dialect=source_dialect, target_dialect=target_dialect,
            source_type=type_str, source_parsed=parsed, source_info=None,
            target_type="UNKNOWN", target_info=None,
            warnings=[f"Type '{parsed.base_type}' not found in {source_dialect} registry"],
            confidence="low")

    if source_dialect == target_dialect:
        return MappingResult(source_dialect=source_dialect, target_dialect=target_dialect,
            source_type=type_str, source_parsed=parsed,
            source_info=source_info, target_type=parsed.full_name,
            target_info=source_info, confidence="high")

    if target_dialect not in source_info.mappings:
        return MappingResult(source_dialect=source_dialect, target_dialect=target_dialect,
            source_type=type_str, source_parsed=parsed,
            source_info=source_info, target_type="UNKNOWN", target_info=None,
            warnings=[f"No mapping defined for {parsed.base_type} -> {target_dialect}"],
            confidence="low")

    raw_target = source_info.mappings[target_dialect]
    target_info = get_type_info(target_dialect, raw_target.split("(")[0].split(" ")[0])

    target_type = _build_target_type(parsed, source_info, raw_target, target_info,
                                     source_dialect, target_dialect, warnings)

    if parsed.unsigned and target_dialect != "mysql":
        warnings.append(f"{target_dialect} does not support UNSIGNED integers. "
                        "Consider using a larger type or adding a CHECK constraint.")

    _check_size_warnings(parsed, source_info, target_info, target_dialect, warnings)

    gotchas = get_gotchas_for_mapping(source_dialect, target_dialect,
                                      parsed.full_name, target_type)

    confidence = "high"
    if warnings:
        confidence = "medium"
    if any(g.severity == "danger" for g in gotchas):
        confidence = "low"

    return MappingResult(source_dialect=source_dialect, target_dialect=target_dialect,
        source_type=type_str, source_parsed=parsed,
        source_info=source_info, target_type=target_type,
        target_info=target_info, warnings=warnings,
        gotchas=gotchas, confidence=confidence)


def _build_target_type(parsed, source_info, raw_target, target_info,
                       source_dialect, target_dialect, warnings):
    if "(" in raw_target:
        return raw_target
    base_target = raw_target
    if parsed.params and target_info and target_info.params != "none":
        params = _adjust_params(parsed, source_info, target_info, warnings)
        if params:
            base_target = raw_target + "(" + ",".join(params) + ")"
    elif parsed.params and parsed.has_max:
        if target_dialect == "postgres":
            pass
        elif target_dialect == "mysql":
            pass
        else:
            base_target = raw_target + "(MAX)"
    return base_target


def _adjust_params(parsed, source_info, target_info, warnings):
    params = list(parsed.params)
    if parsed.has_max:
        return []
    if params and params[0].isdigit():
        val = int(params[0])
        if target_info.max_size and val > target_info.max_size:
            warnings.append(f"Length {val} exceeds {target_info.name} maximum of {target_info.max_size}. Truncating to {target_info.max_size}.")
            params[0] = str(target_info.max_size)
        if target_info.precision_max and val > target_info.precision_max:
            warnings.append(f"Precision {val} exceeds {target_info.name} maximum of {target_info.precision_max}. Truncating to {target_info.precision_max}.")
            params[0] = str(target_info.precision_max)
    if len(params) > 1 and params[1].isdigit():
        val = int(params[1])
        if target_info.scale_max and val > target_info.scale_max:
            warnings.append(f"Scale {val} exceeds {target_info.name} maximum of {target_info.scale_max}. Truncating to {target_info.scale_max}.")
            params[1] = str(target_info.scale_max)
    return params


def _check_size_warnings(parsed, source_info, target_info, target_dialect, warnings):
    if target_info is None:
        return
    if (source_info.max_size and target_info.max_size
            and source_info.max_size > target_info.max_size):
        if parsed.length and parsed.length > target_info.max_size:
            warnings.append(f"Source length {parsed.length} exceeds target max of {target_info.max_size} in {target_dialect}.")
    if (source_info.precision_max and target_info.precision_max
            and source_info.precision_max > target_info.precision_max):
        if parsed.precision and parsed.precision > target_info.precision_max:
            warnings.append(f"Source precision {parsed.precision} exceeds target max of {target_info.precision_max} in {target_dialect}.")


def compare_type(type_str: str, base_dialect: str | None = None) -> CompareResult:
    parsed = parse_type(type_str)
    if base_dialect is None:
        base_dialect = _detect_dialect(parsed.base_type)
    mappings: dict[str, MappingResult] = {}
    for dialect in DIALECTS:
        if dialect == base_dialect:
            mappings[dialect] = MappingResult(
                source_dialect=base_dialect, target_dialect=dialect,
                source_type=type_str, source_parsed=parsed,
                source_info=get_type_info(base_dialect, parsed.base_type),
                target_type=parsed.full_name,
                target_info=get_type_info(dialect, parsed.base_type),
                confidence="high", notes="Source dialect")
        else:
            mappings[dialect] = map_type(type_str, base_dialect, dialect)
    return CompareResult(type_name=type_str, parsed=parsed, mappings=mappings)


def _detect_dialect(type_name: str) -> str:
    type_name = type_name.upper()
    pg_only = {"BYTEA", "JSONB", "SERIAL", "BIGSERIAL", "SMALLSERIAL",
               "INET", "CIDR", "MACADDR", "TSVECTOR", "TSQUERY", "OID",
               "TIMESTAMPTZ", "TIMETZ"}
    mysql_only = {"TINYINT", "MEDIUMINT", "TINYTEXT", "MEDIUMTEXT",
                  "LONGTEXT", "TINYBLOB", "MEDIUMBLOB", "LONGBLOB",
                  "ENUM", "SET", "YEAR"}
    sqlserver_only = {"NVARCHAR", "NCHAR", "NTEXT", "DATETIME2",
                      "DATETIMEOFFSET", "SMALLDATETIME", "SMALLMONEY",
                      "UNIQUEIDENTIFIER", "SQL_VARIANT", "ROWVERSION",
                      "IMAGE", "GEOGRAPHY"}
    oracle_only = {"VARCHAR2", "NVARCHAR2", "NUMBER", "BINARY_FLOAT",
                   "BINARY_DOUBLE", "CLOB", "NCLOB", "BFILE", "XMLTYPE",
                   "SDO_GEOMETRY", "ROWID", "UROWID", "LONG RAW"}
    if type_name in pg_only:
        return "postgres"
    if type_name in mysql_only:
        return "mysql"
    if type_name in sqlserver_only:
        return "sqlserver"
    if type_name in oracle_only:
        return "oracle"
    return "postgres"


# ============================================================
# CLI
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="sql-type-mapper",
        description="Map SQL types between database dialects.",
    )
    parser.add_argument("type", help='SQL type string (e.g., "VARCHAR(255)")')
    parser.add_argument("--from", dest="source", required=True, choices=DIALECTS,
                        help="Source dialect")
    parser.add_argument("--to", dest="target", required=True, choices=DIALECTS,
                        help="Target dialect")

    args = parser.parse_args()
    result = map_type(args.type, args.source, args.target)

    print(f"Source: {result.source_type} ({result.source_dialect})")
    print(f"Target: {result.target_type} ({result.target_dialect})")
    print(f"Confidence: {result.confidence}")

    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"  ! {w}")

    if result.gotchas:
        print("\nGotchas:")
        for g in result.gotchas:
            marker = "[!!!]" if g.severity == "danger" else ("[!!]" if g.severity == "warning" else "[i]")
            print(f"  {marker} {g.title}")
            print(f"       {g.description[:100]}...")
            if g.workaround:
                print(f"       Workaround: {g.workaround[:80]}")


if __name__ == "__main__":
    main()
