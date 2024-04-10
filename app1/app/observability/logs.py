"""Logger module."""

from __future__ import annotations

import json
import multiprocessing
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from functools import singledispatchmethod
from itertools import chain
from pathlib import Path
from typing import TypedDict

import loguru
from loguru import logger

from commons.environments import envs


class Message(TypedDict):
    """Log message."""

    text: str
    record: loguru.Record


@dataclass
class DBLoggerHandler:
    """Database logger handler."""

    db_index: str = field(default=envs('LOG_DB_INDEX', 'logs_commons'))
    db_host: str = field(default=envs('LOG_DB_HOST'))
    db_port: str = field(default=envs('LOG_DB_PORT'))
    db_user: str = field(default=envs('LOG_DB_USER', 'admin'), repr=False)
    db_pass: str = field(default=envs('LOG_DB_PASS', 'admin'), repr=False)

    max_workers: int = field(
        default=envs('LOG_DB_WORKERS', default=multiprocessing.cpu_count()),
        repr=False,
    )

    @property
    def mapping(self) -> dict:
        """Create mapping."""
        mapping = Path(__file__).parent / '.resources/logs_mappings.json'
        with mapping.open() as file:
            return json.load(file)

    def create_index(self):
        """Create index if not exists."""
        if not self.client.indices.exists(self.db_index):
            self.client.indices.create(self.db_index, self.mapping)

    @property
    def client(self):  # noqa: ANN201
        """Client db."""
        from opensearchpy import OpenSearch

        return OpenSearch(
            f'{self.db_host}:{self.db_port}',
            http_auth=(self.db_user, self.db_pass),
        )

    def _write(self, record: loguru.Record):
        self.create_index()
        self.client.index(index=self.db_index, body=record)

    def write(self, data: str):
        """Write data logger in database.

        Parameters
        ----------
        data:
            Logger data

        """
        msg: Message = json.loads(data)

        record = msg['record']
        record['text'] = msg['text']
        record['extra'] = record['extra'].get('extra', {})

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            executor.submit(self._write, record)


LOG_LEVEL = envs('LOGURU_LEVEL') or envs('LOG_LEVEL', default='TRACE')
LOG_FORMAT = envs('LOGURU_FORMAT') or envs(
    'LOG_FORMAT',
    default=(
        '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | '
        '<level>{level: <8}</level> | '
        '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - '
        '<level>{message}</level>'
    ),
)


class Encoder(json.JSONEncoder):
    """Encode json."""

    def default(self, o) -> str:  # noqa: ANN001
        """Serializable object."""
        return self.serializer(o)

    @singledispatchmethod
    def serializer(self, value: datetime) -> str:
        """Serialize."""
        return str(value)


def _format(record: loguru.Record) -> str:
    def escape(value: dict) -> str:
        return re.sub(r'\}|\<', ']', re.sub(r'\{|\>', '[', value))

    extra = record['extra'].pop('extra', {})

    line = '<fg #5c4bec>{key}</fg #5c4bec>={value}'
    extras = ' '.join(
        line.format(key=key, value=escape(json.dumps(val, cls=Encoder)))
        for key, val in chain(record['extra'].items(), extra.items())
    )
    if extra:
        record['extra']['extra'] = extra
    return f'{LOG_FORMAT} :: <b>{extras}</b>\n'


handlers = [
    {
        'sink': sys.stderr,
        'level': LOG_LEVEL,
        'colorize': True,
        'format': _format,
    },
]
if all([envs('LOG_DB_HOST'), envs('LOG_DB_PORT')]):
    handlers.append(
        {
            'sink': DBLoggerHandler(),
            'level': LOG_LEVEL,
            'colorize': False,
            'serialize': True,
            'format': _format,
        },
    )

logger.remove()
logger.configure(
    handlers=handlers,
    levels=[
        {
            'name': 'PERFORMANCE',
            'no': 60,
            'color': '<yellow>',
            'icon': '\u2139\uFE0F',
        },
    ],
)

logger.perf = lambda message, *args, **kwargs: logger._log(  # noqa: SLF001
    'PERFORMANCE',
    False,
    logger._options,  # noqa: SLF001
    message,
    args,
    kwargs,
)
