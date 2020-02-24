import pytest
try:
    import http.client as httplib
except ImportError:
    import httplib

from testing_support.fixtures import (validate_transaction_metrics,
        override_application_settings, validate_tt_segment_params)
from testing_support.validators.validate_span_events import (
        validate_span_events)
from testing_support.external_fixtures import (cache_outgoing_headers,
    validate_cross_process_headers, insert_incoming_headers,
    validate_external_node_params)
from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)

from newrelic.common.encoding_utils import DistributedTracePayload
from newrelic.api.background_task import background_task
from newrelic.packages import six


def select_python_version(py2, py3):
    return six.PY3 and py3 or py2


@pytest.fixture(scope='module', autouse=True)
def mock_server():
    with MockExternalHTTPHResponseHeadersServer() as server:
        yield server


_test_httplib_http_request_scoped_metrics = [select_python_version(
        py2=('External/localhost:8989/httplib/', 1),
        py3=('External/localhost:8989/http/', 1))]


_test_httplib_http_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/localhost:8989/all', 1),
        select_python_version(py2=('External/localhost:8989/httplib/', 1),
                              py3=('External/localhost:8989/http/', 1))]


@validate_transaction_metrics(
        'test_httplib:test_httplib_http_request',
        scoped_metrics=_test_httplib_http_request_scoped_metrics,
        rollup_metrics=_test_httplib_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib_http_request():
    connection = httplib.HTTPConnection('localhost', 8989)
    connection.request('GET', '/')
    response = connection.getresponse()
    response.read()
    connection.close()


_test_httplib_https_request_scoped_metrics = [select_python_version(
        py2=('External/www.example.com/httplib/', 1),
        py3=('External/www.example.com/http/', 1))]


_test_httplib_https_request_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/www.example.com/all', 1),
        select_python_version(py2=('External/www.example.com/httplib/', 1),
                              py3=('External/www.example.com/http/', 1))]


@validate_transaction_metrics(
        'test_httplib:test_httplib_https_request',
        scoped_metrics=_test_httplib_https_request_scoped_metrics,
        rollup_metrics=_test_httplib_https_request_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib_https_request():
    connection = httplib.HTTPSConnection('www.example.com', 443)
    connection.request('GET', '/')
    response = connection.getresponse()
    response.read()
    connection.close()


_test_httplib_http_request_with_port_scoped_metrics = [select_python_version(
        py2=('External/localhost:8989/httplib/', 1),
        py3=('External/localhost:8989/http/', 1))]


_test_httplib_http_request_with_port_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/localhost:8989/all', 1),
        select_python_version(py2=('External/localhost:8989/httplib/', 1),
                              py3=('External/localhost:8989/http/', 1))]


@validate_transaction_metrics(
        'test_httplib:test_httplib_http_with_port_request',
        scoped_metrics=_test_httplib_http_request_with_port_scoped_metrics,
        rollup_metrics=_test_httplib_http_request_with_port_rollup_metrics,
        background_task=True)
@background_task()
def test_httplib_http_with_port_request():
    connection = httplib.HTTPConnection('localhost', 8989)
    connection.request('GET', '/')
    response = connection.getresponse()
    response.read()
    connection.close()


@pytest.mark.parametrize('distributed_tracing,span_events', (
    (True, True),
    (True, False),
    (False, False),
))
def test_httplib_cross_process_request(distributed_tracing, span_events):
    @background_task(name='test_httplib:test_httplib_cross_process_request')
    @cache_outgoing_headers
    @validate_cross_process_headers
    def _test():
        connection = httplib.HTTPConnection('localhost', 8989)
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()
        connection.close()

    _test = override_application_settings({
        'distributed_tracing.enabled': distributed_tracing,
        'span_events.enabled': span_events,
    })(_test)

    _test()


_test_httplib_cross_process_response_scoped_metrics = [
        ('ExternalTransaction/localhost:8989/1#2/test', 1)]


_test_httplib_cross_process_response_rollup_metrics = [
        ('External/all', 1),
        ('External/allOther', 1),
        ('External/localhost:8989/all', 1),
        ('ExternalApp/localhost:8989/1#2/all', 1),
        ('ExternalTransaction/localhost:8989/1#2/test', 1)]


_test_httplib_cross_process_response_external_node_params = [
        ('cross_process_id', '1#2'),
        ('external_txn_name', 'test'),
        ('transaction_guid', '0123456789012345')]


@validate_transaction_metrics(
        'test_httplib:test_httplib_cross_process_response',
        scoped_metrics=_test_httplib_cross_process_response_scoped_metrics,
        rollup_metrics=_test_httplib_cross_process_response_rollup_metrics,
        background_task=True)
@insert_incoming_headers
@validate_external_node_params(
        params=_test_httplib_cross_process_response_external_node_params)
@background_task()
def test_httplib_cross_process_response():
    connection = httplib.HTTPConnection('localhost', 8989)
    connection.request('GET', '/')
    response = connection.getresponse()
    response.read()
    connection.close()


def test_httplib_multiple_requests_cross_process_response():
    connection = httplib.HTTPConnection('localhost', 8989)

    @validate_transaction_metrics(
            'test_httplib:test_transaction',
            scoped_metrics=_test_httplib_cross_process_response_scoped_metrics,
            rollup_metrics=_test_httplib_cross_process_response_rollup_metrics,
            background_task=True)
    @insert_incoming_headers
    @validate_external_node_params(
            params=_test_httplib_cross_process_response_external_node_params)
    @background_task(name='test_httplib:test_transaction')
    def test_transaction():
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()

    # make multiple requests with the same connection
    for _ in range(2):
        test_transaction()

    connection.close()


def process_response(response):
    response = response.decode('utf-8').strip()
    values = response.splitlines()
    values = [[x.strip() for x in s.split(':', 1)] for s in values]
    return {v[0]: v[1] for v in values}


def test_httplib_multiple_requests_unique_distributed_tracing_id():
    connection = httplib.HTTPConnection('localhost', 8989)
    response_headers = []

    @background_task(name='test_httplib:test_transaction')
    def test_transaction():
        connection.request('GET', '/')
        response = connection.getresponse()
        response_headers.append(process_response(response.read()))
        connection.request('GET', '/')
        response = connection.getresponse()
        response_headers.append(process_response(response.read()))

    test_transaction = override_application_settings({
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    })(test_transaction)
    # make multiple requests with the same connection
    test_transaction()

    connection.close()
    dt_payloads = [DistributedTracePayload.from_http_safe(header['newrelic'])
        for header in response_headers]

    ids = set()
    for payload in dt_payloads:
        assert payload['d']['id'] not in ids
        ids.add(payload['d']['id'])


def test_httplib_nr_headers_added():
    connection = httplib.HTTPConnection('localhost', 8989)
    key = 'newrelic'
    value = 'gobbledygook'
    headers = []

    @background_task(name='test_httplib:test_transaction')
    def test_transaction():
        connection.putrequest('GET', '/')
        connection.putheader(key, value)
        connection.endheaders()
        response = connection.getresponse()
        headers.append(process_response(response.read()))

    test_transaction = override_application_settings({
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    })(test_transaction)
    test_transaction()
    connection.close()
    # verify newrelic headers already added do not get overrode
    assert headers[0][key] == value


def test_span_events():
    connection = httplib.HTTPConnection('localhost', 8989)

    _settings = {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    }

    uri = 'http://localhost:8989'

    exact_intrinsics = {
        'name': select_python_version(
                py2='External/localhost:8989/httplib/',
                py3='External/localhost:8989/http/'),
        'type': 'Span',
        'sampled': True,

        'category': 'http',
        'span.kind': 'client',
        'component': select_python_version(py2='httplib', py3='http')
    }
    exact_agents = {
        'http.url': uri,
        'http.statusCode': 200,
    }

    expected_intrinsics = ('timestamp', 'duration', 'transactionId')

    @override_application_settings(_settings)
    @validate_span_events(
            count=1,
            exact_intrinsics=exact_intrinsics,
            exact_agents=exact_agents,
            expected_intrinsics=expected_intrinsics)
    @validate_tt_segment_params(exact_params=exact_agents)
    @background_task(name='test_httplib:test_span_events')
    def _test():
        connection.request('GET', '/')
        response = connection.getresponse()
        response.read()

    _test()
