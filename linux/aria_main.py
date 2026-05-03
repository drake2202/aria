"""PyInstaller-friendly entrypoint for Aria.

This imports the package module so relative imports inside legendonline work
when frozen into a single executable.
"""

from legendonline.__main__ import main


if __name__ == "__main__":
    main()
