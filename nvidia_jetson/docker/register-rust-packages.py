"""Register generated ROS Rust crates for colcon-ros-cargo's prefix lookup.

Jazzy's binary message packages ship share/<package>/rust/Cargo.toml without
the rust_packages resource entries expected by colcon-ros-cargo 0.2.
"""

import sys
import tomllib
from pathlib import Path

for argument in sys.argv[1:]:
    prefix = Path(argument)
    index = prefix / "share/ament_index/resource_index/rust_packages"
    for manifest in sorted((prefix / "share").glob("*/rust/Cargo.toml")):
        package = tomllib.loads(manifest.read_text())["package"]["name"]
        index.mkdir(parents=True, exist_ok=True)
        (index / package).touch()
