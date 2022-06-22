# using ubuntu LTS version
FROM ubuntu:20.04 AS builder-image

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install \
    --no-install-recommends -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    git \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3.10-distutils

# create and activate virtual environment
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install pip requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --prefix=/tmp --no-cache-dir wheel \
    && pip install --no-cache-dir --upgrade -r requirements.txt

FROM ubuntu:20.04 AS runner-image

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install \
    --no-install-recommends -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    git \
    python3.10 \
    python3.10-venv \
    && rm -rf /var/lib/apt/lists/*

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

ARG USERNAME=appuser
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN useradd --create-home $USERNAME \
    && mkdir -p /home/appuser/app \
    && mkdir -p $PLAYWRIGHT_BROWSERS_PATH

COPY --from=builder-image --chown=$USERNAME:$USERNAME /opt/venv /opt/venv
COPY --chown=$USERNAME:$USERNAME . /home/${USERNAME}/app

# activate virtual environment
ENV VIRTUAL_ENV="/opt/venv"
RUN python3.10 -m venv $VIRTUAL_ENV
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"

RUN playwright install --with-deps firefox \
    && rm -rf /var/lib/apt/lists/*

# In addition to chown above, sets user after files have been copied
USER appuser

WORKDIR /home/${USERNAME}/app

# EXPOSE 8000

ENTRYPOINT ["python", "meetup_query.py"]
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
# CMD ["/bin/bash"]
