from .audit import audit_action

AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method in AUDITED_METHODS
            and response.status_code < 400
            and not getattr(request, "_audit_logged", False)
        ):
            audit_action(
                request,
                f"{request.method} {request.path}",
                "HTTP",
                request.path,
                {"status": response.status_code},
            )
        return response
