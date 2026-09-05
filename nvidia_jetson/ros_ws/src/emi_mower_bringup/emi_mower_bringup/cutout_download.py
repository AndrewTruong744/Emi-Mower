"""Pure download helper shared by the ROS boundary-cutout node and its tests."""

from pathlib import Path
from urllib.request import urlopen


def download_cutout(url: str, destination: Path) -> None:
    """Download atomically so consumers never observe a partial boundary image."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.part")
    with urlopen(url, timeout=30) as response, temporary.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    temporary.replace(destination)
