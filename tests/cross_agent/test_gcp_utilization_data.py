import json
import os
import pytest

from newrelic.common.utilization import GCPUtilization
from testing_support.mock_http_client import MockHttpClient
from testing_support.fixtures import validate_internal_metrics


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures',
    'utilization_vendor_specific', 'gcp.json'))

_parameters_list = ['testname', 'uri', 'expected_vendors_hash',
        'expected_metrics']

_parameters = ','.join(_parameters_list)


def _load_tests():
    with open(FIXTURE, 'r') as fh:
        js = fh.read()
    return json.loads(js)


def _parametrize_test(test):
    return tuple([test.get(f, None) for f in _parameters_list])


_gcp_tests = [_parametrize_test(t) for t in _load_tests()]


@pytest.fixture(autouse=True)
def reset_http_client():
    yield
    MockHttpClient.FAIL = False
    MockHttpClient.STATUS = 200
    MockHttpClient.DATA = None
    MockHttpClient.EXPECTED_URL = None


@pytest.mark.parametrize(_parameters, _gcp_tests)
def test_gcp(monkeypatch, testname, uri,
             expected_vendors_hash, expected_metrics):

    # Generate mock responses for HttpClient

    def _get_mock_return_value(api_result):
        if api_result['timeout']:
            return 0, None
        else:
            body = json.dumps(api_result['response'])
            return 200, body.encode('utf-8')

    MockHttpClient.EXPECTED_URL = list(uri.keys())[0]
    status, data = (
            _get_mock_return_value(uri[MockHttpClient.EXPECTED_URL]))

    monkeypatch.setattr(GCPUtilization, "CLIENT_CLS", MockHttpClient)
    MockHttpClient.STATUS = status
    MockHttpClient.DATA = data

    metrics = []
    if expected_metrics:
        metrics = [(k, v.get('call_count')) for k, v in
                expected_metrics.items()]

    # Define function that actually runs the test

    @validate_internal_metrics(metrics=metrics)
    def _test_gcp_data():

        data = GCPUtilization.detect()

        if data:
            gcp_vendor_hash = {'gcp': data}
        else:
            gcp_vendor_hash = None

        assert gcp_vendor_hash == expected_vendors_hash

    _test_gcp_data()

    assert not MockHttpClient.FAIL
