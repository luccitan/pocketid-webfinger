import os
import re
import logging
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Query, Request, status
from fastapi.responses import JSONResponse


logger = logging.getLogger('pocketid-webfinger')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
logger.addHandler(handler)

POCKETID_ENDPOINT_ENVVAR='OIDC_ENDPOINT'

# both regexes below loosely defined but should be enough for 99.99% of use-cases and contexts
RE_POCKETID_HTTPS_ENDPOINT = re.compile(r'https:\/\/[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}')
RE_ACCT_URI_SCHEME = re.compile(r'acct:(?P<user>[^@]+)@(?P<host>[^@]+)$')

@asynccontextmanager
async def lifespan(app: FastAPI):
    pocketid_domain = os.environ.get(POCKETID_ENDPOINT_ENVVAR)

    if not pocketid_domain:
        logging.error('Missing HTTP endpoint env. variable at application initialization')
        raise RuntimeError(f"A valid HTTP endpoint must be defined in {POCKETID_ENDPOINT_ENVVAR} env. variable to target the OIDC endpoint")

    if not RE_POCKETID_HTTPS_ENDPOINT.match(pocketid_domain):
        logging.error('Invalid HTTP endpoint env. variable found at application initialization')
        raise RuntimeError(f"The OIDC endpoint provided in {POCKETID_ENDPOINT_ENVVAR} env. variable must be a valid HTTPS URI")

    pocketid_domain = pocketid_domain.rstrip('/')
    app.state.pocketid_domain = pocketid_domain

    yield

app = FastAPI(lifespan=lifespan)

@app.get('/.well-known/webfinger')
def entrypoint(
    request: Request,
    resource: Annotated[str | None, Query()] = None,
) -> JSONResponse:
    pocketid_domain = request.app.state.pocketid_domain

    if resource is None:
        return JSONResponse(
            content={
                'status': status.HTTP_400_BAD_REQUEST,
                'error': {
                    'message': 'The request is not a valid Webfinger request',
                    'details': 'The `resource` query parameter is missing'
                }
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not RE_ACCT_URI_SCHEME.match(resource):
        return JSONResponse(
            content={
                'status': status.HTTP_400_BAD_REQUEST,
                'error': {
                    'message': 'The request is not a valid Webfinger request',
                    'details': 'The `resource` query parameter must be follow the "acct" URI scheme (cf. RFC 7565)'
                }
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return JSONResponse({'subject': resource, 'links': [
        {'rel': 'http://openid.net/specs/connect/1.0/issuer', 'href': pocketid_domain},
        {'rel': 'authorization_endpoint', 'href': pocketid_domain + '/authorize'},
        {'rel': 'token_endpoint', 'href': pocketid_domain + '/api/oidc/token'},
        {'rel': 'userinfo_endpoint', 'href': pocketid_domain + '/api/oidc/userinfo'},
        {'rel': 'jwks_uri', 'href': pocketid_domain + '/.well-known/jwks.json'},
    ]}, status_code=status.HTTP_200_OK)

@app.get('/health')
def healthcheck() -> int:
    return status.HTTP_200_OK

if __name__ == "__main__":
    host = os.environ.get('HOST', '0.0.0.0')
    port = os.environ.get('PORT', '8000')

    uvicorn.run(app, host=host, port=port)