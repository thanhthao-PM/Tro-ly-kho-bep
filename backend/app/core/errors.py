from fastapi import HTTPException


class ApiError(HTTPException):
    """Uniform error body: {"detail": {"code": ..., "message": ...}}."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(status_code=status, detail={"code": code, "message": message})
