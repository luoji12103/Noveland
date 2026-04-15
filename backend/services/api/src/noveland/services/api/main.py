import uvicorn


def main() -> None:
    uvicorn.run("noveland.services.api.app:app", host="0.0.0.0", port=8000)
