#!/usr/bin/env python3
import uvicorn

if __name__ == "__main__":
    print("Starting FastAPI app on http://127.0.0.1:8000")
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True) 