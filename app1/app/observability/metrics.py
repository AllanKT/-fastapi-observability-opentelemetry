# import logging
import json
from os import environ
from time import time
import base64

from opentelemetry.metrics import get_meter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.routing import Match

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
meter = get_meter('spam.meter')

req_count = meter.create_counter(
    name='mantis_request_counter',
    description='Quantidade total de requests',
)

err_count = meter.create_counter(
    name='mantis_error_counter',
    description='Quantidade total de erros',
)

active_count = meter.create_up_down_counter(
    name='mantis_active_requests',
    description='Quantidade de requests ativos.',
)

total_time = meter.create_histogram(
    name='mantis_total_request_time', description='time to response a request.'
)

user_created_count = meter.create_counter(
    name='mantis_user_created_count',
    description='Quantidade total usuários criados',
)


class MetricsMeddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app=app)
        self.app_name = environ.get('OTEL_SERVICE_NAME')

    def get_path(self, request: Request):
        for route in request.app.routes:
            match_, _ = route.matches(request.scope)
            if match_ == Match.FULL:
                return route.path

        return request.url.path

    def get_auth_details(self, request: Request):
        header = request.headers
        data = json.loads(base64.b64decode(header.get('Authentication')))
        print(data)

    async def dispatch(self, request: Request, call_next):
        self.get_auth_details(request)
        base_attributes = {
            'method': request.method,
            'path': self.get_path(request),
            'host': request.client.host,
        }

        active_count.add(1, attributes=base_attributes)
        start_time = time()

        try:
            response = await call_next(request)
            attributes = base_attributes | {
                'status_code': response.status_code,
            }
            req_count.add(1, attributes=attributes)
        except Exception as e:
            attributes = base_attributes | {
                'exception_type': type(e).__name__,
                'status_code': 500,
            }
            req_count.add(1, attributes=attributes)
            err_count.add(1)
            # logger.error('Deu ruim!')
            raise e from None
        finally:
            active_count.add(-1, attributes=base_attributes)
            total_time.record(time() - start_time, attributes=base_attributes)

        return response
