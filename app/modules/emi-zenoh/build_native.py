#!/usr/bin/env python3
"""Build native Zenoh against the sibling fork; credentials never enter artifacts."""

import argparse
import os
import shutil
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
TARGETS = {"arm64-v8a": "aarch64-linux-android", "x86_64": "x86_64-linux-android"}
parser = argparse.ArgumentParser()
parser.add_argument("--android", action="store_true", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
output = Path(args.output)
sdk = Path(os.environ.get("ANDROID_HOME", str(Path.home() / "Library/Android/sdk")))
ndk = Path(os.environ.get("ANDROID_NDK_HOME", str(sdk / "ndk/27.1.12297006")))
host = "darwin-x86_64" if os.uname().sysname == "Darwin" else "linux-x86_64"
tools = ndk / "toolchains/llvm/prebuilt" / host / "bin"
abis = os.environ.get("EMI_ZENOH_ABIS", "arm64-v8a,x86_64").split(",")
for abi in abis:
    target = TARGETS[abi]
    subprocess.run(
        ["rustup", "target", "add", target, "--toolchain", "stable"], check=True
    )
    env = os.environ.copy()
    compiler = str(tools / f"{target}24-clang")
    env[f"CARGO_TARGET_{target.upper().replace('-', '_')}_LINKER"] = compiler
    env[f"CARGO_TARGET_{target.upper().replace('-', '_')}_RUSTFLAGS"] = (
        "-C link-arg=-Wl,-z,max-page-size=16384"
    )
    env[f"CC_{target.replace('-', '_')}"] = compiler
    env[f"AR_{target.replace('-', '_')}"] = str(tools / "llvm-ar")
    subprocess.run(
        [
            "cargo",
            "+stable",
            "build",
            "--locked",
            "--manifest-path",
            str(ROOT / "rust/Cargo.toml"),
            "--release",
            "--target",
            target,
        ],
        env=env,
        check=True,
    )
    destination = output / abi
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        ROOT / f"rust/target/{target}/release/libemi_zenoh_native.so", destination
    )
