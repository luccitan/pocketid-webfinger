import os

import pytest
from httpx import Response
from fastapi import status
from fastapi.testclient import TestClient

from main import app, POCKETID_ENDPOINT_ENVVAR


class TestApplication:

    @pytest.mark.parametrize('route', [
        '/',
        '/.well-known',
        '/whatever'
    ])
    def test_unsupported_routes(self, route: str):
        client = TestClient(app)
        response: Response = client.get(route)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_badly_initialized(self, monkeypatch: pytest.MonkeyPatch):
        # Testing missing Pocket ID endpoint
        if os.environ.get(POCKETID_ENDPOINT_ENVVAR):
            monkeypatch.delenv(POCKETID_ENDPOINT_ENVVAR)
        with pytest.raises(RuntimeError, match='A valid HTTP endpoint must be defined'):
            TestClient(app).__enter__()

        # Testing invalid Pocket ID endpoint
        monkeypatch.setenv(POCKETID_ENDPOINT_ENVVAR, 'http://auth.example.com')
        with pytest.raises(RuntimeError, match='must be a valid HTTPS URI'):
            TestClient(app).__enter__()

    def test_missing_resource(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(POCKETID_ENDPOINT_ENVVAR, 'https://auth.example.com')
        with TestClient(app) as client:
            response: Response = client.get('/.well-known/webfinger', params=None)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_dict = response.json()

        assert set(response_dict.keys()) == {'status', 'error'}
        assert response_dict['status'] == status.HTTP_400_BAD_REQUEST
        assert set(response_dict['error'].keys()) == {'message', 'details'}
        assert response_dict['error']['message'] == 'The request is not a valid Webfinger request'
        assert response_dict['error']['details'] == 'The `resource` query parameter is missing'

    def test_invalid_resource(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(POCKETID_ENDPOINT_ENVVAR, 'https://auth.example.com')
        with TestClient(app) as client:
            response: Response = client.get('/.well-known/webfinger', params={'resource': 'foo@example.com'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_dict = response.json()

        assert set(response_dict.keys()) == {'status', 'error'}
        assert response_dict['status'] == status.HTTP_400_BAD_REQUEST
        assert set(response_dict['error'].keys()) == {'message', 'details'}
        assert response_dict['error']['message'] == 'The request is not a valid Webfinger request'
        assert response_dict['error']['details'] == 'The `resource` query parameter must be follow the "acct" URI scheme (cf. RFC 7565)'

    def test_valid_request(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(POCKETID_ENDPOINT_ENVVAR, 'https://auth.example.com')
        with TestClient(app) as client:
            response: Response = client.get('/.well-known/webfinger', params={'resource': 'acct:foo@example.com'})
        assert response.status_code == status.HTTP_200_OK
        response_dict = response.json()

        assert response_dict == {
            'subject': 'acct:foo@example.com',
            'links': [
                {'rel': 'http://openid.net/specs/connect/1.0/issuer', 'href': 'https://auth.example.com'},
                {'rel': 'authorization_endpoint', 'href': 'https://auth.example.com/authorize'},
                {'rel': 'token_endpoint', 'href': 'https://auth.example.com/api/oidc/token'},
                {'rel': 'userinfo_endpoint', 'href': 'https://auth.example.com/api/oidc/userinfo'},
                {'rel': 'jwks_uri', 'href': 'https://auth.example.com/.well-known/jwks.json'},
            ]
        }