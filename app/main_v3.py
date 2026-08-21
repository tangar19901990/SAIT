"""Compatibility launcher for SAIT v3.

The canonical application entry point is app.main. Keeping this file as a
thin wrapper prevents the v3 batch launcher from accidentally running an
older copy of the CLI/provider-command logic.
"""

from app.main import main


if __name__ == "__main__":
    main()
