import os

try:
    # Import the GUI entrypoint from the split module structure
    from gui import main
except ImportError:
    main = None


def _fallback_run():
    """Fallback behavior when gui module is not available.

    Attempts to read input.sql and prints a short status message
    so the script doesn't crash if the GUI module isn't present yet.
    """
    path = os.path.join(os.path.dirname(__file__), "input.sql")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            print("Loaded input.sql successfully (GUI module missing).")
            print("Preview (first 200 chars):")
            print(content[:200])
        except Exception as e:
            print(f"Error reading input.sql: {e}")
    else:
        print("input.sql not found and GUI module missing. Nothing to run.")


if __name__ == "__main__":
    import os
    if main is not None:
        main()
    else:
        _fallback_run()
