class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def error_body(code: str, message: str, details=None) -> dict:
    return {"data": None, "error": {"code": code, "message": message, "details": details}}
