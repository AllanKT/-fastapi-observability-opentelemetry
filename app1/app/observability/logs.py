"""Logger module."""

import json
from time import time_ns
import traceback
from typing import Optional, Any

from opentelemetry.sdk.util import ns_to_iso_str
from opentelemetry.util.types import Attributes
import logging.config
import logging
from opentelemetry._logs import LogRecord as APILogRecord, SeverityNumber, NoOpLogger, get_logger, get_logger_provider, std_to_otel
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import (
    format_span_id,
    format_trace_id,
    get_current_span
)
from opentelemetry.trace.span import TraceFlags
from opentelemetry.sdk.resources import Resource
from opentelemetry.attributes import BoundedAttributes


class LogRecord(APILogRecord):
    """A LogRecord instance represents an event being logged.

    LogRecord instances are created and emitted via `Logger`
    every time something is logged. They contain all the information
    pertinent to the event being logged.
    """

    def __init__(
        self,
        timestamp: Optional[int] = None,
        observed_timestamp: Optional[int] = None,
        trace_id: Optional[int] = None,
        span_id: Optional[int] = None,
        trace_flags: Optional[TraceFlags] = None,
        severity_text: Optional[str] = None,
        severity_number: Optional[SeverityNumber] = None,
        body: Optional[Any] = None,
        resource: Optional[Resource] = None,
        attributes: Optional[Attributes] = None,
        # limits: Optional[LogLimits] = _UnsetLogLimits,
    ):
        super().__init__(
            **{
                "timestamp": timestamp,
                "observed_timestamp": observed_timestamp,
                "trace_id": trace_id,
                "span_id": span_id,
                "trace_flags": trace_flags,
                "severity_text": severity_text,
                "severity_number": severity_number,
                "body": body,
                "attributes": BoundedAttributes(
                    # maxlen=limits.max_attributes,
                    attributes=attributes if bool(attributes) else None,
                    immutable=False,
                    # max_value_len=limits.max_attribute_length,
                ),
            }
        )
        self.resource = resource

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LogRecord):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def to_json(self, indent=4) -> str:
        return json.dumps(
                {
                    "body": self.body,
                    "severity_number": repr(self.severity_number),
                    "severity_text": self.severity_text,
                    "attributes": dict(self.attributes)
                    if bool(self.attributes)
                    else None,
                    "dropped_attributes": self.dropped_attributes,
                    "timestamp": ns_to_iso_str(self.timestamp),
                    "observed_timestamp": ns_to_iso_str(self.observed_timestamp),
                    "trace_id": f"0x{format_trace_id(self.trace_id)}"
                    if self.trace_id is not None
                    else "",
                    "span_id": f"0x{format_span_id(self.span_id)}"
                    if self.span_id is not None
                    else "",
                    "trace_flags": self.trace_flags,
                    "resource": repr(self.resource.attributes)
                    if self.resource
                    else "",
                },
                indent=indent,
        )

    @property
    def dropped_attributes(self) -> int:
        if self.attributes:
            return self.attributes.dropped
        return 0


_RESERVED_ATTRS = frozenset(
    (
        "asctime",
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "message",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    )
)

class LoggingHandler(logging.Handler):
    """A handler class which writes logging records, in OTLP format, to
    a network destination or file. Supports signals from the `logging` module.
    https://docs.python.org/3/library/logging.html
    """

    def __init__(
        self,
        level=logging.NOTSET,
        logger_provider=None,
    ) -> None:
        super().__init__(level=level)
        self._logger_provider = logger_provider or get_logger_provider()
        self._logger = get_logger(
            __name__, logger_provider=self._logger_provider
        )

    @staticmethod
    def _get_attributes(record: logging.LogRecord) -> Attributes:
        attributes = {
            k: v for k, v in vars(record).items() if k not in _RESERVED_ATTRS
        }
        print(attributes)
        req = attributes.pop('request', {})
        print(req)
        print(req.headers.get('teste'))
        print(req.headers.get('teste2'))
        if req:
            print('================')
            attributes['teste'] = req.headers.get('teste')
            attributes['teste2'] = req.headers.get('teste2')
        print(attributes)

        # Add standard code attributes for logs.
        attributes[SpanAttributes.CODE_FILEPATH] = record.pathname
        attributes[SpanAttributes.CODE_FUNCTION] = record.funcName
        attributes[SpanAttributes.CODE_LINENO] = record.lineno

        if record.exc_info:
            exctype, value, tb = record.exc_info
            if exctype is not None:
                attributes[SpanAttributes.EXCEPTION_TYPE] = exctype.__name__
            if value is not None and value.args:
                attributes[SpanAttributes.EXCEPTION_MESSAGE] = value.args[0]
            if tb is not None:
                # https://github.com/open-telemetry/opentelemetry-specification/blob/9fa7c656b26647b27e485a6af7e38dc716eba98a/specification/trace/semantic_conventions/exceptions.md#stacktrace-representation
                attributes[SpanAttributes.EXCEPTION_STACKTRACE] = "".join(
                    traceback.format_exception(*record.exc_info)
                )
        return attributes

    def _translate(self, record: logging.LogRecord) -> LogRecord:
        timestamp = int(record.created * 1e9)
        observered_timestamp = time_ns()
        span_context = get_current_span().get_span_context()
        attributes = self._get_attributes(record)

        severity_number = std_to_otel(record.levelno)
        if isinstance(record.msg, str) and record.args:
            body = record.msg % record.args
        else:
            body = record.msg

        level_name = (
            "WARN" if record.levelname == "WARNING" else record.levelname
        )

        return LogRecord(
            timestamp=timestamp,
            observed_timestamp=observered_timestamp,
            trace_id=span_context.trace_id,
            span_id=span_context.span_id,
            trace_flags=span_context.trace_flags,
            severity_text=level_name,
            severity_number=severity_number,
            body=body,
            resource=self._logger.resource,
            attributes=attributes,
        )

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a record. Skip emitting if logger is NoOp.

        The record is translated to OTel format, and then sent across the pipeline.
        """
        if not isinstance(self._logger, NoOpLogger):
            self._logger.emit(self._translate(record))

    # def flush(self) -> None:
    #     """
    #     Flushes the logging output. Skip flushing if logger is NoOp.
    #     """
    #     if not isinstance(self._logger, NoOpLogger):
    #         self._logger_provider.force_flush()


class MyClass(object):
    def __init__(self):
        self.log = logging.getLogger(".".join([__name__, self.__class__.__name__]))
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(LoggingHandler())

    @property
    def logger(self):
        return self.log
