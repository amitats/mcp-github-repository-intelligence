import re
from packaging.version import Version
from packaging.version import InvalidVersion


def clean_version(value: str | None) -> str | None:
    if not value:
        return None

    value = value.strip()

    value = re.sub(
        r"^[vV]",
        "",
        value,
    )

    return value


def compare_versions(
    current: str | None,
    latest: str | None,
) -> str:

    if not current or not latest:
        return "UNKNOWN"

    current_clean = clean_version(current)
    latest_clean = clean_version(latest)

    try:
        current_v = Version(current_clean)
        latest_v = Version(latest_clean)

        if current_v == latest_v:
            return "CURRENT"

        if current_v < latest_v:
            return "UPDATE_AVAILABLE"

        return "AHEAD_OF_LATEST"

    except InvalidVersion:
        return "UNKNOWN"