#!/usr/bin/env python3
"""Cross-language parity and build verification for refinery-roborio-mcp.

Checks that Java, C++, and Python implementations all define the same
MCP tool names, server constants, JSON-RPC methods, and public API surface.
Also runs builds and tests where possible.
"""

import os
import re
import subprocess
import sys

# ── Canonical definitions ────────────────────────────────────────────────────
# These are the single source of truth — every language must match.

EXPECTED_TOOLS = [
    "get_robot_status",
    "get_battery_voltage",
    "get_match_info",
    "get_robot_stats",
    "get_connection_info",
    "get_subsystems",
    "get_networktables",
]

EXPECTED_CONSTANTS = {
    "server_name": "refinery-roborio-mcp",
    "server_version": "0.0.3",
    "mcp_protocol_version": "2025-03-26",
    "default_port": "8765",
}

EXPECTED_MCP_METHODS = [
    "initialize",
    "notifications/initialized",
    "tools/list",
    "tools/call",
    "ping",
]

# ── Paths ────────────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAVA_DIR = os.path.join(ROOT, "src", "main", "java", "com", "bionanomics", "refinery", "mcp")
CPP_DIR = os.path.join(ROOT, "src", "main", "cpp")
CPP_INCLUDE = os.path.join(ROOT, "src", "main", "include", "refinery", "mcp")
PY_DIR = os.path.join(ROOT, "src", "main", "python", "refinery_roborio_mcp")
PY_TESTS = os.path.join(ROOT, "src", "main", "python", "tests")

# ── Helpers ──────────────────────────────────────────────────────────────────

failures = []


def fail(msg):
    failures.append(msg)
    print(f"  FAIL: {msg}")


def ok(msg):
    print(f"  OK:   {msg}")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def find_quoted_strings(text, pattern):
    """Find all quoted strings matching a regex pattern in text."""
    return re.findall(pattern, text)

# ── File existence checks ────────────────────────────────────────────────────

JAVA_FILES = [
    "RoboRioMcpServer.java",
    "RoboRioMcpTools.java",
    "JsonRpc.java",
    "JsonParser.java",
    "JsonMap.java",
    "JsonList.java",
    "JsonUtil.java",
]

CPP_HEADERS = [
    "RoboRioMcpServer.h",
    "RoboRioMcpTools.h",
    "JsonRpc.h",
]

CPP_SOURCES = [
    "RoboRioMcpServer.cpp",
    "RoboRioMcpTools.cpp",
    "JsonRpc.cpp",
]

PY_MODULES = [
    "__init__.py",
    "mcp_server.py",
    "mcp_tools.py",
    "json_rpc.py",
]


def check_files_exist():
    print("\n── File existence ──")
    for name in JAVA_FILES:
        path = os.path.join(JAVA_DIR, name)
        if os.path.isfile(path):
            ok(f"Java: {name}")
        else:
            fail(f"Java: missing {name}")

    for name in CPP_HEADERS:
        path = os.path.join(CPP_INCLUDE, name)
        if os.path.isfile(path):
            ok(f"C++ header: {name}")
        else:
            fail(f"C++ header: missing {name}")

    for name in CPP_SOURCES:
        path = os.path.join(CPP_DIR, name)
        if os.path.isfile(path):
            ok(f"C++ source: {name}")
        else:
            fail(f"C++ source: missing {name}")

    for name in PY_MODULES:
        path = os.path.join(PY_DIR, name)
        if os.path.isfile(path):
            ok(f"Python: {name}")
        else:
            fail(f"Python: missing {name}")

# ── Tool name parity ────────────────────────────────────────────────────────

def extract_tool_names_java():
    src = read(os.path.join(JAVA_DIR, "RoboRioMcpTools.java"))
    return re.findall(r'defineTool\(\s*"([^"]+)"', src)


def extract_tool_names_cpp():
    src = read(os.path.join(CPP_DIR, "RoboRioMcpTools.cpp"))
    return re.findall(r'DefineTool\(\s*"([^"]+)"', src)


def extract_tool_names_python():
    src = read(os.path.join(PY_DIR, "mcp_tools.py"))
    return re.findall(r'_define_tool\(\s*"([^"]+)"', src)


def check_tool_parity():
    print("\n── MCP tool parity ──")
    java_tools = extract_tool_names_java()
    cpp_tools = extract_tool_names_cpp()
    py_tools = extract_tool_names_python()

    for lang, tools in [("Java", java_tools), ("C++", cpp_tools), ("Python", py_tools)]:
        if sorted(tools) == sorted(EXPECTED_TOOLS):
            ok(f"{lang}: all {len(EXPECTED_TOOLS)} tools present")
        else:
            missing = set(EXPECTED_TOOLS) - set(tools)
            extra = set(tools) - set(EXPECTED_TOOLS)
            if missing:
                fail(f"{lang}: missing tools: {missing}")
            if extra:
                fail(f"{lang}: unexpected tools: {extra}")

# ── Server constant parity ──────────────────────────────────────────────────

def extract_constants_java():
    src = read(os.path.join(JAVA_DIR, "RoboRioMcpServer.java"))
    return {
        "server_name": re.search(r'SERVER_NAME\s*=\s*"([^"]+)"', src),
        "server_version": re.search(r'SERVER_VERSION\s*=\s*"([^"]+)"', src),
        "mcp_protocol_version": re.search(r'MCP_PROTOCOL_VERSION\s*=\s*"([^"]+)"', src),
        "default_port": re.search(r'DEFAULT_PORT\s*=\s*(\d+)', src),
    }


def extract_constants_cpp():
    src = read(os.path.join(CPP_INCLUDE, "RoboRioMcpServer.h"))
    return {
        "server_name": re.search(r'kServerName\s*=\s*"([^"]+)"', src),
        "server_version": re.search(r'kServerVersion\s*=\s*"([^"]+)"', src),
        "mcp_protocol_version": re.search(r'kMcpProtocolVersion\s*=\s*"([^"]+)"', src),
        "default_port": re.search(r'kDefaultPort\s*=\s*(\d+)', src),
    }


def extract_constants_python():
    src = read(os.path.join(PY_DIR, "mcp_server.py"))
    return {
        "server_name": re.search(r'SERVER_NAME\s*=\s*"([^"]+)"', src),
        "server_version": re.search(r'SERVER_VERSION\s*=\s*"([^"]+)"', src),
        "mcp_protocol_version": re.search(r'MCP_PROTOCOL_VERSION\s*=\s*"([^"]+)"', src),
        "default_port": re.search(r'DEFAULT_PORT\s*=\s*(\d+)', src),
    }


def check_constant_parity():
    print("\n── Server constant parity ──")
    extractors = [
        ("Java", extract_constants_java),
        ("C++", extract_constants_cpp),
        ("Python", extract_constants_python),
    ]
    for lang, extractor in extractors:
        matches = extractor()
        for key, expected in EXPECTED_CONSTANTS.items():
            m = matches.get(key)
            if m is None:
                fail(f"{lang}: constant {key} not found")
            elif m.group(1) != expected:
                fail(f"{lang}: {key} = '{m.group(1)}', expected '{expected}'")
            else:
                ok(f"{lang}: {key} = '{expected}'")

# ── MCP method parity ───────────────────────────────────────────────────────

def extract_methods_java():
    src = read(os.path.join(JAVA_DIR, "RoboRioMcpServer.java"))
    # Java uses string comparisons like case "initialize":, "method".equals(...)
    # or string literals in switch/if blocks
    methods = set()
    for m in re.finditer(r'(?:case\s+|equals\()"([^"]+)"', src):
        if "/" in m.group(1) or m.group(1) in ("initialize", "ping"):
            methods.add(m.group(1))
    return methods


def extract_methods_cpp():
    src = read(os.path.join(CPP_DIR, "RoboRioMcpServer.cpp"))
    methods = set()
    for m in re.finditer(r'method\s*==\s*"([^"]+)"', src):
        methods.add(m.group(1))
    return methods


def extract_methods_python():
    src = read(os.path.join(PY_DIR, "mcp_server.py"))
    methods = set()
    for m in re.finditer(r'method\s*==\s*"([^"]+)"', src):
        methods.add(m.group(1))
    return methods


def check_method_parity():
    print("\n── MCP method parity ──")
    java_methods = extract_methods_java()
    cpp_methods = extract_methods_cpp()
    py_methods = extract_methods_python()
    expected = set(EXPECTED_MCP_METHODS)

    for lang, methods in [("Java", java_methods), ("C++", cpp_methods), ("Python", py_methods)]:
        if methods >= expected:
            ok(f"{lang}: all {len(expected)} MCP methods handled")
        else:
            missing = expected - methods
            fail(f"{lang}: missing method handlers: {missing}")

# ── Public API checks ───────────────────────────────────────────────────────

def check_java_api():
    """Verify key public methods exist in Java sources."""
    print("\n── Java public API ──")
    checks = [
        ("RoboRioMcpServer.java", [
            r"public\s+static\s+void\s+start\s*\(\s*\)",
            r"public\s+static\s+void\s+start\s*\(\s*int",
            r"public\s+static\s+void\s+stop\s*\(",
        ]),
        ("RoboRioMcpTools.java", [
            r"public\s+static\s+JsonList\s+getToolDefinitions\s*\(",
            r"public\s+static\s+JsonMap\s+callTool\s*\(",
        ]),
        ("JsonRpc.java", [
            r"public\s+static\s+String\s+resultResponse\s*\(",
            r"public\s+static\s+String\s+errorResponse\s*\(",
        ]),
    ]
    for filename, patterns in checks:
        src = read(os.path.join(JAVA_DIR, filename))
        for pattern in patterns:
            if re.search(pattern, src):
                name = re.search(r"\w+\s*\(", pattern.replace(r"\s+", " ").replace(r"\(", "("))
                ok(f"Java {filename}: {pattern.split('s+')[-1][:40]}…")
            else:
                fail(f"Java {filename}: missing pattern {pattern[:60]}")


def check_cpp_api():
    """Verify key public methods exist in C++ headers."""
    print("\n── C++ public API ──")
    checks = [
        ("RoboRioMcpServer.h", [
            r"static\s+void\s+Start\s*\(\s*\)",
            r"static\s+void\s+Start\s*\(\s*int",
            r"static\s+void\s+Stop\s*\(",
        ]),
        ("RoboRioMcpTools.h", [
            r"static\s+wpi::json\s+GetToolDefinitions\s*\(",
            r"static\s+wpi::json\s+CallTool\s*\(",
        ]),
        ("JsonRpc.h", [
            r"static\s+std::string\s+ResultResponse\s*\(",
            r"static\s+std::string\s+ErrorResponse\s*\(",
        ]),
    ]
    for filename, patterns in checks:
        src = read(os.path.join(CPP_INCLUDE, filename))
        for pattern in patterns:
            if re.search(pattern, src):
                ok(f"C++ {filename}: found {pattern[:50]}…")
            else:
                fail(f"C++ {filename}: missing pattern {pattern[:60]}")


def check_python_api():
    """Verify key public functions/classes exist in Python modules."""
    print("\n── Python public API ──")
    checks = [
        ("mcp_server.py", [
            r"class\s+RoboRioMcpServer",
            r"def\s+start\s*\(",
            r"def\s+stop\s*\(",
        ]),
        ("mcp_tools.py", [
            r"class\s+RoboRioMcpTools",
            r"def\s+get_tool_definitions\s*\(",
            r"def\s+call_tool\s*\(",
        ]),
        ("json_rpc.py", [
            r"def\s+result_response\s*\(",
            r"def\s+error_response\s*\(",
        ]),
    ]
    for filename, patterns in checks:
        src = read(os.path.join(PY_DIR, filename))
        for pattern in patterns:
            if re.search(pattern, src):
                ok(f"Python {filename}: found {pattern[:50]}…")
            else:
                fail(f"Python {filename}: missing pattern {pattern[:60]}")

# ── Version alignment ───────────────────────────────────────────────────────

def check_version_alignment():
    """Verify version strings match across build files."""
    print("\n── Version alignment ──")
    gradle = read(os.path.join(ROOT, "build.gradle"))
    pyproject = read(os.path.join(ROOT, "src", "main", "python", "pyproject.toml"))
    vendordep = os.path.join(ROOT, "vendordep", "refinery-roborio-mcp.json")

    # build.gradle version
    m = re.search(r"version\s*=\s*'([^']+)'", gradle)
    gradle_ver = m.group(1) if m else None

    # pyproject.toml version
    m = re.search(r'version\s*=\s*"([^"]+)"', pyproject)
    pyproject_ver = m.group(1) if m else None

    expected_ver = EXPECTED_CONSTANTS["server_version"]

    if gradle_ver == expected_ver:
        ok(f"build.gradle version = '{gradle_ver}'")
    else:
        fail(f"build.gradle version = '{gradle_ver}', expected '{expected_ver}'")

    if pyproject_ver == expected_ver:
        ok(f"pyproject.toml version = '{pyproject_ver}'")
    else:
        fail(f"pyproject.toml version = '{pyproject_ver}', expected '{expected_ver}'")

    if os.path.isfile(vendordep):
        vd = read(vendordep)
        m = re.search(r'"version"\s*:\s*"([^"]+)"', vd)
        vd_ver = m.group(1) if m else None
        if vd_ver == expected_ver:
            ok(f"vendordep version = '{vd_ver}'")
        else:
            fail(f"vendordep version = '{vd_ver}', expected '{expected_ver}'")
    else:
        fail("vendordep/refinery-roborio-mcp.json not found")

# ── Build checks ────────────────────────────────────────────────────────────

def run_gradle_build():
    """Run ./gradlew build (Java compile + tests)."""
    print("\n── Java build (Gradle) ──")
    gradlew = os.path.join(ROOT, "gradlew")
    if not os.path.isfile(gradlew):
        fail("gradlew not found")
        return
    result = subprocess.run(
        [gradlew, "build", "-x", "javadoc"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode == 0:
        ok("Gradle build succeeded")
    else:
        fail(f"Gradle build failed:\n{result.stdout}\n{result.stderr}")


def run_python_tests():
    """Run Python unit tests (pytest if available, else direct execution)."""
    print("\n── Python tests ──")
    py_cwd = os.path.join(ROOT, "src", "main", "python")
    test_files = [
        os.path.join(PY_TESTS, "test_json_rpc.py"),
        os.path.join(PY_TESTS, "test_mcp_server.py"),
    ]

    # Try pytest first, fall back to running test files directly
    result = subprocess.run(
        [sys.executable, "-m", "pytest", PY_TESTS, "-v", "--tb=short"],
        cwd=py_cwd, capture_output=True, text=True, timeout=60,
    )
    if result.returncode == 0:
        ok(f"Python tests passed (pytest)\n{result.stdout}")
        return

    # pytest not available — run each test file directly
    if "No module named pytest" in result.stderr:
        print("  (pytest not found, running tests directly)")
        for tf in test_files:
            name = os.path.basename(tf)
            r = subprocess.run(
                [sys.executable, tf], cwd=py_cwd,
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 0:
                ok(f"Python {name} passed")
            else:
                fail(f"Python {name} failed:\n{r.stdout}\n{r.stderr}")
    else:
        fail(f"Python tests failed:\n{result.stdout}\n{result.stderr}")

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("refinery-roborio-mcp: Cross-Language Parity & Build Test")
    print("=" * 60)

    check_files_exist()
    check_tool_parity()
    check_constant_parity()
    check_method_parity()
    check_java_api()
    check_cpp_api()
    check_python_api()
    check_version_alignment()

    # Build checks (can be skipped with --no-build)
    if "--no-build" not in sys.argv:
        run_gradle_build()
        run_python_tests()
    else:
        print("\n── Builds skipped (--no-build) ──")

    # Summary
    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED: {len(failures)} issue(s)")
        for f in failures:
            print(f"  • {f}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
