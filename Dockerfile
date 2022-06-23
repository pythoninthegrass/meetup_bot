# using ubuntu LTS version
FROM ubuntu:20.04 AS builder-image

COPY requirements.txt .

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
    python3.10-distutils \
    && rm -rf /var/lib/apt/lists/*

# create and activate virtual environment
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install pip requirements
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --upgrade -r requirements.txt

FROM ubuntu:20.04 AS runner-image

ARG USERNAME=appuser
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN useradd --create-home $USERNAME \
    && mkdir -p /home/${USERNAME}/app \
    && mkdir -p $PLAYWRIGHT_BROWSERS_PATH

COPY --chown=${USERNAME}:${USERNAME} . /home/${USERNAME}/app
COPY --from=builder-image --chown=${USERNAME}:${USERNAME} /opt/venv /opt/venv

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

# ENV NODE_ENV=production

# # Install node 14
# RUN curl -sL https://deb.nodesource.com/setup_14.x | bash - \
#     && apt-get install -y nodejs \
#     && rm -rf /var/lib/apt/lists/*

# # TODO: switch back to python playwright when v1.23 release is available
# # Install playwright
# RUN npm install -g playwright@next \
#     && playwright install --with-deps firefox \
#     && rm -rf /var/lib/apt/lists/*

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# activate virtual environment
ENV VIRTUAL_ENV="/opt/venv"
RUN python3.10 -m venv $VIRTUAL_ENV
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"

# Install playwright
RUN playwright install --with-deps firefox \
    && rm -rf /var/lib/apt/lists/*

# In addition to chown above, sets user after files have been copied
USER appuser

WORKDIR /home/${USERNAME}/app

# EXPOSE 8000

# ENTRYPOINT ["python", "meetup_query.py"]
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
CMD ["/bin/bash"]
