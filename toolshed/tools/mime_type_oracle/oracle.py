"""
MIME Type Oracle — Look up MIME types by extension and vice versa.

Bidirectional lookup with rich metadata: RFC references, binary/text
classification, compressibility, common aliases, associated programs.
Handles ambiguous extensions like .ts (TypeScript vs MPEG transport stream).

CAPABILITIES
============
1. Extension Lookup: Extension to MIME type with full metadata
2. Reverse Lookup: MIME type to extensions
3. Alias Resolution: text/json -> application/json, etc.
4. Ambiguous Extension Detection: .ts, .mts flagged with all interpretations
5. Keyword Search: Search by type, description, program, extension
6. Metadata: RFC refs, binary/text, compressibility, programs, aliases
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════
# MimeEntry — the core data structure
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MimeEntry:
    """A MIME type entry with full metadata."""
    mime_type: str
    extensions: tuple[str, ...]
    kind: str  # "text" or "binary"
    compressible: bool
    description: str
    aliases: tuple[str, ...] = ()
    rfcs: tuple[str, ...] = ()
    programs: tuple[str, ...] = ()


# ═══════════════════════════════════════════════════════════════════
# Comprehensive MIME Database
# ═══════════════════════════════════════════════════════════════════

MIME_DATABASE: tuple[MimeEntry, ...] = (

    # --- text/* ---
    MimeEntry("text/plain", (".txt", ".text", ".log", ".conf", ".cfg", ".ini", ".lst"), "text", True, "Plain text", rfcs=("RFC 2046", "RFC 3676"), programs=("Notepad", "vim", "nano", "VS Code")),
    MimeEntry("text/html", (".html", ".htm", ".shtml"), "text", True, "HTML document", aliases=("text/x-html",), rfcs=("RFC 2854",), programs=("web browsers", "VS Code")),
    MimeEntry("text/css", (".css",), "text", True, "Cascading Style Sheets", rfcs=("RFC 2318",), programs=("web browsers", "VS Code")),
    MimeEntry("text/javascript", (".js", ".mjs"), "text", True, "JavaScript", aliases=("application/javascript", "application/x-javascript", "text/x-javascript"), rfcs=("RFC 9239",), programs=("Node.js", "web browsers", "VS Code")),
    MimeEntry("text/csv", (".csv",), "text", True, "Comma-separated values", rfcs=("RFC 4180",), programs=("Excel", "LibreOffice Calc", "Google Sheets")),
    MimeEntry("text/tab-separated-values", (".tsv",), "text", True, "Tab-separated values", programs=("Excel", "LibreOffice Calc")),
    MimeEntry("text/xml", (".xml",), "text", True, "XML document", aliases=("application/xml",), rfcs=("RFC 7303",), programs=("web browsers", "VS Code", "XMLSpy")),
    MimeEntry("text/markdown", (".md", ".markdown", ".mkd", ".mkdn"), "text", True, "Markdown document", rfcs=("RFC 7763",), programs=("VS Code", "Obsidian", "Typora")),
    MimeEntry("text/calendar", (".ics", ".ifb"), "text", True, "iCalendar data", rfcs=("RFC 5545",), programs=("Outlook", "Google Calendar", "Apple Calendar")),
    MimeEntry("text/vcard", (".vcf", ".vcard"), "text", True, "vCard contact", rfcs=("RFC 6350",), programs=("Outlook", "Apple Contacts", "Google Contacts")),
    MimeEntry("text/rtf", (".rtf",), "text", True, "Rich Text Format", programs=("WordPad", "LibreOffice Writer", "TextEdit")),
    MimeEntry("text/x-python", (".py", ".pyw", ".pyi"), "text", True, "Python source code", programs=("Python", "VS Code", "PyCharm")),
    MimeEntry("text/x-c", (".c", ".h"), "text", True, "C source code", programs=("gcc", "VS Code", "CLion")),
    MimeEntry("text/x-c++", (".cpp", ".cxx", ".cc", ".hpp", ".hxx", ".hh"), "text", True, "C++ source code", aliases=("text/x-c++src",), programs=("g++", "VS Code", "CLion")),
    MimeEntry("text/x-java-source", (".java",), "text", True, "Java source code", programs=("javac", "IntelliJ IDEA", "VS Code")),
    MimeEntry("text/x-rust", (".rs",), "text", True, "Rust source code", programs=("rustc", "VS Code", "RustRover")),
    MimeEntry("text/x-go", (".go",), "text", True, "Go source code", programs=("go", "VS Code", "GoLand")),
    MimeEntry("text/x-ruby", (".rb", ".rbw"), "text", True, "Ruby source code", programs=("ruby", "VS Code", "RubyMine")),
    MimeEntry("text/x-perl", (".pl", ".pm"), "text", True, "Perl source code", programs=("perl", "VS Code")),
    MimeEntry("text/x-shellscript", (".sh", ".bash", ".zsh", ".fish"), "text", True, "Shell script", aliases=("application/x-sh",), programs=("bash", "zsh", "VS Code")),
    MimeEntry("text/x-php", (".php", ".php3", ".php4", ".php5", ".phtml"), "text", True, "PHP source code", aliases=("application/x-php",), programs=("php", "VS Code", "PhpStorm")),
    MimeEntry("text/x-lua", (".lua",), "text", True, "Lua source code", programs=("lua", "VS Code")),
    MimeEntry("text/x-swift", (".swift",), "text", True, "Swift source code", programs=("swift", "Xcode", "VS Code")),
    MimeEntry("text/x-kotlin", (".kt", ".kts"), "text", True, "Kotlin source code", programs=("kotlinc", "IntelliJ IDEA", "VS Code")),
    MimeEntry("text/x-scala", (".scala", ".sc"), "text", True, "Scala source code", programs=("scalac", "IntelliJ IDEA", "VS Code")),
    MimeEntry("text/x-sql", (".sql",), "text", True, "SQL query", programs=("psql", "mysql", "VS Code", "DBeaver")),
    MimeEntry("text/x-yaml", (".yaml", ".yml"), "text", True, "YAML document", aliases=("application/x-yaml", "text/yaml"), programs=("VS Code", "any text editor")),
    MimeEntry("text/x-toml", (".toml",), "text", True, "TOML configuration", programs=("VS Code", "any text editor")),
    MimeEntry("text/x-diff", (".diff", ".patch"), "text", True, "Unified diff / patch file", programs=("patch", "git", "VS Code")),
    MimeEntry("text/x-cmake", (".cmake",), "text", True, "CMake build script", programs=("cmake", "VS Code", "CLion")),
    MimeEntry("text/x-dockerfile", (".dockerfile",), "text", True, "Dockerfile", programs=("docker", "VS Code")),
    MimeEntry("text/x-r", (".r", ".R"), "text", True, "R source code", programs=("R", "RStudio", "VS Code")),

    # --- application/* Documents & Archives ---
    MimeEntry("application/json", (".json",), "text", True, "JSON data", aliases=("text/json",), rfcs=("RFC 8259",), programs=("jq", "VS Code", "web browsers")),
    MimeEntry("application/ld+json", (".jsonld",), "text", True, "JSON-LD linked data", rfcs=("RFC 6906",), programs=("VS Code", "web browsers")),
    MimeEntry("application/schema+json", (), "text", True, "JSON Schema", programs=("VS Code", "ajv")),
    MimeEntry("application/geo+json", (".geojson",), "text", True, "GeoJSON geographic data", rfcs=("RFC 7946",), programs=("QGIS", "Mapbox", "Leaflet")),
    MimeEntry("application/pdf", (".pdf",), "binary", False, "Portable Document Format", rfcs=("RFC 8118",), programs=("Acrobat Reader", "web browsers", "Evince", "Preview")),
    MimeEntry("application/zip", (".zip",), "binary", False, "ZIP archive", programs=("7-Zip", "WinZip", "unzip", "Windows Explorer")),
    MimeEntry("application/gzip", (".gz", ".gzip"), "binary", False, "Gzip compressed data", rfcs=("RFC 1952",), programs=("gzip", "7-Zip", "tar")),
    MimeEntry("application/x-bzip2", (".bz2",), "binary", False, "Bzip2 compressed data", programs=("bzip2", "7-Zip", "tar")),
    MimeEntry("application/x-xz", (".xz",), "binary", False, "XZ compressed data", programs=("xz", "7-Zip", "tar")),
    MimeEntry("application/zstd", (".zst", ".zstd"), "binary", False, "Zstandard compressed data", rfcs=("RFC 8878",), programs=("zstd", "tar")),
    MimeEntry("application/x-tar", (".tar",), "binary", True, "Tape archive", programs=("tar", "7-Zip")),
    MimeEntry("application/x-7z-compressed", (".7z",), "binary", False, "7-Zip archive", programs=("7-Zip",)),
    MimeEntry("application/x-rar-compressed", (".rar",), "binary", False, "RAR archive", aliases=("application/vnd.rar",), programs=("WinRAR", "7-Zip", "unrar")),
    MimeEntry("application/octet-stream", (".bin", ".exe", ".dll", ".so", ".dylib"), "binary", True, "Arbitrary binary data", rfcs=("RFC 2046",)),
    MimeEntry("application/wasm", (".wasm",), "binary", True, "WebAssembly module", programs=("web browsers", "wasmtime", "wasmer")),
    MimeEntry("application/x-executable", (".elf",), "binary", True, "ELF executable", programs=("operating system loader",)),

    # --- Office / Productivity ---
    MimeEntry("application/vnd.openxmlformats-officedocument.wordprocessingml.document", (".docx",), "binary", False, "Microsoft Word document (OOXML)", aliases=("application/x-docx",), programs=("Microsoft Word", "LibreOffice Writer", "Google Docs")),
    MimeEntry("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", (".xlsx",), "binary", False, "Microsoft Excel spreadsheet (OOXML)", programs=("Microsoft Excel", "LibreOffice Calc", "Google Sheets")),
    MimeEntry("application/vnd.openxmlformats-officedocument.presentationml.presentation", (".pptx",), "binary", False, "Microsoft PowerPoint presentation (OOXML)", programs=("Microsoft PowerPoint", "LibreOffice Impress", "Google Slides")),
    MimeEntry("application/msword", (".doc",), "binary", True, "Microsoft Word document (legacy)", programs=("Microsoft Word", "LibreOffice Writer")),
    MimeEntry("application/vnd.ms-excel", (".xls",), "binary", True, "Microsoft Excel spreadsheet (legacy)", programs=("Microsoft Excel", "LibreOffice Calc")),
    MimeEntry("application/vnd.ms-powerpoint", (".ppt",), "binary", True, "Microsoft PowerPoint presentation (legacy)", programs=("Microsoft PowerPoint", "LibreOffice Impress")),
    MimeEntry("application/vnd.oasis.opendocument.text", (".odt",), "binary", False, "OpenDocument Text", programs=("LibreOffice Writer",)),
    MimeEntry("application/vnd.oasis.opendocument.spreadsheet", (".ods",), "binary", False, "OpenDocument Spreadsheet", programs=("LibreOffice Calc",)),
    MimeEntry("application/vnd.oasis.opendocument.presentation", (".odp",), "binary", False, "OpenDocument Presentation", programs=("LibreOffice Impress",)),
    MimeEntry("application/epub+zip", (".epub",), "binary", False, "EPUB ebook", programs=("Calibre", "Apple Books", "Kindle")),

    # --- Web / API ---
    MimeEntry("application/xhtml+xml", (".xhtml",), "text", True, "XHTML document", rfcs=("RFC 3236",), programs=("web browsers", "VS Code")),
    MimeEntry("application/atom+xml", (".atom",), "text", True, "Atom feed", rfcs=("RFC 4287",), programs=("feed readers", "web browsers")),
    MimeEntry("application/rss+xml", (".rss",), "text", True, "RSS feed", programs=("feed readers", "web browsers")),
    MimeEntry("application/x-www-form-urlencoded", (), "text", True, "URL-encoded form data", rfcs=("RFC 1866",), programs=("web browsers", "curl")),
    MimeEntry("application/graphql", (".graphql", ".gql"), "text", True, "GraphQL query", programs=("Apollo", "Relay", "VS Code")),
    MimeEntry("application/x-ndjson", (".ndjson", ".jsonl"), "text", True, "Newline-delimited JSON", aliases=("application/jsonl",), programs=("jq", "VS Code")),
    MimeEntry("application/msgpack", (".msgpack",), "binary", True, "MessagePack binary serialization"),
    MimeEntry("application/x-protobuf", (".proto",), "text", True, "Protocol Buffers schema", programs=("protoc", "VS Code")),

    # --- Security / Crypto ---
    MimeEntry("application/x-x509-ca-cert", (".crt", ".cer", ".der"), "binary", True, "X.509 certificate", programs=("openssl", "Certificate Manager")),
    MimeEntry("application/x-pem-file", (".pem",), "text", True, "PEM-encoded certificate or key", programs=("openssl",)),
    MimeEntry("application/pkcs12", (".p12", ".pfx"), "binary", False, "PKCS#12 certificate bundle", programs=("openssl", "Certificate Manager")),
    MimeEntry("application/pgp-signature", (".sig", ".asc"), "text", True, "PGP signature", rfcs=("RFC 3156",), programs=("gpg", "Kleopatra")),

    # --- Misc application ---
    MimeEntry("application/x-sqlite3", (".sqlite", ".sqlite3", ".db"), "binary", True, "SQLite database", programs=("sqlite3", "DB Browser for SQLite", "DBeaver")),
    MimeEntry("application/java-archive", (".jar",), "binary", False, "Java archive (JAR)", programs=("java", "IntelliJ IDEA")),
    MimeEntry("application/vnd.android.package-archive", (".apk",), "binary", False, "Android application package", programs=("Android Studio", "adb")),
    MimeEntry("application/x-apple-diskimage", (".dmg",), "binary", False, "Apple disk image", programs=("macOS Finder", "hdiutil")),
    MimeEntry("application/x-iso9660-image", (".iso",), "binary", True, "ISO 9660 disc image", programs=("mount", "7-Zip", "VirtualBox")),
    MimeEntry("application/x-deb", (".deb",), "binary", False, "Debian package", programs=("dpkg", "apt")),
    MimeEntry("application/x-rpm", (".rpm",), "binary", False, "RPM package", programs=("rpm", "dnf", "yum")),
    MimeEntry("application/x-msi", (".msi",), "binary", True, "Windows Installer package", programs=("msiexec", "Windows Installer")),
    MimeEntry("application/vnd.apple.installer+xml", (".pkg",), "binary", False, "macOS installer package", programs=("Installer.app",)),
    MimeEntry("application/x-latex", (".latex", ".tex"), "text", True, "LaTeX document", programs=("pdflatex", "Overleaf", "TeXShop", "VS Code")),
    MimeEntry("application/postscript", (".ps", ".eps", ".ai"), "text", True, "PostScript / Encapsulated PostScript", programs=("Ghostscript", "Illustrator", "Inkscape")),
    MimeEntry("application/x-bibtex", (".bib",), "text", True, "BibTeX bibliography", programs=("BibDesk", "JabRef", "VS Code")),
    MimeEntry("application/cbor", (".cbor",), "binary", True, "Concise Binary Object Representation", rfcs=("RFC 8949",)),
    MimeEntry("application/x-plist", (".plist",), "text", True, "Apple property list (XML)", programs=("Xcode", "plutil")),
    MimeEntry("application/vnd.sqlite3", (), "binary", True, "SQLite 3 database (IANA registered)", aliases=("application/x-sqlite3",), programs=("sqlite3", "DB Browser for SQLite")),

    # --- image/* ---
    MimeEntry("image/jpeg", (".jpg", ".jpeg", ".jpe", ".jfif"), "binary", False, "JPEG image", aliases=("image/pjpeg",), rfcs=("RFC 2045",), programs=("web browsers", "Photoshop", "GIMP", "Preview")),
    MimeEntry("image/png", (".png",), "binary", False, "PNG image", rfcs=("RFC 2083",), programs=("web browsers", "Photoshop", "GIMP", "Preview")),
    MimeEntry("image/gif", (".gif",), "binary", False, "GIF image", rfcs=("RFC 2046",), programs=("web browsers", "Photoshop", "GIMP")),
    MimeEntry("image/webp", (".webp",), "binary", False, "WebP image", programs=("web browsers", "Photoshop", "GIMP")),
    MimeEntry("image/avif", (".avif",), "binary", False, "AVIF image", programs=("web browsers", "GIMP")),
    MimeEntry("image/svg+xml", (".svg", ".svgz"), "text", True, "SVG vector image", programs=("web browsers", "Inkscape", "Illustrator")),
    MimeEntry("image/bmp", (".bmp",), "binary", True, "Bitmap image", programs=("Paint", "Photoshop", "GIMP")),
    MimeEntry("image/tiff", (".tiff", ".tif"), "binary", True, "TIFF image", rfcs=("RFC 3302",), programs=("Photoshop", "GIMP", "Preview")),
    MimeEntry("image/x-icon", (".ico",), "binary", True, "ICO icon", aliases=("image/vnd.microsoft.icon",), programs=("web browsers", "IcoFX")),
    MimeEntry("image/heif", (".heif", ".heic"), "binary", False, "HEIF image (High Efficiency Image Format)", programs=("Apple Photos", "Preview", "GIMP")),
    MimeEntry("image/jxl", (".jxl",), "binary", False, "JPEG XL image", programs=("GIMP", "web browsers")),
    MimeEntry("image/x-photoshop", (".psd",), "binary", True, "Photoshop document", aliases=("image/vnd.adobe.photoshop",), programs=("Photoshop", "GIMP")),
    MimeEntry("image/x-xcf", (".xcf",), "binary", True, "GIMP image", programs=("GIMP",)),
    MimeEntry("image/x-raw", (".raw", ".cr2", ".nef", ".arw", ".dng"), "binary", True, "Camera RAW image", programs=("Lightroom", "Photoshop", "RawTherapee", "darktable")),

    # --- audio/* ---
    MimeEntry("audio/mpeg", (".mp3",), "binary", False, "MP3 audio", rfcs=("RFC 3003",), programs=("VLC", "foobar2000", "iTunes", "Audacity")),
    MimeEntry("audio/ogg", (".ogg", ".oga"), "binary", False, "Ogg Vorbis audio", rfcs=("RFC 5334",), programs=("VLC", "foobar2000", "Audacity")),
    MimeEntry("audio/opus", (".opus",), "binary", False, "Opus audio", rfcs=("RFC 7845",), programs=("VLC", "foobar2000", "Audacity")),
    MimeEntry("audio/wav", (".wav",), "binary", True, "Waveform audio", aliases=("audio/x-wav", "audio/wave"), programs=("VLC", "Audacity", "foobar2000")),
    MimeEntry("audio/flac", (".flac",), "binary", False, "FLAC lossless audio", programs=("VLC", "foobar2000", "Audacity")),
    MimeEntry("audio/aac", (".aac",), "binary", False, "AAC audio", programs=("VLC", "iTunes", "foobar2000")),
    MimeEntry("audio/mp4", (".m4a",), "binary", False, "MP4 audio", programs=("VLC", "iTunes", "foobar2000")),
    MimeEntry("audio/webm", (".weba",), "binary", False, "WebM audio", programs=("web browsers", "VLC")),
    MimeEntry("audio/midi", (".mid", ".midi"), "binary", True, "MIDI audio", aliases=("audio/x-midi",), rfcs=("RFC 4695",), programs=("VLC", "GarageBand", "LMMS")),
    MimeEntry("audio/x-aiff", (".aiff", ".aif"), "binary", True, "AIFF audio", programs=("VLC", "Audacity", "iTunes")),
    MimeEntry("audio/x-ms-wma", (".wma",), "binary", False, "Windows Media Audio", programs=("Windows Media Player", "VLC")),

    # --- video/* ---
    MimeEntry("video/mp4", (".mp4", ".m4v"), "binary", False, "MP4 video", rfcs=("RFC 4337",), programs=("VLC", "web browsers", "mpv")),
    MimeEntry("video/webm", (".webm",), "binary", False, "WebM video", programs=("web browsers", "VLC", "mpv")),
    MimeEntry("video/ogg", (".ogv",), "binary", False, "Ogg Theora video", rfcs=("RFC 5334",), programs=("VLC", "web browsers")),
    MimeEntry("video/x-matroska", (".mkv",), "binary", False, "Matroska video", programs=("VLC", "mpv", "MPC-HC")),
    MimeEntry("video/x-msvideo", (".avi",), "binary", True, "AVI video", programs=("VLC", "Windows Media Player", "mpv")),
    MimeEntry("video/quicktime", (".mov", ".qt"), "binary", False, "QuickTime video", programs=("QuickTime Player", "VLC", "mpv")),
    MimeEntry("video/x-flv", (".flv",), "binary", False, "Flash video", programs=("VLC", "mpv")),
    MimeEntry("video/x-ms-wmv", (".wmv",), "binary", False, "Windows Media Video", programs=("Windows Media Player", "VLC")),
    MimeEntry("video/mp2t", (".ts", ".mts", ".m2ts"), "binary", False, "MPEG transport stream", programs=("VLC", "mpv", "ffmpeg")),
    MimeEntry("video/3gpp", (".3gp",), "binary", False, "3GPP video", rfcs=("RFC 3839",), programs=("VLC", "mpv")),

    # --- font/* ---
    MimeEntry("font/woff", (".woff",), "binary", False, "Web Open Font Format", rfcs=("RFC 8081",), programs=("web browsers", "FontForge")),
    MimeEntry("font/woff2", (".woff2",), "binary", False, "Web Open Font Format 2", rfcs=("RFC 8081",), programs=("web browsers", "FontForge")),
    MimeEntry("font/ttf", (".ttf",), "binary", True, "TrueType font", aliases=("application/x-font-ttf",), rfcs=("RFC 8081",), programs=("web browsers", "FontForge", "Font Book")),
    MimeEntry("font/otf", (".otf",), "binary", True, "OpenType font", aliases=("application/x-font-otf",), rfcs=("RFC 8081",), programs=("web browsers", "FontForge", "Font Book")),
    MimeEntry("font/collection", (".ttc",), "binary", True, "TrueType font collection", rfcs=("RFC 8081",), programs=("Font Book", "FontForge")),

    # --- TypeScript (ambiguous with .ts) ---
    MimeEntry("text/typescript", (".ts", ".tsx", ".mts", ".cts"), "text", True, "TypeScript source code", aliases=("application/typescript",), programs=("tsc", "Node.js", "VS Code", "web browsers")),
    MimeEntry("text/jsx", (".jsx",), "text", True, "JSX (React) source code", programs=("Node.js", "VS Code", "web browsers")),

    # --- Additional ---
    MimeEntry("application/x-bat", (".bat", ".cmd"), "text", True, "Windows batch script", programs=("cmd.exe", "PowerShell")),
    MimeEntry("application/x-powershell", (".ps1", ".psm1", ".psd1"), "text", True, "PowerShell script", programs=("PowerShell", "VS Code")),
    MimeEntry("application/x-msdownload", (), "binary", True, "Windows executable (generic)", aliases=("application/exe",), programs=("Windows",)),
    MimeEntry("application/x-registry", (".reg",), "text", True, "Windows Registry file", programs=("regedit",)),
    MimeEntry("application/x-ipynb+json", (".ipynb",), "text", True, "Jupyter Notebook", programs=("JupyterLab", "VS Code", "Google Colab")),
    MimeEntry("application/vnd.apple.mpegurl", (".m3u8",), "text", True, "HLS playlist", programs=("VLC", "web browsers", "ffmpeg")),
    MimeEntry("application/x-subrip", (".srt",), "text", True, "SubRip subtitle", programs=("VLC", "mpv", "Subtitle Edit")),
    MimeEntry("text/vtt", (".vtt",), "text", True, "WebVTT subtitle", programs=("web browsers", "VLC", "mpv")),
    MimeEntry("application/manifest+json", (".webmanifest",), "text", True, "Web app manifest", programs=("web browsers",)),
    MimeEntry("application/vnd.google-earth.kml+xml", (".kml",), "text", True, "Google Earth KML", programs=("Google Earth",)),
    MimeEntry("application/vnd.google-earth.kmz", (".kmz",), "binary", False, "Google Earth KMZ (compressed KML)", programs=("Google Earth",)),
    MimeEntry("application/vnd.amazon.ebook", (".azw", ".azw3"), "binary", False, "Amazon Kindle ebook", programs=("Kindle", "Calibre")),
    MimeEntry("application/x-mobipocket-ebook", (".mobi",), "binary", False, "Mobipocket ebook", programs=("Kindle", "Calibre")),
    MimeEntry("message/rfc822", (".eml", ".mht", ".mhtml"), "text", True, "Email message", rfcs=("RFC 5322",), programs=("Outlook", "Thunderbird")),
    MimeEntry("model/gltf+json", (".gltf",), "text", True, "glTF 3D model (JSON)", programs=("Blender", "three.js", "web browsers")),
    MimeEntry("model/gltf-binary", (".glb",), "binary", True, "glTF 3D model (binary)", programs=("Blender", "three.js", "web browsers")),
    MimeEntry("model/stl", (".stl",), "binary", True, "STL 3D model (stereolithography)", programs=("Blender", "Cura", "PrusaSlicer")),
    MimeEntry("model/obj", (".obj",), "text", True, "Wavefront OBJ 3D model", programs=("Blender", "Maya", "3ds Max")),
    MimeEntry("multipart/form-data", (), "binary", False, "Multipart form data (file uploads)", rfcs=("RFC 7578",), programs=("web browsers", "curl")),
)


# ═══════════════════════════════════════════════════════════════════
# Normalization helpers
# ═══════════════════════════════════════════════════════════════════

def _normalize_ext(ext: str) -> str:
    """Normalize extension: lowercase, ensure leading dot."""
    ext = ext.strip().lower()
    if ext and not ext.startswith("."):
        ext = "." + ext
    return ext


def _normalize_mime(mime: str) -> str:
    """Normalize MIME type: lowercase, strip whitespace."""
    return mime.strip().lower()


# ═══════════════════════════════════════════════════════════════════
# Lazy index building
# ═══════════════════════════════════════════════════════════════════

_ext_index: dict[str, list[MimeEntry]] | None = None
_mime_index: dict[str, MimeEntry] | None = None
_alias_index: dict[str, MimeEntry] | None = None


def _build_indexes() -> None:
    global _ext_index, _mime_index, _alias_index
    _ext_index = {}
    _mime_index = {}
    _alias_index = {}
    for entry in MIME_DATABASE:
        _mime_index[_normalize_mime(entry.mime_type)] = entry
        for ext in entry.extensions:
            norm = _normalize_ext(ext)
            if norm not in _ext_index:
                _ext_index[norm] = []
            _ext_index[norm].append(entry)
        for alias in entry.aliases:
            akey = _normalize_mime(alias)
            if akey not in _alias_index:
                _alias_index[akey] = entry


def _ensure_indexes() -> None:
    if _ext_index is None:
        _build_indexes()


# ═══════════════════════════════════════════════════════════════════
# Lookup Result
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LookupResult:
    """Result of an extension lookup, possibly ambiguous."""
    extension: str
    entries: tuple[MimeEntry, ...]
    is_ambiguous: bool

    @property
    def primary(self) -> MimeEntry | None:
        return self.entries[0] if self.entries else None


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def lookup_extension(ext: str) -> LookupResult:
    """Look up MIME type(s) for a file extension. Returns all matches."""
    _ensure_indexes()
    assert _ext_index is not None
    norm = _normalize_ext(ext)
    entries = _ext_index.get(norm, [])
    return LookupResult(extension=norm, entries=tuple(entries), is_ambiguous=len(entries) > 1)


def lookup_mime_type(mime: str) -> MimeEntry | None:
    """Look up a MIME type by canonical name or alias."""
    _ensure_indexes()
    assert _mime_index is not None and _alias_index is not None
    norm = _normalize_mime(mime)
    return _mime_index.get(norm) or _alias_index.get(norm)


def reverse_lookup(mime: str) -> tuple[str, ...]:
    """Get all extensions for a MIME type."""
    entry = lookup_mime_type(mime)
    return entry.extensions if entry else ()


def search_mime_types(query: str) -> list[MimeEntry]:
    """Search MIME types by keyword (case-insensitive substring)."""
    _ensure_indexes()
    q = query.strip().lower()
    if not q:
        return []
    results: list[MimeEntry] = []
    seen: set[str] = set()
    for entry in MIME_DATABASE:
        if entry.mime_type in seen:
            continue
        searchable = " ".join([
            entry.mime_type, entry.description,
            " ".join(entry.extensions), " ".join(entry.aliases),
            " ".join(entry.programs), entry.kind,
        ]).lower()
        if q in searchable:
            results.append(entry)
            seen.add(entry.mime_type)
    return results


def is_ambiguous(ext: str) -> bool:
    """Check if an extension maps to multiple MIME types."""
    return lookup_extension(ext).is_ambiguous


def get_ambiguous_extensions() -> dict[str, list[MimeEntry]]:
    """Get all extensions that map to multiple MIME types."""
    _ensure_indexes()
    assert _ext_index is not None
    return {ext: entries for ext, entries in sorted(_ext_index.items()) if len(entries) > 1}


def get_all_extensions() -> list[str]:
    """Get all known extensions, sorted."""
    _ensure_indexes()
    assert _ext_index is not None
    return sorted(_ext_index.keys())


def get_all_mime_types() -> list[str]:
    """Get all canonical MIME type strings, sorted."""
    _ensure_indexes()
    assert _mime_index is not None
    return sorted(_mime_index.keys())


# ═══════════════════════════════════════════════════════════════════
# Formatting
# ═══════════════════════════════════════════════════════════════════

def _entry_to_dict(entry: MimeEntry) -> dict:
    d: dict = {
        "mime_type": entry.mime_type,
        "extensions": list(entry.extensions),
        "kind": entry.kind,
        "compressible": entry.compressible,
        "description": entry.description,
    }
    if entry.aliases:
        d["aliases"] = list(entry.aliases)
    if entry.rfcs:
        d["rfcs"] = list(entry.rfcs)
    if entry.programs:
        d["programs"] = list(entry.programs)
    return d


def format_lookup_result(result: LookupResult, as_json: bool = False) -> str:
    if not result.entries:
        if as_json:
            return json.dumps({"extension": result.extension, "matches": []}, indent=2)
        return f"No MIME type found for extension: {result.extension}"
    if as_json:
        return json.dumps({
            "extension": result.extension,
            "ambiguous": result.is_ambiguous,
            "matches": [_entry_to_dict(e) for e in result.entries],
        }, indent=2)
    lines: list[str] = []
    if result.is_ambiguous:
        lines.append(f"Extension {result.extension} is AMBIGUOUS — {len(result.entries)} interpretations:")
        lines.append("")
        for i, entry in enumerate(result.entries, 1):
            lines.append(f"  [{i}] {entry.mime_type}")
            lines.append(f"      {entry.description}")
            lines.append(f"      Kind: {entry.kind}  |  Compressible: {'yes' if entry.compressible else 'no'}")
            if entry.programs:
                lines.append(f"      Programs: {', '.join(entry.programs)}")
            if entry.rfcs:
                lines.append(f"      RFCs: {', '.join(entry.rfcs)}")
            if entry.aliases:
                lines.append(f"      Aliases: {', '.join(entry.aliases)}")
            lines.append("")
    else:
        entry = result.entries[0]
        lines.append(f"{result.extension}  →  {entry.mime_type}")
        lines.append(f"  {entry.description}")
        lines.append(f"  Kind: {entry.kind}  |  Compressible: {'yes' if entry.compressible else 'no'}")
        if entry.extensions and len(entry.extensions) > 1:
            others = [e for e in entry.extensions if e != result.extension]
            if others:
                lines.append(f"  Other extensions: {', '.join(others)}")
        if entry.programs:
            lines.append(f"  Programs: {', '.join(entry.programs)}")
        if entry.rfcs:
            lines.append(f"  RFCs: {', '.join(entry.rfcs)}")
        if entry.aliases:
            lines.append(f"  Aliases: {', '.join(entry.aliases)}")
    return "\n".join(lines)


def format_info(entry: MimeEntry, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(_entry_to_dict(entry), indent=2)
    lines = [
        f"MIME Type:     {entry.mime_type}",
        f"Description:   {entry.description}",
        f"Kind:          {entry.kind}",
        f"Compressible:  {'yes' if entry.compressible else 'no'}",
    ]
    if entry.extensions:
        lines.append(f"Extensions:    {', '.join(entry.extensions)}")
    else:
        lines.append("Extensions:    (none)")
    if entry.aliases:
        lines.append(f"Aliases:       {', '.join(entry.aliases)}")
    if entry.rfcs:
        lines.append(f"RFCs:          {', '.join(entry.rfcs)}")
    if entry.programs:
        lines.append(f"Programs:      {', '.join(entry.programs)}")
    return "\n".join(lines)


def format_search_results(results: list[MimeEntry], query: str, as_json: bool = False) -> str:
    if as_json:
        return json.dumps({"query": query, "count": len(results), "results": [_entry_to_dict(e) for e in results]}, indent=2)
    if not results:
        return f"No MIME types matching: {query}"
    lines = [f"Found {len(results)} MIME type(s) matching \"{query}\":", ""]
    for entry in results:
        exts = ", ".join(entry.extensions) if entry.extensions else "(none)"
        lines.append(f"  {entry.mime_type}")
        lines.append(f"    {entry.description}  [{entry.kind}]")
        lines.append(f"    Extensions: {exts}")
        lines.append("")
    return "\n".join(lines).rstrip()
