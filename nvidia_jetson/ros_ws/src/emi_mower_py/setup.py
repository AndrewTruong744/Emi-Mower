from setuptools import find_packages, setup


package_name = "emi_mower_py"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=[
        "setuptools",
        "numpy",
        "eclipse-zenoh>=1.9.0",
        "livekit>=1.0.0",
    ],
    zip_safe=True,
    entry_points={
        "console_scripts": [
            "livekit_node = emi_mower_py.nodes.livekit_node:main",
        ],
    },
)
