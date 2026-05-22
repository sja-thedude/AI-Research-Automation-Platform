"""Request-scoped middleware: attach a correlation ID for tracing."""
import uuid

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware:
    """Ensure every request/response carries a correlation ID.

    Honors an inbound X-Request-ID (from a gateway/load balancer) or mints one.
    Useful for tracing a request across Django -> Celery -> AI provider calls.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.request_id = request_id
        response = self.get_response(request)
        response[REQUEST_ID_HEADER] = request_id
        return response
