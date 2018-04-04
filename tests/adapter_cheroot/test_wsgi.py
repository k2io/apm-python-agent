import socket

import cheroot.wsgi
import newrelic.api.transaction
from testing_support.fixtures import validate_transaction_metrics


def get_open_port():
    # This function came from:
    # https://stackoverflow.com/questions/2838244/get-open-tcp-port-in-python
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wsgi_test_app(environ, start_response):
    newrelic.api.transaction.set_transaction_name('wsgi_test_transaction')
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return [b'Hello world!']


def start_response(status, response_headers, exc_info=None):
    """Empty callable"""
    pass


_test_scoped_metrics = [
    ('Python/WSGI/Finalize', 1),
    ('Python/WSGI/Application', 1),
    ('Function/test_wsgi:wsgi_test_app', 1),
]


@validate_transaction_metrics('wsgi_test_transaction',
        scoped_metrics=_test_scoped_metrics)
def test_wsgi_test_function_transaction_metrics_positional_args():
    server = cheroot.wsgi.Server(('0.0.0.0', get_open_port()), wsgi_test_app)
    environ = {'REQUEST_URI': '/'}
    resp = server.wsgi_app(environ, start_response)

    if hasattr(resp, 'close'):
        resp.close()


@validate_transaction_metrics('wsgi_test_transaction',
        scoped_metrics=_test_scoped_metrics)
def test_wsgi_test_function_transaction_metrics_keyword_args():
    server = cheroot.wsgi.Server(bind_addr=('0.0.0.0', get_open_port()),
                                 wsgi_app=wsgi_test_app)
    environ = {'REQUEST_URI': '/'}
    resp = server.wsgi_app(environ, start_response)

    if hasattr(resp, 'close'):
        resp.close()
