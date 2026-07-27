from typing import AsyncIterator
from fastapi.responses import StreamingResponse

async def stream_response(
    stream_iter: AsyncIterator[str],
) -> StreamingResponse:
    """Envuelve un iterador SSE en una StreamingResponse."""
    return StreamingResponse(
        stream_iter,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )