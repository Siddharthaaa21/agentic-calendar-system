import os
import runpy
import sys

# Ensure repo root and backend are discoverable
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

backend_dir = os.path.join(root_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

frontend_app_path = os.path.join(root_dir, "frontend", "app.py")
runpy.run_path(frontend_app_path, run_name="__main__")
