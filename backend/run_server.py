"""
Run the backend server with proper configuration
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
        access_log=True,
        # Increase limits to handle file uploads
        limit_concurrency=1000,
        limit_max_requests=10000,
        timeout_keep_alive=75,
        # This is critical - allows larger request bodies
        h11_max_incomplete_event_size=16777216,  # 16MB
    )

