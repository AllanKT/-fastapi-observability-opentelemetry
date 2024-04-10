from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from app.observability.logs import MyClass
from app.observability.metrics import MetricsMeddleware as metrics


logger = MyClass().logger

class Instrumentation():

    def instrument(self, app, engine = None):
        FastAPIInstrumentor.instrument_app(app, excluded_urls="redocs,docs,healthcheck")
        RequestsInstrumentor().instrument()
        LoggingInstrumentor().instrument()
        if engine:
            SQLAlchemyInstrumentor().instrument(engine=engine)
