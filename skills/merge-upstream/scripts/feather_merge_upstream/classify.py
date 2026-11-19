"""Advice only: which changed paths are test support, fixtures, runner configuration or build configuration.

The rule is matched on the path's text alone, case-insensitively, and is stated in the output so a reader can judge
what it does and does not catch; a path it misses is not thereby unrelated to how acceptance is checked."""
from fnmatch import fnmatchcase

TEST_DIRECTORIES = {"test", "tests", "testing", "__tests__", "testdata", "test-data", "test_data"}
TEST_FILES = ("test_*", "*_test.*", "*.test.*", "*.spec.*", "*_spec.*", "conftest.py")
FIXTURE_DIRECTORIES = {"fixture", "fixtures", "__fixtures__", "__snapshots__"}
RUNNER_FILES = ("pytest.ini", "tox.ini", "noxfile.py", "conftest.py", ".coveragerc", "jest.config.*",
                "vitest.config.*", "karma.conf.*", "playwright.config.*", "cypress.config.*", ".mocharc.*",
                "phpunit.xml*", ".gitlab-ci.yml", ".travis.yml", "azure-pipelines.yml", "jenkinsfile")
RUNNER_DIRECTORIES = (".github/workflows/", ".circleci/", ".buildkite/")
BUILD_FILES = ("pyproject.toml", "setup.py", "setup.cfg", "requirements*.txt", "pipfile", "pipfile.lock",
               "poetry.lock", "uv.lock", "package.json", "package-lock.json", "pnpm-lock.yaml",
               "pnpm-workspace.yaml", "yarn.lock", "tsconfig*.json", "go.mod", "go.sum", "go.work", "cargo.toml",
               "cargo.lock", "makefile", "gnumakefile", "*.mk", "cmakelists.txt", "*.cmake", "build.gradle*",
               "settings.gradle*", "pom.xml", "dockerfile", "*.dockerfile", "docker-compose*.yml",
               "docker-compose*.yaml", ".gitmodules", ".gitattributes", "plugin.json")

RULE = ("Matched on the path text, case-insensitively. test-support: a directory component named "
        + ", ".join(sorted(TEST_DIRECTORIES)) + "; or a file name matching " + ", ".join(TEST_FILES)
        + ". fixtures: a directory component named " + ", ".join(sorted(FIXTURE_DIRECTORIES))
        + ". runner-configuration: a file name matching " + ", ".join(RUNNER_FILES) + "; or a path under "
        + ", ".join(RUNNER_DIRECTORIES) + ". build-configuration: a file name matching " + ", ".join(BUILD_FILES)
        + ". A path can be in several classes; a path in none is not thereby unrelated to how acceptance is "
        "checked.")


def classes(path: str) -> list[str]:
    lowered = path.lower()
    parts = lowered.split("/")
    directories, name = parts[:-1], parts[-1]
    found = []
    if TEST_DIRECTORIES.intersection(directories) or any(fnmatchcase(name, pattern) for pattern in TEST_FILES):
        found.append("test-support")
    if FIXTURE_DIRECTORIES.intersection(directories):
        found.append("fixtures")
    if (any(fnmatchcase(name, pattern) for pattern in RUNNER_FILES)
            or any(lowered.startswith(prefix) for prefix in RUNNER_DIRECTORIES)):
        found.append("runner-configuration")
    if any(fnmatchcase(name, pattern) for pattern in BUILD_FILES):
        found.append("build-configuration")
    return found
