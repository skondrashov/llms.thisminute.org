"""
chmod Calculator — Convert, Explain, and Query Unix File Permissions

Converts between numeric (octal) and symbolic (rwxr-xr-x) chmod formats,
explains permissions in plain English, answers natural-language queries
about who can do what, and provides common permission presets.

Handles all 4096 basic modes (000-777) plus special bits:
- setuid (4xxx): s/S in owner execute position
- setgid (2xxx): s/S in group execute position
- sticky (1xxx): t/T in others execute position

Pure Python, no external dependencies.

Usage:
    python calculator.py convert 755
    python calculator.py convert rwxr-xr-x
    python calculator.py explain 755
    python calculator.py query 755 "who can write?"
    python calculator.py common
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass


# ===================================================================
# Converter — numeric <-> symbolic
# ===================================================================

# Permission bit constants
OWNER_READ = 0o400
OWNER_WRITE = 0o200
OWNER_EXEC = 0o100
GROUP_READ = 0o040
GROUP_WRITE = 0o020
GROUP_EXEC = 0o010
OTHER_READ = 0o004
OTHER_WRITE = 0o002
OTHER_EXEC = 0o001

SETUID = 0o4000
SETGID = 0o2000
STICKY = 0o1000

# Maps a 3-bit permission value (0-7) to its rwx string
_PERM_STRINGS = {
    0: "---",
    1: "--x",
    2: "-w-",
    3: "-wx",
    4: "r--",
    5: "r-x",
    6: "rw-",
    7: "rwx",
}

# Reverse: symbolic triplet to octal digit
_PERM_VALUES = {v: k for k, v in _PERM_STRINGS.items()}


def numeric_to_symbolic(mode: int | str) -> str:
    """Convert a numeric mode (e.g., 755 or 0o755) to symbolic (e.g., 'rwxr-xr-x').

    For modes with special bits, the result includes s/S/t/T notation:
    - setuid + owner execute  -> 's' in position 2
    - setuid + no owner exec  -> 'S' in position 2
    - setgid + group execute  -> 's' in position 5
    - setgid + no group exec  -> 'S' in position 5
    - sticky + others execute -> 't' in position 8
    - sticky + no others exec -> 'T' in position 8

    Args:
        mode: Octal mode as int (0o755) or string ("755", "0755", "4755").

    Returns:
        Symbolic string like 'rwxr-xr-x' (9 chars) or 'rwsr-xr-t' (with specials).

    Raises:
        ValueError: If mode is out of range or not a valid octal string.
    """
    mode = _normalize_mode(mode)
    _validate_mode(mode)

    owner = (mode >> 6) & 0o7
    group = (mode >> 3) & 0o7
    other = mode & 0o7

    owner_str = list(_PERM_STRINGS[owner])
    group_str = list(_PERM_STRINGS[group])
    other_str = list(_PERM_STRINGS[other])

    # Apply special bits
    if mode & SETUID:
        owner_str[2] = "s" if owner_str[2] == "x" else "S"
    if mode & SETGID:
        group_str[2] = "s" if group_str[2] == "x" else "S"
    if mode & STICKY:
        other_str[2] = "t" if other_str[2] == "x" else "T"

    return "".join(owner_str) + "".join(group_str) + "".join(other_str)


def symbolic_to_numeric(symbolic: str) -> int:
    """Convert a symbolic mode string (e.g., 'rwxr-xr-x') to numeric (e.g., 0o755).

    Handles special bit notation (s/S/t/T).

    Args:
        symbolic: 9-character symbolic string like 'rwxr-xr-x'.

    Returns:
        Octal mode as integer (e.g., 0o755).

    Raises:
        ValueError: If symbolic string is invalid.
    """
    symbolic = symbolic.strip()
    if len(symbolic) != 9:
        raise ValueError(
            f"Symbolic mode must be exactly 9 characters, got {len(symbolic)}: '{symbolic}'"
        )

    owner_str = symbolic[0:3]
    group_str = symbolic[3:6]
    other_str = symbolic[6:9]

    mode = 0

    # Parse owner
    owner_bits, has_setuid = _parse_triplet(owner_str, "owner")
    mode |= owner_bits << 6
    if has_setuid:
        mode |= SETUID

    # Parse group
    group_bits, has_setgid = _parse_triplet(group_str, "group")
    mode |= group_bits << 3
    if has_setgid:
        mode |= SETGID

    # Parse other
    other_bits, has_sticky = _parse_triplet(other_str, "other")
    mode |= other_bits
    if has_sticky:
        mode |= STICKY

    return mode


def _parse_triplet(triplet: str, which: str) -> tuple[int, bool]:
    """Parse a 3-character permission triplet, returning (basic_bits, has_special)."""
    if len(triplet) != 3:
        raise ValueError(f"Permission triplet must be 3 chars, got: '{triplet}'")

    r_char, w_char, x_char = triplet[0], triplet[1], triplet[2]

    if r_char not in ("r", "-"):
        raise ValueError(
            f"Invalid read character '{r_char}' in {which} permissions"
        )
    if w_char not in ("w", "-"):
        raise ValueError(
            f"Invalid write character '{w_char}' in {which} permissions"
        )

    value = 0
    if r_char == "r":
        value |= 4
    if w_char == "w":
        value |= 2

    has_special = False

    if which == "owner":
        valid_exec = ("x", "-", "s", "S")
        if x_char not in valid_exec:
            raise ValueError(
                f"Invalid execute character '{x_char}' in {which} permissions"
            )
        if x_char == "x":
            value |= 1
        elif x_char == "s":
            value |= 1
            has_special = True
        elif x_char == "S":
            has_special = True
    elif which == "group":
        valid_exec = ("x", "-", "s", "S")
        if x_char not in valid_exec:
            raise ValueError(
                f"Invalid execute character '{x_char}' in {which} permissions"
            )
        if x_char == "x":
            value |= 1
        elif x_char == "s":
            value |= 1
            has_special = True
        elif x_char == "S":
            has_special = True
    elif which == "other":
        valid_exec = ("x", "-", "t", "T")
        if x_char not in valid_exec:
            raise ValueError(
                f"Invalid execute character '{x_char}' in {which} permissions"
            )
        if x_char == "x":
            value |= 1
        elif x_char == "t":
            value |= 1
            has_special = True
        elif x_char == "T":
            has_special = True

    return value, has_special


def parse_mode(mode_str: str) -> int:
    """Parse a mode from either numeric or symbolic format.

    Accepts:
    - Numeric strings: '755', '0755', '4755', '0o755'
    - Symbolic strings: 'rwxr-xr-x', 'rwsr-xr-t'

    Returns:
        Integer mode value.

    Raises:
        ValueError: If mode_str is not a recognized format.
    """
    mode_str = mode_str.strip()
    if _looks_symbolic(mode_str):
        return symbolic_to_numeric(mode_str)
    return _normalize_mode(mode_str)


def format_numeric(mode: int) -> str:
    """Format a mode as an octal string.

    Returns '755' for basic modes or '4755' for modes with special bits.
    """
    if mode > 0o777:
        return format(mode, "04o")
    return format(mode, "03o")


def _normalize_mode(mode: int | str) -> int:
    """Normalize mode input to an integer."""
    if isinstance(mode, int):
        return mode
    if isinstance(mode, str):
        mode = mode.strip()
        if mode.startswith("0o") or mode.startswith("0O"):
            return int(mode, 8)
        if re.match(r"^[0-7]{1,4}$", mode):
            return int(mode, 8)
        raise ValueError(
            f"Invalid numeric mode: '{mode}'. Expected octal digits (0-7), "
            f"e.g., '755' or '4755'."
        )
    raise TypeError(f"Expected int or str, got {type(mode).__name__}")


def _validate_mode(mode: int) -> None:
    """Validate that a mode is in the legal range [0, 0o7777]."""
    if not (0 <= mode <= 0o7777):
        raise ValueError(
            f"Mode {oct(mode)} is out of range. Must be between 0o0000 and 0o7777."
        )


def _looks_symbolic(s: str) -> bool:
    """Heuristic check: does this string look like a symbolic mode?"""
    if len(s) != 9:
        return False
    valid_chars = set("rwxsStT-")
    return all(c in valid_chars for c in s)


# ===================================================================
# Explainer — plain English explanations
# ===================================================================

def explain(mode: int | str) -> str:
    """Return a full plain-English explanation of a permission mode.

    Args:
        mode: Permission mode as int, numeric string, or symbolic string.

    Returns:
        Multi-line string explaining all permissions.
    """
    if isinstance(mode, str):
        mode = parse_mode(mode)

    symbolic = numeric_to_symbolic(mode)
    numeric_str = format_numeric(mode)

    lines = [
        f"Mode: {numeric_str} ({symbolic})",
        "",
    ]

    owner = (mode >> 6) & 0o7
    group = (mode >> 3) & 0o7
    other = mode & 0o7

    lines.append(f"  Owner:  {_describe_permissions(owner)}")
    lines.append(f"  Group:  {_describe_permissions(group)}")
    lines.append(f"  Others: {_describe_permissions(other)}")

    specials = _describe_special_bits(mode)
    if specials:
        lines.append("")
        for desc in specials:
            lines.append(f"  Special: {desc}")

    return "\n".join(lines)


def explain_owner(mode: int) -> str:
    """Explain what the owner can do."""
    owner = (mode >> 6) & 0o7
    return _describe_permissions(owner)


def explain_group(mode: int) -> str:
    """Explain what the group can do."""
    group = (mode >> 3) & 0o7
    return _describe_permissions(group)


def explain_others(mode: int) -> str:
    """Explain what others can do."""
    other = mode & 0o7
    return _describe_permissions(other)


def _describe_permissions(bits: int) -> str:
    """Describe a 3-bit permission value in plain English."""
    perms = []
    if bits & 4:
        perms.append("read")
    if bits & 2:
        perms.append("write")
    if bits & 1:
        perms.append("execute")

    if not perms:
        return "no permissions"
    if len(perms) == 1:
        return perms[0]
    if len(perms) == 2:
        return f"{perms[0]} and {perms[1]}"
    return f"{perms[0]}, {perms[1]}, and {perms[2]}"


def _describe_special_bits(mode: int) -> list[str]:
    """Describe any special bits set on the mode."""
    descriptions = []
    if mode & SETUID:
        descriptions.append(
            "setuid is set \u2014 when executed, the process runs as the file owner"
        )
    if mode & SETGID:
        descriptions.append(
            "setgid is set \u2014 when executed, the process runs as the file group; "
            "on directories, new files inherit the directory's group"
        )
    if mode & STICKY:
        descriptions.append(
            "sticky bit is set \u2014 on directories, only the file owner can delete "
            "or rename files"
        )
    return descriptions


def get_permission_list(bits: int) -> list[str]:
    """Return a list of permission names for a 3-bit permission value."""
    perms = []
    if bits & 4:
        perms.append("read")
    if bits & 2:
        perms.append("write")
    if bits & 1:
        perms.append("execute")
    return perms


# ===================================================================
# Query — natural language permission queries
# ===================================================================

# Map of class names to bit shift offsets
_CLASS_SHIFTS = {
    "owner": 6,
    "group": 3,
    "others": 0,
    "other": 0,
}

# Map of permission names to bit values within a triplet
_PERM_BITS = {
    "read": 4,
    "write": 2,
    "execute": 1,
    "exec": 1,
}

# Map of special bit names to their masks
_SPECIAL_BITS = {
    "setuid": SETUID,
    "suid": SETUID,
    "setgid": SETGID,
    "sgid": SETGID,
    "sticky": STICKY,
    "sticky bit": STICKY,
}


def query(mode: int | str, question: str) -> str:
    """Answer a natural-language question about a permission mode.

    Args:
        mode: Permission mode (int, numeric string, or symbolic string).
        question: Natural language question.

    Returns:
        Plain English answer.
    """
    if isinstance(mode, str):
        mode = parse_mode(mode)

    question = question.strip().lower().rstrip("?").strip()

    # Try "is [special] set?"
    special_answer = _try_special_query(mode, question)
    if special_answer is not None:
        return special_answer

    # Try "can [class] [permission]?"
    can_answer = _try_can_query(mode, question)
    if can_answer is not None:
        return can_answer

    # Try "who can [permission]?"
    who_answer = _try_who_query(mode, question)
    if who_answer is not None:
        return who_answer

    return (
        "Sorry, I didn't understand that question. Try:\n"
        '  "who can read?"\n'
        '  "can owner write?"\n'
        '  "is setuid set?"'
    )


def who_can(mode: int, permission: str) -> list[str]:
    """Return which classes have the given permission."""
    perm_bit = _PERM_BITS.get(permission.lower())
    if perm_bit is None:
        raise ValueError(f"Unknown permission: '{permission}'")

    result = []
    for cls_name, shift in [("owner", 6), ("group", 3), ("others", 0)]:
        triplet = (mode >> shift) & 0o7
        if triplet & perm_bit:
            result.append(cls_name)
    return result


def can_class(mode: int, cls: str, permission: str) -> bool:
    """Check if a specific class has a specific permission."""
    cls = cls.lower()
    if cls == "other":
        cls = "others"
    shift = _CLASS_SHIFTS.get(cls)
    if shift is None:
        raise ValueError(f"Unknown class: '{cls}'")

    perm_bit = _PERM_BITS.get(permission.lower())
    if perm_bit is None:
        raise ValueError(f"Unknown permission: '{permission}'")

    triplet = (mode >> shift) & 0o7
    return bool(triplet & perm_bit)


def is_special_set(mode: int, special: str) -> bool:
    """Check if a special bit is set."""
    mask = _SPECIAL_BITS.get(special.lower())
    if mask is None:
        raise ValueError(f"Unknown special bit: '{special}'")
    return bool(mode & mask)


def _try_special_query(mode: int, question: str) -> str | None:
    """Try to parse 'is [special] set' queries."""
    m = re.match(r"is\s+(setuid|suid|setgid|sgid|sticky|sticky\s*bit)\s+set", question)
    if m:
        special_name = m.group(1).strip()
        mask = _SPECIAL_BITS.get(special_name)
        if mask is None:
            return None
        if mode & mask:
            return f"Yes, {_canonical_special_name(special_name)} is set."
        else:
            return f"No, {_canonical_special_name(special_name)} is not set."
    return None


def _try_can_query(mode: int, question: str) -> str | None:
    """Try to parse 'can [class] [permission]' queries."""
    m = re.match(
        r"can\s+(owner|group|others?)\s+(read|write|execute|exec)",
        question,
    )
    if m:
        cls = m.group(1)
        perm = m.group(2)
        if cls == "other":
            cls = "others"
        if perm == "exec":
            perm = "execute"
        result = can_class(mode, cls, perm)
        if result:
            return f"Yes, {cls} can {perm}."
        else:
            return f"No, {cls} cannot {perm}."
    return None


def _try_who_query(mode: int, question: str) -> str | None:
    """Try to parse 'who can [permission]' queries."""
    m = re.match(r"who\s+can\s+(read|write|execute|exec)", question)
    if m:
        perm = m.group(1)
        if perm == "exec":
            perm = "execute"
        classes = who_can(mode, perm)
        if not classes:
            return f"No one can {perm}."
        if len(classes) == 1:
            return f"{classes[0].capitalize()} can {perm}."
        if len(classes) == 2:
            return f"{classes[0].capitalize()} and {classes[1]} can {perm}."
        return (
            f"{classes[0].capitalize()}, {classes[1]}, "
            f"and {classes[2]} can {perm}."
        )
    return None


def _canonical_special_name(name: str) -> str:
    """Return the canonical display name for a special bit."""
    name = name.lower().strip()
    if name in ("setuid", "suid"):
        return "setuid"
    if name in ("setgid", "sgid"):
        return "setgid"
    if name in ("sticky", "sticky bit"):
        return "sticky bit"
    return name


# ===================================================================
# Common presets
# ===================================================================

@dataclass(frozen=True)
class PermissionPreset:
    """A common permission preset."""

    mode: int
    name: str
    description: str
    use_case: str

    @property
    def numeric(self) -> str:
        return format_numeric(self.mode)

    @property
    def symbolic(self) -> str:
        return numeric_to_symbolic(self.mode)


# Ordered from most restrictive to most permissive
COMMON_PRESETS: list[PermissionPreset] = [
    PermissionPreset(
        mode=0o000, name="No access",
        description="No permissions for anyone",
        use_case="Locking out a file completely (root can still access)",
    ),
    PermissionPreset(
        mode=0o400, name="Owner read-only",
        description="Owner can read; no one else has access",
        use_case="Sensitive config files, private keys (e.g., ~/.ssh/id_rsa)",
    ),
    PermissionPreset(
        mode=0o444, name="Read-only for all",
        description="Everyone can read; no one can write or execute",
        use_case="Published read-only files, reference documents",
    ),
    PermissionPreset(
        mode=0o600, name="Owner read/write",
        description="Owner can read and write; no one else has access",
        use_case="Private data files, SSH keys, password files",
    ),
    PermissionPreset(
        mode=0o644, name="Standard file",
        description="Owner can read and write; everyone else can read",
        use_case="Most regular files, web content, source code",
    ),
    PermissionPreset(
        mode=0o660, name="Owner+group read/write",
        description="Owner and group can read and write; others have no access",
        use_case="Shared project files within a team",
    ),
    PermissionPreset(
        mode=0o664, name="Collaborative file",
        description="Owner and group can read and write; others can read",
        use_case="Files in shared repositories",
    ),
    PermissionPreset(
        mode=0o666, name="Read/write for all",
        description="Everyone can read and write; no one can execute",
        use_case="Temporary shared files (generally insecure)",
    ),
    PermissionPreset(
        mode=0o700, name="Owner full access",
        description="Owner can read, write, and execute; no one else has access",
        use_case="Private scripts, personal bin directories",
    ),
    PermissionPreset(
        mode=0o711, name="Owner full, others execute",
        description="Owner has full access; group and others can only execute",
        use_case="CGI scripts, programs that should run but not be read",
    ),
    PermissionPreset(
        mode=0o750, name="Owner full, group read/execute",
        description="Owner has full access; group can read and execute; others have no access",
        use_case="Shared program directories, group-accessible scripts",
    ),
    PermissionPreset(
        mode=0o755, name="Standard executable",
        description="Owner has full access; everyone else can read and execute",
        use_case="Scripts, programs, /usr/bin/ contents, web directories",
    ),
    PermissionPreset(
        mode=0o775, name="Collaborative executable",
        description="Owner and group have full access; others can read and execute",
        use_case="Shared project directories, group-managed scripts",
    ),
    PermissionPreset(
        mode=0o777, name="Full access for all",
        description="Everyone can read, write, and execute",
        use_case="Temporary workaround only (insecure for production)",
    ),
    PermissionPreset(
        mode=0o1777, name="Sticky + full access",
        description="Everyone can read, write, and execute; only owners can delete",
        use_case="/tmp directory \u2014 prevents users from deleting each other's files",
    ),
    PermissionPreset(
        mode=0o2755, name="Setgid executable",
        description="Standard executable with setgid; new files inherit group",
        use_case="Shared directories where group ownership should be preserved",
    ),
    PermissionPreset(
        mode=0o4755, name="Setuid executable",
        description="Standard executable with setuid; runs as file owner",
        use_case="Programs like passwd, ping that need elevated privileges",
    ),
    PermissionPreset(
        mode=0o4711, name="Setuid, owner full, others execute",
        description="Setuid; owner has full access; others can only execute",
        use_case="Privileged programs that shouldn't be readable (e.g., su)",
    ),
]


def get_presets() -> list[PermissionPreset]:
    """Return all common permission presets."""
    return list(COMMON_PRESETS)


def find_preset(mode: int) -> PermissionPreset | None:
    """Find a preset matching the given mode, or None."""
    for preset in COMMON_PRESETS:
        if preset.mode == mode:
            return preset
    return None


def format_preset_table() -> str:
    """Format all presets as a readable table."""
    lines = [
        f"{'Mode':<8} {'Symbolic':<12} {'Name':<30} Description",
        f"{'-' * 8} {'-' * 12} {'-' * 30} {'-' * 40}",
    ]
    for p in COMMON_PRESETS:
        lines.append(
            f"{p.numeric:<8} {p.symbolic:<12} {p.name:<30} {p.description}"
        )
    return "\n".join(lines)


# ===================================================================
# CLI
# ===================================================================

def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="chmod-calc",
        description="Convert, explain, and query Unix file permissions.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # convert
    convert_parser = subparsers.add_parser(
        "convert", help="Convert between numeric and symbolic permission formats",
    )
    convert_parser.add_argument(
        "mode", help="Permission mode in numeric (755) or symbolic (rwxr-xr-x) format",
    )

    # explain
    explain_parser = subparsers.add_parser(
        "explain", help="Show plain English explanation of a permission mode",
    )
    explain_parser.add_argument(
        "mode", help="Permission mode in numeric (755) or symbolic (rwxr-xr-x) format",
    )

    # query
    query_parser = subparsers.add_parser(
        "query", help='Answer questions about permissions (e.g., "who can write?")',
    )
    query_parser.add_argument(
        "mode", help="Permission mode in numeric (755) or symbolic (rwxr-xr-x) format",
    )
    query_parser.add_argument(
        "question", help='Question about the permissions (e.g., "who can write?")',
    )

    # common
    subparsers.add_parser(
        "common", help="List common permission presets with descriptions",
    )

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "convert":
        try:
            mode_int = parse_mode(args.mode)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        symbolic = numeric_to_symbolic(mode_int)
        numeric_str = format_numeric(mode_int)
        if _looks_symbolic(args.mode):
            print(f"Symbolic: {args.mode}")
            print(f"Numeric:  {numeric_str}")
        else:
            print(f"Numeric:  {numeric_str}")
            print(f"Symbolic: {symbolic}")
        preset = find_preset(mode_int)
        if preset:
            print(f"Name:     {preset.name}")
        return 0

    elif args.command == "explain":
        try:
            result = explain(args.mode)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print(result)
        return 0

    elif args.command == "query":
        try:
            answer = query(args.mode, args.question)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print(answer)
        return 0

    elif args.command == "common":
        print(format_preset_table())
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
