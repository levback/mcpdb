from importlib.metadata import distribution
from pathlib import Path


def test_no_namespace_packages(project_root: Path) -> None:
    package_distribution = distribution("mcpdb")

    assert package_distribution.metadata["Name"] == "mcpdb"
    assert (project_root / "src" / "mcpdb" / "__init__.py").is_file()
