# See https://just.systems/man/en

# load .env (e.g., ${HEROKU_APP})
set dotenv-load

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
        docker build -f Dockerfile.web -t {{TAG}} --build-arg CHIPSET_ARCH=aarch64-linux-gnu .
    else
        docker buildx build -f Dockerfile.web --progress=plain -t {{TAG}} --build-arg CHIPSET_ARCH=x86_64-linux-gnu --load .
    fi

# intel build over ssh, then push to heroku
buildx:
    docker buildx build -f Dockerfile.web --progress=plain -t {{TAG}} --build-arg CHIPSET_ARCH=x86_64-linux-gnu --load .
    heroku container:release web --app ${HEROKU_APP}

# arm build w/docker-compose defaults (no push due to arm64)
build-clean:
    docker-compose build --pull --no-cache --build-arg CHIPSET_ARCH=aarch64-linux-gnu --parallel

# kick off a build on heroku from ci
push:
    git push heroku main

# pull latest heroku image
pull:
    #!/usr/bin/env bash
    set -euxo pipefail
    if [[ $(heroku auth:whoami 2>&1 | awk '/Error/ {$1=""; print $0}' | xargs) = "Error: not logged in" ]]; then
        echo 'Not logged into Heroku. Logging in now...'
        heroku auth:login
        heroku container:login
    fi
    docker pull {{TAG}}

# start docker-compose container
start:
    docker-compose up -d

# run container
run:
    docker run --rm -it \
    --env-file .env \
    -p 3000:3000 \
    -v $(pwd):/app \
    --name {{APP}} {{TAG}} {{SHELL}}

# ssh into container
exec:
    docker exec -it {{APP}} {{SHELL}}

# stop docker-compose container
stop:
    docker-compose stop

# remove docker-compose container(s) and networks
down:
    docker-compose stop && docker-compose down --remove-orphans
