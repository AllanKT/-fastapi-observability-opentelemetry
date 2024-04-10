"""Logger module."""

import os
import json
import logging.config
import getpass
import threading
import logging


class NewLogger(logging.Logger):
    # override the makeRecord method
    def makeRecord(self, *args, **kwargs):
        rv = super(NewLogger, self).makeRecord(*args, **kwargs)
        req = rv.__dict__.get("request", {})
        rv.__dict__["request"] = {
            "host": req.headers.get('host')
        }
        print('====================')
        print(req.headers)
        if req:
            rv.__dict__ = {
                **rv.__dict__,
                **{
                    "host": req.headers.get('host')
                }
            }

        # rv.__dict__["City"] = rv.__dict__.get("City", "Khazad-dum")
        return rv


class MyClass(object):
    def __init__(self):
        self.log = NewLogger("foobar")
        self.log.propagate = False

        log_ = logging.getLogger(".".join([__name__, self.__class__.__name__]))
        log_.setLevel(logging.DEBUG)

        self.log.addHandler(log_)

    @property
    def logger(self):
        return self.log
