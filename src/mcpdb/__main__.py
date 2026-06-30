from mcpdb import __version__


def render_version() -> str:
    return f"mcpdb {__version__}"


def main() -> None:
    print(render_version())


if __name__ == "__main__":
    main()
