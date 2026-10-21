"""Rule-based entity extraction from cleaned CI logs (v0.2.5 knowledge graph).

Each rule maps a recognisable pattern to a typed entity:

    tool       what was running                pytest, cargo, eslint, ...
    error      what kind of thing went wrong   tests_failed, AssertionError, ...
    package    a dependency named in an error
    exit_code  the process exit status

The rules are deterministic on purpose: every edge in the graph can be traced
back to the line that produced it. They were written against the 51 "dev"
logs only; see experiments/002_graphrag_vs_flat.md for the held-out result.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Entity:
    kind: str
    name: str

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.name}"


def _any(patterns: list[str]) -> re.Pattern:
    """One multiline regex matching any of the given alternatives."""
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.MULTILINE)


# --- tools -----------------------------------------------------------------

# A tool counts when it is invoked (at the start of a command line, possibly
# through a runner such as `python -m` or `yarn`), not when its name merely
# appears in a path or sentence.
_RUNNERS = [
    r"(?:python3?|py)\s+-m\s+",
    r"npx\s+",
    r"yarn\s+(?:run\s+)?",
    r"pnpm\s+(?:run\s+|exec\s+)?",
    r"npm\s+(?:run|exec)\s+",
    r"uv\s+run\s+",
    r"uvx\s+",
    r"poetry\s+run\s+",
    r"pipx\s+run\s+",
]
_CMD_PREFIX = (
    r"^\s*(?:\[command\]|\$\s|\+\s|>\s|Run\s)?(?:" + "|".join(_RUNNERS) + r")?(?:\S*[\\/])?"
)
_INVOKED_TOOLS = [
    "pytest", "tox", "nox", "ruff", "black", "flake8", "pylint", "mypy", "pyright",
    "pre-commit", "sphinx-build", "mkdocs", "twine", "cibuildwheel", "pip", "uv",
    "poetry", "hatch", "pdm", "conda", "cargo", "rustc", "rustup", "npm", "yarn",
    "pnpm", "jest", "vitest", "eslint", "prettier", "tsc", "esbuild", "webpack",
    "rollup", "playwright", "docker", "cmake", "gradle", "mvn", "actionlint",
    "towncrier", "codecov", "bazel", "ninja", "meson",
]
_INVOKED = {
    tool: re.compile(
        _CMD_PREFIX + re.escape(tool) + r"(?:\.exe|\.cmd)?(?=\s|$)", re.MULTILINE
    )
    for tool in _INVOKED_TOOLS
}

# Characteristic output, for when the invocation itself is not in the log.
_TOOL_OUTPUT = {
    "pytest": [
        r"=+ (?:test session starts|short test summary info|FAILURES|ERRORS) =+",
        r"=+ .*\b\d+ (?:passed|failed|errors?)\b.* in [\d.]+s",
    ],
    "jest": [r"^Test Suites:\s+\d+", r"^Snapshots:\s+\d+"],
    "cargo": [
        r"^\s*(?:Compiling|Finished|Running) \S+",
        r"error: could not compile `",
        r"test result: (?:ok|FAILED)\.",
    ],
    "rustc": [r"error\[E\d{4}\]", r"rustc --explain"],
    "mypy": [r"Found \d+ errors? in \d+ files? \(checked \d+ source files?\)"],
    "pyright": [r"\d+ errors?, \d+ warnings?, \d+ informations?"],
    "eslint": [r"✖ \d+ problems? \(\d+ errors?, \d+ warnings?\)"],
    "pre-commit": [r"^- hook id: "],
    "tox": [r"^\s*\S+: FAIL code \d+", r"evaluation failed :\("],
    "esbuild": [r"\[plugin: [\w-]+\]", r"✘ \[ERROR\]"],
    "sphinx-build": [r"build finished with problems", r"Sphinx v\d", r"\(line\s+\d+\) broken "],
    "black": [r"^would reformat ", r"files? would be reformatted"],
    "make": [r"^make(?:\[\d+\])?: \*\*\* "],
    "yum": [r"Yum repo downloading error", r"\byum install "],
    "apt": [r"^E: ", r"^\s*(?:sudo )?apt(?:-get)? (?:install|update)"],
    "git": [r"^fatal: .*(?:repository|reference|remote|refspec)"],
    "gcc": [
        r"\b(?:gcc|cc|g\+\+|clang)(?:-\d+)?: (?:fatal )?error",
        r"error: command '.*(?:gcc|cc|clang)'",
    ],
    "node": [r"^node:internal/", r"^Node\.js v\d+"],
    "github-script": [r"core\.setFailed\("],
}
_TOOL_OUTPUT_RE = {tool: _any(patterns) for tool, patterns in _TOOL_OUTPUT.items()}

# --- error signatures ---------------------------------------------------------

_ERROR_RULES = {
    # tests
    "tests_failed": [
        r"=+ .*\b\d+ failed\b.* in [\d.]+s",
        r"^FAILED \S+::\S+",
        r"test result: FAILED",
        r"error: test run failed",
        r"^Tests:\s+\d+ failed",
        r"^Test Suites:\s+\d+ failed",
    ],
    "test_collection_error": [
        r"\d+ errors? during collection",
        r"=+ .*\b\d+ errors?\b.* in [\d.]+s",
        r"^ERROR \S+::\S+",
    ],
    "snapshot_mismatch": [r"(?i:\d+ snapshots? failed)", r"(?i:snapshot .* did not match)"],
    "assertion_failed": [r"assertion `[^`]*` failed", r"AssertionError", r"^\s*assert .* ==? "],
    # build / compile
    "compile_failed": [
        r"error: could not compile",
        r"error\[E\d{4}\]",
        r"(?i:compilation (?:failed|terminated))",
        r"error: command '.*(?:gcc|cc|clang)\S*' failed",
        r"\b(?:gcc|cc|clang)\S*: (?:fatal )?error",
        r"error: Command '\['(?:cc|gcc|clang)'",
    ],
    "bundle_failed": [
        r"✘ \[ERROR\]",
        r"ERROR: \[plugin: ",
        r"Build failed with \d+ errors?",
    ],
    "package_build_failed": [
        r"(?i:failed (?:to build|building) (?:wheel|sdist))",
        r"InvalidDistribution",
        r"Failed to build installable wheels",
        r"error: subprocess-exited-with-error",
    ],
    # types / lint / format
    "type_errors": [
        r"Found \d+ errors? in \d+ files?",
        r"[1-9]\d* errors?, \d+ warnings?, \d+ informations?",
        r"error TS\d+:",
        r": error: .*\[[a-z][a-z-]+\]\s*$",
    ],
    "format_diff": [
        r"^would reformat ",
        r"files? would be reformatted",
        r"Code style issues found",
        r"Oh no! 💥",
    ],
    "lint_errors": [
        r"✖ \d+ problems?",
        r"^Found \d+ errors?\.$",
        r"\b[A-Z]{1,3}\d{3,4} \[\*\]",
        r"(?i:\d+ errors? and \d+ warnings? potentially fixable)",
    ],
    "hook_failed": [r"^- hook id: .*\n(?:- .*\n)*?- exit code: [1-9]"],
    # dependencies
    "no_matching_distribution": [
        r"No matching distribution found",
        r"Could not find a version that satisfies",
        r"ResolutionImpossible",
        r"No solution found when resolving",
        r"(?i:unable to resolve dependency)",
        r"ERESOLVE",
    ],
    "module_not_found": [
        r"ModuleNotFoundError",
        r"No module named",
        r"Cannot find module",
        r"ImportError",
        r"Module not found: ",
    ],
    "lockfile_out_of_date": [
        r"(?i:lock ?file .*(?:needs to be updated|out of date|not up to date))",
        r"--locked` was provided",
        r"frozen-lockfile",
    ],
    "missing_export": [
        r"does not provide an export",
        r"has no exported member",
        r"is not exported from",
    ],
    # infrastructure
    "network_error": [
        r"Connection (?:refused|reset|timed out)",
        r"Could not resolve host",
        r"ECONNRESET|ETIMEDOUT",
        r"Curl error \(\d+\)",
        r"Timeout was reached",
        r"could not download file",
        r"Failed to download",
        r"(?:502|503|504) (?:Bad Gateway|Service Unavailable|Gateway Time-?out)",
        r"(?i:temporary failure in name resolution)",
    ],
    "rate_limited": [r"(?i:rate limit)", r"HTTP 429", r"Too Many Requests"],
    "step_timeout": [
        r"has timed out after \d+ minutes",
        r"exceeded the maximum execution time",
        r"The operation was canceled",
        r"(?i:timeout exceeded)",
        r"pexpect\.exceptions\.TIMEOUT",
    ],
    "out_of_memory": [
        r"(?i:out of memory)",
        r"OOMKilled",
        r"Cannot allocate memory",
        r"MemoryError",
        r"^Killed$",
    ],
    "disk_full": [r"No space left on device"],
    # CI configuration
    "command_not_found": [
        r"command not found",
        r"is not recognized as an internal or external command",
        r"(?i:could not find task)",
    ],
    "action_not_found": [
        r"Can't find 'action\.ya?ml'",
        r"Unable to resolve action",
        r"unable to find version",
    ],
    "workflow_invalid": [
        r"(?i:invalid workflow file)",
        r'label "[^"]+" is unknown',
    ],
    "artifact_missing": [
        r"(?i:artifact (?:directory )?(?:does not exist|not found|was not found))",
        r"no matching workflow run found",
        r"Unable to (?:find|download) artifact",
        r"No artifacts? found",
    ],
    "file_not_found": [r"No such file or directory", r"FileNotFoundError", r"ENOENT"],
    "permission_denied": [
        r"Permission denied",
        r"Resource not accessible by integration",
        r"EACCES",
        r"HTTP 403",
        r"(?i:refusing to check out)",
    ],
    # repository policy
    "changelog_required": [
        r"(?i:please add .* (?:change line|changelog))",
        r"(?i:no changelog entry)",
        r"(?i:news fragment)",
    ],
    "restricted_change": [
        r"(?i:restricted to organization members)",
        r"(?i:not allowed to (?:modify|change))",
    ],
    # docs
    "docs_problem": [
        r"(?i:broken link)",
        r"build finished with problems",
        r"reference target not found",
    ],
    # gate jobs and regression checks
    "gate_job": [r"alls?-green", r"Some of the required to succeed jobs failed"],
    "regression_detected": [r"(?i:new (?:project )?failures introduced)"],
}
_ERROR_RE = {name: _any(patterns) for name, patterns in _ERROR_RULES.items()}

# Language-level exception names, e.g. AssertionError, TypeError, IOException.
_EXCEPTION = re.compile(r"\b((?:[A-Z][a-z0-9]+)+(?:Error|Exception))\b")
_RUST_CODE = re.compile(r"error\[(E\d{4})\]")

# --- packages and exit codes --------------------------------------------------

_PACKAGE_RE = [
    re.compile(pattern, re.MULTILINE)
    for pattern in [
        r"No module named ['\"]?([A-Za-z_][\w.]*)",
        r"No matching distribution found for ([A-Za-z_][\w.-]*)",
        r"satisfies the requirement ([A-Za-z_][\w.-]*)",
        r"Cannot find module ['\"]([^'\"\s]+)['\"]",
        r"could not compile `([\w-]+)`",
        r"The requested module ['\"]([^'\"\s]+)['\"]",
    ]
]
_EXIT_CODE = re.compile(
    r"(?:exit code:?|exited with(?: code)?|FAIL code|failed with code) (\d{1,3})\b"
)


def extract_entities(cleaned_log: str) -> set[Entity]:
    """Return the typed entities found in a log already passed through clean_log()."""
    found: set[Entity] = set()

    for tool, pattern in _INVOKED.items():
        if pattern.search(cleaned_log):
            found.add(Entity("tool", tool))
    for tool, pattern in _TOOL_OUTPUT_RE.items():
        if pattern.search(cleaned_log):
            found.add(Entity("tool", tool))

    for name, pattern in _ERROR_RE.items():
        if pattern.search(cleaned_log):
            found.add(Entity("error", name))
    for name in _EXCEPTION.findall(cleaned_log):
        found.add(Entity("error", name))
    for code in _RUST_CODE.findall(cleaned_log):
        found.add(Entity("error", f"rustc_{code}"))

    for pattern in _PACKAGE_RE:
        for name in pattern.findall(cleaned_log):
            found.add(Entity("package", name.lower().split(".")[0]))
    for code in _EXIT_CODE.findall(cleaned_log):
        found.add(Entity("exit_code", code))

    return found
