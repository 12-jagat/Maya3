import os
import sys

# Ensure backend directory is in python search path
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Change cwd to backend so local config and relative storage paths resolve cleanly
os.chdir(backend_dir)

if __name__ == "__main__":
    from app.main import app
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting MAYA backend on {host}:{port}...", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="info")
