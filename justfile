# See https://just.systems/man/en

# load .env (e.g., ${HEROKU_APP})
set dotenv-load := true

# set env var
export APP   := "meetupbot"
export SHELL := "/bin/sh"
export TAG   := "registry.heroku.com/${HEROKU_APP}/web:latest"

# x86_64/arm64
arch := `uname -m`

# hostname
host := `uname -n`

# halp
default:
    just --list

# build locally or on intel box
build:
    #!/usr/bin/env bash
    set -euxo pipefail
    # accepts justfile env/vars
    if [[ {{arch}} == "arm64" ]]; then
        docker build -f Dockerfile.web -t $TAG --build-arg CHIPSET_ARCH=aarch64-linux-gnu .
    else
        docker buildx build -f Dockerfile.web --progress=plain -t $TAG --build-arg CHIPSET_ARCH=x86_64-linux-gnu --load .
    fi

# intel build
buildx:
    docker buildx build -f Dockerfile.web --progress=plain -t $TAG --build-arg CHIPSET_ARCH=x86_64-linux-gnu --load .

# arm build w/docker-compose defaults
build-clean:
    docker-compose build --pull --no-cache --build-arg CHIPSET_ARCH=aarch64-linux-gnu

# pull latest heroku image
pull:
    docker pull registry.heroku.com/${HEROKU_APP}/web

# start docker-compose container
start:
    docker-compose up -d

# ssh into container
exec:
    docker-compose exec {{APP}} {{SHELL}}

# stop docker-compose container
stop:
    docker-compose stop

# remove docker-compose container(s) and networks
down:
    docker-compose stop && docker-compose down --remove-orphans
