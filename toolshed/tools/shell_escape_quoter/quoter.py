"""
Shell Escape Quoter — Safe String Quoting for Agents

Escapes and quotes strings for Bash, Zsh, POSIX sh, Fish, PowerShell, and
cmd.exe.  Agents constantly build shell commands from user input, filenames,
and generated text.  An unescaped semicolon, backtick, or dollar sign can
turn a harmless string into arbitrary command execution.

This tool handles every dangerous character in every shell:
  - Quotes and backticks (injection)
  - Dollar signs and percent signs (expansion)
  - Semicolons, pipes, ampersands (command chaining)
  - Newlines, null bytes, carriage returns (control)
  - Globs, redirects, braces (glob/expansion)

Also provides string analysis: for any input, reports which characters are
special in which shells, the danger level, and whether injection is possible.

SUPPORTED SHELLS
================
  bash, zsh, sh (POSIX), fish, powershell, cmd

ESCAPING STRATEGIES
===================
  - POSIX (bash/zsh/sh): Single quotes for safe strings, $'...' ANSI-C
    quoting for strings with single quotes or control characters
  - sh: Uses 'text'"'"'more' concatenation trick for portability when
    $'...' is not available
  - Fish: Single quotes with \\' and \\\\ escape sequences (unlike POSIX)
  - PowerShell: Single quotes with '' doubling; double quotes with
    backtick escapes for control characters
  - cmd.exe: Double quotes with "" escaping, %% for percent, ^! for
    delayed expansion

Pure Python, no external dependencies.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum


# ============================================================
# Shell Definitions
# ============================================================

class ShellType(Enum):
    BASH = "bash"
    ZSH = "zsh"
    SH = "sh"
    FISH = "fish"
    POWERSHELL = "powershell"
    CMD = "cmd"


@dataclass(frozen=True)
class SpecialChar:
    char: str
    name: str
    description: str
    danger_level: str  # "high", "medium", "low"
    category: str  # "injection", "expansion", "glob", "control", "redirect", "separator"


@dataclass(frozen=True)
class ShellDefinition:
    shell_type: ShellType
    name: str
    display_name: str
    special_chars: tuple[SpecialChar, ...]
    quoting_notes: str

    def get_special_char_set(self) -> set[str]:
        return {sc.char for sc in self.special_chars}

    def is_special(self, char: str) -> bool:
        return char in self.get_special_char_set()

    def get_char_info(self, char: str) -> SpecialChar | None:
        for sc in self.special_chars:
            if sc.char == char:
                return sc
        return None


# --- POSIX shell special characters (shared by bash, zsh, sh) ---

_POSIX_BASE_CHARS = (
    SpecialChar("'", "single quote", "Ends single-quoted string; can break out of quoting context", "high", "injection"),
    SpecialChar('"', "double quote", "Ends double-quoted string; allows variable expansion and command substitution inside", "high", "injection"),
    SpecialChar("`", "backtick", "Command substitution: `cmd` executes cmd and substitutes its output", "high", "injection"),
    SpecialChar("$", "dollar sign", "Variable expansion ($VAR), command substitution ($(cmd)), arithmetic ($((expr)))", "high", "expansion"),
    SpecialChar("\\", "backslash", "Escape character: removes special meaning of next character", "medium", "control"),
    SpecialChar("\n", "newline", "Command separator: terminates a command, starts a new one", "high", "separator"),
    SpecialChar(";", "semicolon", "Command separator: allows chaining multiple commands", "high", "separator"),
    SpecialChar("&", "ampersand", "Background execution (&), logical AND (&&)", "high", "separator"),
    SpecialChar("|", "pipe", "Pipe output to next command (|), logical OR (||)", "high", "separator"),
    SpecialChar("<", "less-than", "Input redirection: reads from file", "medium", "redirect"),
    SpecialChar(">", "greater-than", "Output redirection: writes to file (overwrites)", "medium", "redirect"),
    SpecialChar("(", "open paren", "Subshell execution, command grouping", "medium", "injection"),
    SpecialChar(")", "close paren", "Ends subshell or command group", "medium", "injection"),
    SpecialChar("{", "open brace", "Brace expansion, command grouping", "medium", "expansion"),
    SpecialChar("}", "close brace", "Ends brace expansion or command group", "medium", "expansion"),
    SpecialChar("*", "asterisk", "Glob: matches any number of characters in filenames", "medium", "glob"),
    SpecialChar("?", "question mark", "Glob: matches exactly one character in filenames", "medium", "glob"),
    SpecialChar("[", "open bracket", "Glob: character class [abc], range [a-z]", "medium", "glob"),
    SpecialChar("]", "close bracket", "Ends glob character class", "low", "glob"),
    SpecialChar("#", "hash", "Comment: everything after # is ignored (at start of word)", "medium", "control"),
    SpecialChar("~", "tilde", "Home directory expansion: ~ expands to $HOME", "low", "expansion"),
    SpecialChar(" ", "space", "Word splitting: separates command arguments", "low", "separator"),
    SpecialChar("\t", "tab", "Word splitting: separates command arguments", "low", "separator"),
    SpecialChar("\r", "carriage return", "Can be used to overwrite terminal output, hide malicious commands", "medium", "control"),
    SpecialChar("\x00", "null byte", "String terminator in C-based shells; can truncate strings unexpectedly", "high", "control"),
)

_BASH_EXTRA_CHARS = (
    SpecialChar("!", "exclamation", "History expansion: !cmd repeats last command starting with cmd", "medium", "expansion"),
)

_ZSH_EXTRA_CHARS = (
    SpecialChar("!", "exclamation", "History expansion (when enabled): !cmd repeats last command", "medium", "expansion"),
    SpecialChar("=", "equals", "In zsh, =cmd expands to the path of cmd (like which)", "low", "expansion"),
)

_FISH_CHARS = (
    SpecialChar("'", "single quote", "Ends single-quoted string; use \\' to include literal single quote", "high", "injection"),
    SpecialChar('"', "double quote", "Ends double-quoted string; allows variable expansion inside", "high", "injection"),
    SpecialChar("$", "dollar sign", "Variable expansion: $VAR substitutes the variable's value", "high", "expansion"),
    SpecialChar("\\", "backslash", "Escape character: removes special meaning of next character", "medium", "control"),
    SpecialChar("\n", "newline", "Command separator", "high", "separator"),
    SpecialChar(";", "semicolon", "Command separator", "high", "separator"),
    SpecialChar("&", "ampersand", "Background execution (&)", "high", "separator"),
    SpecialChar("|", "pipe", "Pipe output to next command", "high", "separator"),
    SpecialChar("<", "less-than", "Input redirection", "medium", "redirect"),
    SpecialChar(">", "greater-than", "Output redirection", "medium", "redirect"),
    SpecialChar("(", "open paren", "Command substitution: (cmd) in fish", "medium", "injection"),
    SpecialChar(")", "close paren", "Ends command substitution", "medium", "injection"),
    SpecialChar("{", "open brace", "Brace expansion", "medium", "expansion"),
    SpecialChar("}", "close brace", "Ends brace expansion", "medium", "expansion"),
    SpecialChar("*", "asterisk", "Glob: matches any characters", "medium", "glob"),
    SpecialChar("?", "question mark", "Glob: matches one character", "medium", "glob"),
    SpecialChar("[", "open bracket", "Glob: character class", "medium", "glob"),
    SpecialChar("]", "close bracket", "Ends glob character class", "low", "glob"),
    SpecialChar("#", "hash", "Comment (at start of line or after ;)", "medium", "control"),
    SpecialChar("~", "tilde", "Home directory expansion", "low", "expansion"),
    SpecialChar(" ", "space", "Argument separator", "low", "separator"),
    SpecialChar("\t", "tab", "Argument separator", "low", "separator"),
    SpecialChar("\r", "carriage return", "Can hide malicious content in terminal output", "medium", "control"),
    SpecialChar("\x00", "null byte", "String terminator; can truncate strings", "high", "control"),
)

_POWERSHELL_CHARS = (
    SpecialChar("'", "single quote", "Ends single-quoted string (literal); double it to include: ''", "high", "injection"),
    SpecialChar('"', "double quote", "Ends double-quoted string; allows variable expansion ($var) and subexpressions $(expr)", "high", "injection"),
    SpecialChar("$", "dollar sign", "Variable reference ($var), subexpression ($(expr))", "high", "expansion"),
    SpecialChar("`", "backtick", "Escape character in PowerShell (like \\ in bash); also line continuation", "high", "control"),
    SpecialChar("\n", "newline", "Statement terminator", "high", "separator"),
    SpecialChar(";", "semicolon", "Statement separator", "high", "separator"),
    SpecialChar("&", "ampersand", "Call operator: & cmd executes cmd; && is pipeline chain AND", "high", "separator"),
    SpecialChar("|", "pipe", "Pipeline operator", "high", "separator"),
    SpecialChar("<", "less-than", "Redirection operator", "medium", "redirect"),
    SpecialChar(">", "greater-than", "Redirection operator", "medium", "redirect"),
    SpecialChar("(", "open paren", "Subexpression, grouping", "medium", "injection"),
    SpecialChar(")", "close paren", "Ends subexpression", "medium", "injection"),
    SpecialChar("{", "open brace", "Script block delimiter", "medium", "injection"),
    SpecialChar("}", "close brace", "Ends script block", "medium", "injection"),
    SpecialChar("@", "at sign", "Splatting (@args), array literal @(), hash table @{}", "medium", "expansion"),
    SpecialChar("#", "hash", "Comment", "medium", "control"),
    SpecialChar("*", "asterisk", "Wildcard in paths", "medium", "glob"),
    SpecialChar("?", "question mark", "Wildcard: single character; also alias for Where-Object", "medium", "glob"),
    SpecialChar("[", "open bracket", "Type literal, indexing", "low", "expansion"),
    SpecialChar("]", "close bracket", "Ends type literal or indexing", "low", "expansion"),
    SpecialChar(" ", "space", "Parameter separator", "low", "separator"),
    SpecialChar("\t", "tab", "Parameter separator", "low", "separator"),
    SpecialChar("\r", "carriage return", "Can manipulate terminal display", "medium", "control"),
    SpecialChar("\x00", "null byte", "Can cause unexpected string termination", "high", "control"),
)

_CMD_CHARS = (
    SpecialChar('"', "double quote", "Quoting mechanism; toggles quote mode on/off", "high", "injection"),
    SpecialChar("^", "caret", "Escape character in cmd.exe: ^c removes special meaning of c", "medium", "control"),
    SpecialChar("&", "ampersand", "Command separator (cmd1 & cmd2), conditional (&& and ||)", "high", "separator"),
    SpecialChar("|", "pipe", "Pipe output to next command", "high", "separator"),
    SpecialChar("<", "less-than", "Input redirection", "medium", "redirect"),
    SpecialChar(">", "greater-than", "Output redirection", "medium", "redirect"),
    SpecialChar("(", "open paren", "Command grouping", "medium", "injection"),
    SpecialChar(")", "close paren", "End command grouping", "medium", "injection"),
    SpecialChar("%", "percent", "Variable expansion: %VAR%, FOR loop variable %%i", "high", "expansion"),
    SpecialChar("!", "exclamation", "Delayed variable expansion: !VAR! when enabled", "high", "expansion"),
    SpecialChar("\n", "newline", "Command separator", "high", "separator"),
    SpecialChar("\r", "carriage return", "Can manipulate display output", "medium", "control"),
    SpecialChar(" ", "space", "Argument separator", "low", "separator"),
    SpecialChar("\t", "tab", "Argument separator", "low", "separator"),
    SpecialChar("*", "asterisk", "Wildcard in some contexts", "low", "glob"),
    SpecialChar("?", "question mark", "Wildcard: single character", "low", "glob"),
    SpecialChar("\x00", "null byte", "String terminator; truncates strings", "high", "control"),
)


SHELLS: dict[ShellType, ShellDefinition] = {
    ShellType.BASH: ShellDefinition(
        shell_type=ShellType.BASH, name="bash", display_name="Bash",
        special_chars=_POSIX_BASE_CHARS + _BASH_EXTRA_CHARS,
        quoting_notes="Single quotes preserve everything literally (no escape sequences). Double quotes allow $, `, \\, and ! expansion. $'...' ANSI-C quoting supports \\n, \\t, \\', \\\\, \\xHH, etc."),
    ShellType.ZSH: ShellDefinition(
        shell_type=ShellType.ZSH, name="zsh", display_name="Zsh",
        special_chars=_POSIX_BASE_CHARS + _ZSH_EXTRA_CHARS,
        quoting_notes="Similar to bash. Single quotes are fully literal. Double quotes allow expansion. $'...' ANSI-C quoting works. zsh also treats = specially at word start (=cmd -> path lookup)."),
    ShellType.SH: ShellDefinition(
        shell_type=ShellType.SH, name="sh", display_name="POSIX sh",
        special_chars=_POSIX_BASE_CHARS,
        quoting_notes="POSIX sh: single quotes are fully literal. Double quotes allow $, `, \\. $'...' may not be available in all POSIX sh implementations; we use it where needed but prefer single quotes when possible."),
    ShellType.FISH: ShellDefinition(
        shell_type=ShellType.FISH, name="fish", display_name="Fish",
        special_chars=_FISH_CHARS,
        quoting_notes="Fish single quotes support \\' and \\\\ as escape sequences (unlike POSIX). Double quotes allow $var expansion. No backtick command substitution; uses (cmd) instead."),
    ShellType.POWERSHELL: ShellDefinition(
        shell_type=ShellType.POWERSHELL, name="powershell", display_name="PowerShell",
        special_chars=_POWERSHELL_CHARS,
        quoting_notes="Single quotes are literal (no expansion). Embed a single quote by doubling: ''. Double quotes expand $var and $(expr). Backtick (`) is the escape character, not backslash."),
    ShellType.CMD: ShellDefinition(
        shell_type=ShellType.CMD, name="cmd", display_name="cmd.exe",
        special_chars=_CMD_CHARS,
        quoting_notes="cmd.exe uses ^ as escape character outside quotes. Double quotes protect spaces but not all special chars. % is used for variables (%VAR%) and must be doubled (%%) in batch files. No single-quote mechanism."),
}


def get_shell(name: str) -> ShellDefinition:
    name_lower = name.lower().strip()
    aliases = {
        "bash": ShellType.BASH, "zsh": ShellType.ZSH,
        "sh": ShellType.SH, "posix": ShellType.SH,
        "fish": ShellType.FISH,
        "powershell": ShellType.POWERSHELL, "pwsh": ShellType.POWERSHELL, "ps": ShellType.POWERSHELL,
        "cmd": ShellType.CMD, "cmd.exe": ShellType.CMD, "command": ShellType.CMD,
    }
    shell_type = aliases.get(name_lower)
    if shell_type is None:
        valid = ", ".join(sorted(aliases.keys()))
        raise ValueError(f"Unknown shell: {name!r}. Valid shells: {valid}")
    return SHELLS[shell_type]


def all_shells() -> list[ShellDefinition]:
    return [SHELLS[st] for st in ShellType]


def shell_names() -> list[str]:
    return [st.value for st in ShellType]


# ============================================================
# Escaper
# ============================================================

def escape(s: str, shell: str | ShellType | ShellDefinition) -> str:
    if isinstance(shell, str):
        shell_def = get_shell(shell)
    elif isinstance(shell, ShellType):
        shell_def = SHELLS[shell]
    else:
        shell_def = shell

    dispatch = {
        ShellType.BASH: escape_bash,
        ShellType.ZSH: escape_zsh,
        ShellType.SH: escape_sh,
        ShellType.FISH: escape_fish,
        ShellType.POWERSHELL: escape_powershell,
        ShellType.CMD: escape_cmd,
    }
    return dispatch[shell_def.shell_type](s)


def escape_all(s: str) -> dict[str, str]:
    result = {}
    for shell_def in all_shells():
        result[shell_def.name] = escape(s, shell_def)
    return result


def _needs_ansi_c_quoting(s: str) -> bool:
    for ch in s:
        if ch == "'":
            return True
        if ord(ch) < 0x20 or ord(ch) == 0x7F:
            return True
        if ch == "\x00":
            return True
    return False


def _ansi_c_quote(s: str) -> str:
    parts = []
    for ch in s:
        code = ord(ch)
        if ch == "'":
            parts.append("\\'")
        elif ch == "\\":
            parts.append("\\\\")
        elif ch == "\n":
            parts.append("\\n")
        elif ch == "\r":
            parts.append("\\r")
        elif ch == "\t":
            parts.append("\\t")
        elif ch == "\x00":
            parts.append("\\x00")
        elif ch == "\a":
            parts.append("\\a")
        elif ch == "\b":
            parts.append("\\b")
        elif ch == "\f":
            parts.append("\\f")
        elif ch == "\v":
            parts.append("\\v")
        elif ch == "\x1b":
            parts.append("\\e")
        elif code < 0x20 or code == 0x7F:
            parts.append(f"\\x{code:02x}")
        else:
            parts.append(ch)
    return "$'" + "".join(parts) + "'"


def _simple_single_quote(s: str) -> str:
    return "'" + s + "'"


_SAFE_CHARS = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "_./-:@,+="
)


def escape_posix(s: str) -> str:
    if s == "":
        return "''"
    if _needs_ansi_c_quoting(s):
        return _ansi_c_quote(s)
    if all(ch in _SAFE_CHARS for ch in s):
        return s
    return _simple_single_quote(s)


def escape_bash(s: str) -> str:
    return escape_posix(s)


def escape_zsh(s: str) -> str:
    return escape_posix(s)


def escape_sh(s: str) -> str:
    if s == "":
        return "''"
    has_control = any(ord(ch) < 0x20 or ord(ch) == 0x7F or ch == "\x00" for ch in s)
    if has_control:
        return _ansi_c_quote(s)
    if all(ch in _SAFE_CHARS for ch in s):
        return s
    if "'" not in s:
        return _simple_single_quote(s)
    return "'" + s.replace("'", "'\"'\"'") + "'"


def escape_fish(s: str) -> str:
    if s == "":
        return "''"
    if all(ch in _SAFE_CHARS for ch in s):
        return s
    has_control = any(ord(ch) < 0x20 or ord(ch) == 0x7F or ch == "\x00" for ch in s)
    if has_control:
        parts = []
        in_quote = False
        for ch in s:
            code = ord(ch)
            if code < 0x20 or code == 0x7F or ch == "\x00":
                if in_quote:
                    parts.append("'")
                    in_quote = False
                parts.append(f"\\x{code:02x}")
            elif ch == "'":
                if in_quote:
                    parts.append("\\'")
                else:
                    parts.append("'")
                    in_quote = True
                    parts.append("\\'")
            elif ch == "\\":
                if not in_quote:
                    parts.append("'")
                    in_quote = True
                parts.append("\\\\")
            else:
                if not in_quote:
                    parts.append("'")
                    in_quote = True
                parts.append(ch)
        if in_quote:
            parts.append("'")
        return "".join(parts)
    result = ["'"]
    for ch in s:
        if ch == "'":
            result.append("\\'")
        elif ch == "\\":
            result.append("\\\\")
        else:
            result.append(ch)
    result.append("'")
    return "".join(result)


def escape_powershell(s: str) -> str:
    if s == "":
        return "''"
    safe_chars_ps = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "_./-:,+="
    )
    if all(ch in safe_chars_ps for ch in s):
        return s
    has_control = any(ord(ch) < 0x20 or ord(ch) == 0x7F or ch == "\x00" for ch in s)
    if has_control:
        parts = []
        for ch in s:
            code = ord(ch)
            if ch == '"':
                parts.append('`"')
            elif ch == '$':
                parts.append('`$')
            elif ch == '`':
                parts.append('``')
            elif ch == "\n":
                parts.append("`n")
            elif ch == "\r":
                parts.append("`r")
            elif ch == "\t":
                parts.append("`t")
            elif ch == "\x00":
                parts.append("`0")
            elif ch == "\a":
                parts.append("`a")
            elif ch == "\b":
                parts.append("`b")
            elif ch == "\f":
                parts.append("`f")
            elif ch == "\v":
                parts.append("`v")
            elif ch == "\x1b":
                parts.append("`e")
            elif code < 0x20 or code == 0x7F:
                parts.append(f"`u{{{code:04X}}}")
            else:
                parts.append(ch)
        return '"' + "".join(parts) + '"'
    return "'" + s.replace("'", "''") + "'"


def escape_cmd(s: str) -> str:
    if s == "":
        return '""'
    if all(ch in _SAFE_CHARS for ch in s):
        return s
    parts = []
    for ch in s:
        if ch == '"':
            parts.append('""')
        elif ch == '%':
            parts.append('%%')
        elif ch == '!':
            parts.append('^!')
        elif ch == '\n':
            parts.append('^\n')
        elif ch == '\r':
            parts.append('\r')
        elif ch == '\x00':
            parts.append('\x00')
        else:
            parts.append(ch)
    return '"' + "".join(parts) + '"'


# ============================================================
# Analyzer
# ============================================================

@dataclass
class CharFinding:
    char: str
    position: int
    char_info: SpecialChar
    shell_name: str


@dataclass
class ShellAnalysis:
    shell_name: str
    shell_display_name: str
    findings: list[CharFinding]
    risk_level: str  # "safe", "low", "medium", "high", "critical"
    risk_summary: str
    injection_possible: bool
    total_special_chars: int
    unique_special_chars: int

    @property
    def dangerous_chars(self) -> list[CharFinding]:
        return [f for f in self.findings if f.char_info.danger_level == "high"]

    @property
    def has_injection_chars(self) -> bool:
        return any(f.char_info.category == "injection" for f in self.findings)

    @property
    def has_expansion_chars(self) -> bool:
        return any(f.char_info.category == "expansion" for f in self.findings)


@dataclass
class AnalysisResult:
    input_string: str
    input_repr: str
    input_length: int
    shell_analyses: list[ShellAnalysis]
    overall_risk: str

    @property
    def is_safe_everywhere(self) -> bool:
        return all(a.risk_level == "safe" for a in self.shell_analyses)


def analyze_string(
    s: str,
    shells: list[str | ShellType | ShellDefinition] | None = None,
) -> AnalysisResult:
    if shells is None:
        shell_defs = all_shells()
    else:
        shell_defs = []
        for shell in shells:
            if isinstance(shell, str):
                shell_defs.append(get_shell(shell))
            elif isinstance(shell, ShellType):
                shell_defs.append(SHELLS[shell])
            else:
                shell_defs.append(shell)

    shell_analyses = []
    for shell_def in shell_defs:
        analysis = _analyze_for_shell(s, shell_def)
        shell_analyses.append(analysis)

    risk_order = {"safe": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    overall_risk = "safe"
    for analysis in shell_analyses:
        if risk_order.get(analysis.risk_level, 0) > risk_order.get(overall_risk, 0):
            overall_risk = analysis.risk_level

    return AnalysisResult(
        input_string=s, input_repr=repr(s), input_length=len(s),
        shell_analyses=shell_analyses, overall_risk=overall_risk)


def _analyze_for_shell(s: str, shell_def: ShellDefinition) -> ShellAnalysis:
    findings: list[CharFinding] = []
    for i, ch in enumerate(s):
        char_info = shell_def.get_char_info(ch)
        if char_info is not None:
            findings.append(CharFinding(char=ch, position=i,
                                        char_info=char_info, shell_name=shell_def.name))

    if not findings:
        return ShellAnalysis(
            shell_name=shell_def.name, shell_display_name=shell_def.display_name,
            findings=findings, risk_level="safe",
            risk_summary="No special characters found. String is safe as-is.",
            injection_possible=False, total_special_chars=0, unique_special_chars=0)

    high_count = sum(1 for f in findings if f.char_info.danger_level == "high")
    has_injection = any(f.char_info.category == "injection" for f in findings)
    has_separator = any(
        f.char_info.category == "separator" and f.char_info.danger_level == "high"
        for f in findings)
    has_expansion = any(f.char_info.category == "expansion" for f in findings)

    injection_possible = has_injection or has_separator

    if has_injection and has_separator:
        risk_level = "critical"
        risk_summary = "Contains both injection characters and command separators. An unescaped use of this string could execute arbitrary commands."
    elif has_injection or (has_separator and high_count > 0):
        risk_level = "high"
        risk_summary = "Contains characters that could enable command injection or unintended command execution if not properly escaped."
    elif high_count > 0:
        risk_level = "high"
        risk_summary = "Contains high-danger special characters that could cause unintended behavior if not properly quoted."
    elif has_expansion:
        risk_level = "medium"
        risk_summary = "Contains expansion characters. Values may be interpreted differently than intended without proper quoting."
    elif sum(1 for f in findings if f.char_info.danger_level == "medium") > 0:
        risk_level = "medium"
        risk_summary = "Contains characters with special meaning that should be quoted."
    else:
        risk_level = "low"
        risk_summary = "Contains characters with minor special meaning (whitespace, brackets). Quoting recommended but risk is low."

    unique_chars = {f.char for f in findings}

    return ShellAnalysis(
        shell_name=shell_def.name, shell_display_name=shell_def.display_name,
        findings=findings, risk_level=risk_level, risk_summary=risk_summary,
        injection_possible=injection_possible, total_special_chars=len(findings),
        unique_special_chars=len(unique_chars))


# ============================================================
# CLI
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="shell-escape-quoter",
        description="Escape and quote strings for different shells.",
    )
    parser.add_argument("string", nargs="?", help="The string to escape.")
    parser.add_argument("--shell", "-s", help="Target shell.")
    parser.add_argument("--all", "-a", action="store_true", dest="all_shells",
                        help="Show escaped output for all shells.")
    parser.add_argument("--analyze", action="store_true",
                        help="Analyze string for dangerous characters.")

    args = parser.parse_args()

    if args.string is None:
        parser.error("Provide a string argument.")
        return 1

    if args.analyze:
        if args.shell:
            result = analyze_string(args.string, shells=[args.shell])
        else:
            result = analyze_string(args.string)
        print(f"Analysis of: {result.input_repr}")
        print(f"Length: {result.input_length} characters")
        print(f"Overall risk: {result.overall_risk}")
        print()
        for sa in result.shell_analyses:
            print(f"  {sa.shell_display_name} [{sa.risk_level}] - {sa.risk_summary}")
            if sa.total_special_chars > 0:
                print(f"    {sa.total_special_chars} special chars ({sa.unique_special_chars} unique)")
            if sa.injection_possible:
                print(f"    ** INJECTION RISK **")
        return 0

    if args.all_shells or not args.shell:
        escaped_map = escape_all(args.string)
        print(f"Input: {repr(args.string)}")
        print()
        for shell_name, escaped in escaped_map.items():
            print(f"  {shell_name:>12}: {escaped}")
        return 0

    escaped = escape(args.string, args.shell)
    print(escaped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
