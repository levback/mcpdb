from __future__ import annotations

from rich.table import Table


def build_profiles_table(rows: list[dict[str, str]]) -> Table:
    table = Table(title="profiles")
    table.add_column("name")
    table.add_column("backend")
    for row in rows:
        table.add_row(row["name"], row["backend"])
    return table


def build_tools_table(tool_names: list[str]) -> Table:
    table = Table(title="tools")
    table.add_column("name")
    table.add_column("op_class")
    table.add_column("profiles")
    for name in tool_names:
        table.add_row(name, "n/a", "*")
    return table
