import logging
import sys
from tg.request_local import Response

log = logging.getLogger(__name__)


class ErrorPageApplicationWrapper(object):
    """Given an Application it intercepts the response code and shows a custom page"""

    def __init__(self, handler, config):
        self.handle_error_enabled = config.get('errorpage.enabled', False)
        self.handle_status_codes = set(config.get('errorpage.status_codes', tuple()))
        self.handle_exceptions = config.get('errorpage.handle_exceptions',
                                            not config.get('debug', False))
        self.handle_error_path = config.get('errorpage.path', '/error/document')

        self._handler = handler

        if self.handle_exceptions and 500 not in self.handle_status_codes:
            self.handle_status_codes.add(500)

        log.debug('ErrorPageApplicationWrapper enabled: %s -> %s',
                  self.handle_error_enabled, self.handle_status_codes)

    def __call__(self, controller, environ, context):
        if self.handle_error_enabled is False:
            return self._handler(controller, environ, context)

        try:
            resp = self._handler(controller, environ, context)
        except:
            if self.handle_exceptions is False:
                raise
            # Provide crash details to backlash
            environ['backlash.exc_environ'] = environ.copy()
            environ['backlash.exc_info'] = sys.exc_info()
            # Force response to a 500 Error, otherwise it will be a 200
            resp = context.response
            resp.status_code = 500

        status_code = resp.status_code
        log.debug('ErrorPageApplicationWrapper response: %s -> %s',
                  environ['PATH_INFO'], status_code)
        if status_code in self.handle_status_codes:
            environ['tg.original_request'] = context.request.copy()
            environ['tg.original_response'] = Response(status=resp.status,
                                                       headerlist=resp.headerlist[:],
                                                       app_iter=resp.app_iter)

            environ['PATH_INFO'] = self.handle_error_path
            log.debug('ErrorPageApplicationWrapper serving %s:%s',
                      controller, self.handle_error_path)
            resp = self._handler(controller, environ, context)

        return resp