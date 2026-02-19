# Pocket ID Webfinger proxy

Minimalist server app powered by FastAPI that acts as a Webfinger endpoint for a Pocket ID provider endpoint.
This proxy application has been written with Pocket ID as a target OIDC provider in mind and Tailscale as a Relying Party.

## Configuration

The setup of the server can be configured through different environment variables :

| Environment variable 	| Required 	| Default value 	| Description                                                                                                                                                 	|
|----------------------	|----------	|---------------	|-------------------------------------------------------------------------------------------------------------------------------------------------------------	|
| HOST                 	| False    	| 0.0.0.0       	| Host the application is bound to.  To be changed if you want to restrict at the application level the interface the webserver is bound to.                  	|
| PORT                 	| False    	| 8000          	| Port your application is listening to.                                                                                                                      	|
| OIDC_ENDPOINT        	| True     	|               	| URL of your Pocket ID endpoint.  It MUST be in the form of `https://my.endpoint.com`.  See the [dedicated section](#specification-compliance) for more info 	|


## Usage

### Setup the application

To enable
<details open>
    <summary>With uv</summary>

    ```shell

    export OIDC_ENDPOINT='<https://<your_oidc_endpoint_domain>'

    uv sync --locked
    uv run python main.py
    ```
</details>

<details open>
    <summary>From `docker` build</summary>

    ```shell
    docker run -e OIDC_ENDPOINT="<https://<your_oidc_endpoint_domain>" -p ghcr.io/luccitan/pocketid-webfinger:latest
    ```
</details>

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
  pocketid:
    container_name: pocketid
    image: ghcr.io/pocket-id/pocket-id:v2
    restart: unless-stopped
    env_file: .env
    volumes:
      - "/volumes/auth/pocketid-data:/app/data"
    networks:
      - default
      - network-traefik
    healthcheck:
      test: [ "CMD", "/app/pocket-id", "healthcheck" ]
      interval: 1m30s
      timeout: 5s
      retries: 2
      start_period: 10s
    labels:
      traefik.enable: true
      traefik.http.services.pocketid.loadbalancer.server.port: 1411
      traefik.http.routers.pocketid.rule: Host(`oidc.mydomain.com`)
      traefik.http.routers.pocketid.entrypoints: websecure
      traefik.http.routers.pocketid.service: pocketid

  webfinger:
    container_name: pocketid-webfinger
    image: ghcr.io/luccitan/pocketid-webfinger:latest
    depends_on:
      - pocketid
    networks:
      - default
      - network-traefik
    environment:
      OIDC_ENDPOINT: auth.mydomain.com
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
- The OIDC endpoint MUST be accessible through HTTPS and the proxy app targets the endpoint with the `https` scheme in the URI
- The OIDC endpoint URI is in the form of `https://optional-subdomain.domain.tld` with no suffixes.
- The `resource` argument is in the form of `acct:user@email.com`
- The `http://openid.net/specs/connect/1.0/issuer` minimum info in the Webfinger responses is returned in the `links`
- Some additional optional `links` are added.
