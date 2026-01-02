import sys
import subprocess
from pathlib import Path


def main():
    """Launch the Streamlit viewer app."""
    app_path = Path(__file__).parent / "app.py"

    # Check if streamlit is installed
    import importlib.util

    if not importlib.util.find_spec("streamlit"):
        print("Error: Streamlit is not installed. Please install it with: pip install streamlit")
        sys.exit(1)

    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)] + sys.argv[1:]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        pass
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
