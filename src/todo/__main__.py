import uvicorn
from todo.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "todo.app:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True
    )
