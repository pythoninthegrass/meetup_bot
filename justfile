# See https://just.systems/man/en

# load .env (e.g., ${HEROKU_APP})
set dotenv-load

# positional params
set positional-arguments

# set env var
export APP      := "meetupbot"
export POETRY   := `echo ${POETRY}`
export PY_VER   := `echo ${PY_VER}`
export SCRIPT   := "scheduler.sh"
export SHELL    := "/bin/bash"
export TAG      := "registry.heroku.com/${HEROKU_APP}/web:latest"

# x86_64/arm64
arch := `uname -m`

# hostname
host := `uname -n`

# operating system
os := `uname -s`

# home directory
home_dir := env_var('HOME')

# docker-compose / docker compose
# * https://docs.docker.com/compose/install/linux/#install-using-the-repository
docker-compose := if `command -v docker-compose; echo $?` == "0" {
	"docker-compose"
} else {
	"docker compose"
}

# [halp]     list available commands
default:
	just --list

# [init]     install dependencies, tooling, and virtual environment
install:
    #!/usr/bin/env bash
    set -euxo pipefail

    # TODO: QA
    # dependencies
    if [[ {{os}} == "Linux" ]]; then
        . "/etc/os-release"
        case $ID in
            ubuntu|debian)
                sudo apt update && sudo apt install -y \
                    build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl \
                    llvm libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
                ;;
            arch|endeavouros)
                sudo pacman -S --noconfirm \
                    base-devel openssl zlib bzip2 xz readline sqlite tk
                ;;
            fedora)
                sudo dnf install -y \
                    make gcc zlib-devel bzip2 bzip2-devel readline-devel \
                    sqlite sqlite-devel openssl-devel xz xz-devel libffi-devel
                ;;
            centos)
                sudo yum install -y \
                    make gcc zlib-devel bzip2 bzip2-devel readline-devel \
                    sqlite sqlite-devel openssl-devel xz xz-devel libffi-devel
                ;;
            *)
                echo "Unsupported OS"
                exit 1
                ;;
        esac
    elif [[ {{os}} == "Darwin" ]]; then
        xcode-select --install
        [[ $(command -v brew >/dev/null 2>&1; echo $?) == "0" ]] || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        brew install gettext openssl readline sqlite3 xz zlib tcl-tk
    elif [[ os() == "Windows"]]; then
        echo "Windows is not supported"
        exit 1
    else
        echo "Unsupported OS"
        exit 1
    fi

    # install asdf
    git clone https://github.com/asdf-vm/asdf.git "{{home_dir}}/.asdf" --branch v0.11.1
    . "{{home_dir}}/.asdf/asdf.sh"

    # install python w/asdf
    asdf plugin-add python
    asdf install python {{PY_VER}}

    # install poetry
    asdf plugin-add poetry https://github.com/asdf-community/asdf-poetry.git
    asdf install poetry {{POETRY}}

    # create virtual environment
    poetry config virtualenvs.in-project true
    poetry env use python
    poetry install --no-root

# [deps]     update dependencies
update-deps:
    #!/usr/bin/env bash
    # set -euxo pipefail
    find . -maxdepth 3 -name "pyproject.toml" -exec \
        echo "[{}]" \; -exec \
        echo "Clearring pypi cache..." \; -exec \
        poetry cache clear --all pypi --no-ansi \; -exec \
        poetry update --lock --no-ansi \;

# [deps]     export requirements.txt
export-reqs: update-deps
    #!/usr/bin/env bash
    # set -euxo pipefail
    find . -maxdepth 3 -name "pyproject.toml" -exec \
        echo "[{}]" \; -exec \
        echo "Exporting requirements.txt..." \; -exec \
        poetry export --no-ansi --without-hashes --output requirements.txt \;

# [git]      update git submodules
sub:
    @echo "To add a submodule:"
    @echo "git submodule add https://github.com/username/repo.git path/to/submodule"
    @echo "Updating all submodules..."
    git submodule update --init --recursive && git pull --recurse-submodules -j8

# [git]      update pre-commit hooks
pre-commit:
    @echo "To install pre-commit hooks:"
    @echo "pre-commit install"
    @echo "Updating pre-commit hooks..."
    pre-commit autoupdate

# [check]    lint sh script
checkbash:
    #!/usr/bin/env bash
    checkbashisms {{SCRIPT}}
    if [[ $? -eq 1 ]]; then
        echo "bashisms found. Exiting..."
        exit 1
    else
        echo "No bashisms found"
    fi

# [scripts]  run script in working directory
sh args:
    sh {{args}}

# [heroku]   update env vars
env:
    heroku config:set $(cat .env | grep -v '^#' | xargs)

# [heroku]   get current heroku status
stats:
    heroku ps
    heroku status
    heroku builds
    heroku releases

# [heroku]   get current heroku logs
logs:
    heroku logs --tail

# [heroku]   open heroku url
open:
    heroku open -a ${HEROKU_APP}

# [docker]   build locally
build: checkbash
    #!/usr/bin/env bash
    set -euxo pipefail
    if [[ {{arch}} == "arm64" ]]; then
        docker build -f Dockerfile.web -t {{TAG}} --build-arg CHIPSET_ARCH=aarch64-linux-gnu .
    else
        docker build -f Dockerfile.web --progress=plain -t {{TAG}} .
    fi

# [docker]   arm build
buildx: checkbash
    docker buildx build -f Dockerfile.web --progress=plain -t {{TAG}} --build-arg CHIPSET_ARCH=x86_64-linux-gnu --load .

# [docker]   release to heroku
release: buildx
    heroku container:release web --app ${HEROKU_APP}
    just stats

# [docker]   arm build w/docker-compose defaults (no push due to arm64)
build-clean: checkbash
    {{docker-compose}} build --pull --no-cache --build-arg CHIPSET_ARCH=aarch64-linux-gnu --parallel

# [heroku]   push latest image / kick off a build on heroku from ci
push: checkbash
    git push heroku main -f
    just stats

# [heroku]   pull latest image
pull:
    #!/usr/bin/env bash
    set -euxo pipefail
    if [[ $(heroku auth:whoami 2>&1 | awk '/Error/ {$1=""; print $0}' | xargs) =~ "Error: " ]]; then
        echo 'Not logged into Heroku. Logging in now...'
        heroku auth:login
        heroku container:login
    fi
    docker pull {{TAG}}

# [heroku]   run container hosted on heroku
run-heroku:
    heroku run {{SHELL}} -a ${HEROKU_APP}

# [docker]   run container
run:
    docker run --rm -it \
    --env-file .env \
    -p 3000:3000 \
    -v $(pwd):/app \
    --name {{APP}} {{TAG}} {{SHELL}}

# [docker]   start docker-compose container
up:
	{{docker-compose}} up -d

# [docker]   ssh into container
exec:
    docker exec -it {{APP}} {{SHELL}}

# [docker]   stop docker-compose container
stop:
	{{docker-compose}} stop

# [docker]   remove docker-compose container(s) and networks
down: stop
	{{docker-compose}} down --remove-orphans
