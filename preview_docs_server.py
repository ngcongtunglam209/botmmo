from app.core.runtime_loader import load_modules


modules = load_modules(force_reload=True)
app = modules["app.models.api_models"].app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="warning")
