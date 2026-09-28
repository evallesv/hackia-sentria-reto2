import base64
import binascii
import secrets

from fastapi.responses import JSONResponse
from starlette.datastructures import Headers


class DemoAccess:
    """Control de acceso compartido para la evaluación, incluidos archivos y API."""

    def __init__(self, app, username: str, password: str):
        if not password:
            raise ValueError("DEMO_PASSWORD es obligatorio cuando DEMO_AUTH_ENABLED=true")
        self.app = app
        self.username = username.encode("utf-8")
        self.password = password.encode("utf-8")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or (scope["path"] == "/healthz" and scope["method"] == "GET"):
            return await self.app(scope, receive, send)

        authorization = Headers(scope=scope).get("authorization", "")
        scheme, _, credentials = authorization.partition(" ")
        valid = False
        if scheme.lower() == "basic":
            try:
                decoded = base64.b64decode(credentials, validate=True)
                username, separator, password = decoded.partition(b":")
                username_matches = secrets.compare_digest(username, self.username)
                password_matches = secrets.compare_digest(password, self.password)
                valid = bool(separator) and username_matches and password_matches
            except (ValueError, binascii.Error):
                pass

        if not valid:
            return await JSONResponse(
                {"detail": "Introduce las credenciales de evaluación indicadas en el README."},
                status_code=401,
                headers={
                    "WWW-Authenticate": 'Basic realm="Sentria", charset="UTF-8"',
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )(scope, receive, send)
        await self.app(scope, receive, send)
