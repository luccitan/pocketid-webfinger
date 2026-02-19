# Pocket ID Webfinger endpoint

[![Docker image](https://github.com/luccitan/pocketid-webfinger/actions/workflows/docker.yaml/badge.svg)](https://github.com/luccitan/pocketid-webfinger/actions/workflows/docker.yaml)

Minimalist server app powered by FastAPI that acts as a Webfinger endpoint for a Pocket ID provider endpoint.
This application has been written with Pocket ID as a target OIDC provider in mind and Tailscale as a Relying Party.

## Configuration

The setup of the server can be configured through different environment variables :

| Environment variable 	| Required 	| Default value 	| Description                                                                                                                                                 	|
|----------------------	|----------	|---------------	|-------------------------------------------------------------------------------------------------------------------------------------------------------------	|
| HOST                 	| False    	| 0.0.0.0       	| Host the application is bound to.  To be changed if you want to restrict at the application level the interface the webserver is bound to.                  	|
| PORT                 	| False    	| 8000          	| Port your application is listening to.                                                                                                                      	|
| OIDC_ENDPOINT        	| True     	|               	| URL of your Pocket ID endpoint.  It MUST be in the form of `https://my.endpoint.com`.  See the [dedicated section](#specification-compliance) for more info 	|


## Usage

### Setup the application

#### With `uv`

```shell
export OIDC_ENDPOINT='<https://<your_oidc_endpoint_domain>'

uv sync --locked
uv run python main.py
```

#### With `docker`

```shell
docker run -e OIDC_ENDPOINT="<https://<your_oidc_endpoint_domain>" -p 8000:8000 ghcr.io/luccitan/pocketid-webfinger:latest
```

### Enable the application (Traefik case)

Below you can find an example on how to setup the Webfinger application along with Pocket ID with Traefik in a `docker-compose.yaml` file.
Part of the implementation below is opiniated and can be adapted to your needs and wishes
(e.g. Docker Traefik labels, Traefik externally defined, volumes setup, ...)

```yaml
name: auth

networks:
  default:
    name: network-webfinger
  network-traefik:
    external: true

services:
  webfinger:
    container_name: pocketid-webfinger
    image: ghcr.io/luccitan/pocketid-webfinger:latest
    networks:
      - default
      - network-traefik
    environment:
      OIDC_ENDPOINT: auth.mydomain.com
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 1m
      timeout: 10s
      retries: 3
      start_period: 15s
    labels:
      traefik.enable: true
      traefik.http.services.webfinger.loadbalancer.server.port: 8000
      traefik.http.routers.webfinger.rule: Host(`mydomain.com`) && PathPrefix(`/.well-known/webfinger`)
      traefik.http.routers.webfinger.priority: 10
      traefik.http.routers.webfinger.entrypoints: websecure
      traefik.http.routers.webfinger.service: webfinger
```

## Specification compliance

The two important specifications involved in this application are the [OpenID Connect 1.0 (OIDC)](https://openid.net/specs/openid-connect-discovery-1_0.html)
and the [Webfinger](https://webfinger.net/) specifications.

It involves a lot of small specifications from the types of API responses but also input formalizations and constraints.

This application only considers a subset of the formal specifications linked above, to fulfill the regular needs for the Pocket ID / Tailscale usage described above :
- The OIDC endpoint MUST be accessible through HTTPS and the application targets the endpoint with the `https` scheme in the URI
- The OIDC endpoint URI is in the form of `https://optional-subdomain.domain.tld` with no suffixes.
- The `resource` argument is in the form of `acct:user@email.com`
- The `http://openid.net/specs/connect/1.0/issuer` minimum info in the Webfinger responses is returned in the `links`
- Some additional optional `links` are added.
