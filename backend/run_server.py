import sys
import os

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

if __name__ == "__main__":
    print("Starting run_server.py...", flush=True)
    try:
        from app.main import app
        print("FastAPI app imported successfully.", flush=True)
        import uvicorn
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", 8000))
        print(f"Imported uvicorn. Starting server on {host}:{port}...", flush=True)
        uvicorn.run(app, host=host, port=port, log_level="info")
    except Exception as e:
        import traceback
        print("FATAL ERROR IN RUN_SERVER:", flush=True)
        traceback.print_exc()
