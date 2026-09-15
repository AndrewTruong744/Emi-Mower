"""Atomic persistence for the boundary package's signed downloads."""

from pathlib import Path
from urllib.request import urlopen


def download_cutout(url: str, destination: Path) -> None:
    """Download atomically so analysis never observes a partial image."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.part")
    with urlopen(url, timeout=30) as response, temporary.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    temporary.replace(destination)
