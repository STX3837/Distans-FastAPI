from starlette.responses import JSONResponse, RedirectResponse


RUTAS_PUBLICAS = {
    "/",
    "/login",
    "/registro",
    "/invitado",
    "/recuperar-contrasena",
    "/restablecer-contrasena",
    "/api/login",
    "/api/registro",
    "/api/recuperar-contrasena",
    "/api/restablecer-contrasena",
    # Stripe autentica esta llamada mediante su firma, no mediante la sesión web.
    "/api/stripe/webhook",
}


class RequerirAccesoMiddleware:
    """Impide usar la aplicación hasta elegir invitado o iniciar sesión."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET").upper()
        session = scope.get("session", {})
        tiene_acceso = bool(session.get("usuario") or session.get("es_invitado"))
        es_publica = path in RUTAS_PUBLICAS or path.startswith("/static/") or method == "OPTIONS"

        if tiene_acceso or es_publica:
            await self.app(scope, receive, send)
            return

        if path.startswith("/api/") or method not in {"GET", "HEAD"}:
            response = JSONResponse({"detail": "Debes iniciar sesión o entrar como invitado"}, status_code=401)
        else:
            response = RedirectResponse("/login", status_code=303)
        await response(scope, receive, send)
