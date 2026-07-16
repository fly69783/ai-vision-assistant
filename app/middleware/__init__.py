"""应用中间件。"""

from app.middleware.response_policy import ResponsePolicyMiddleware

__all__ = ["ResponsePolicyMiddleware"]
