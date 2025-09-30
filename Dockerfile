FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies and Python packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-gdal \
    python3-numpy \
    python3-pandas \
    python3-requests \
    python3-dateutil \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

# Verify GDAL installation
RUN gdalinfo --version

# Copy application
COPY . /app
WORKDIR /app

# Install only runtime dependencies (not dev/test dependencies)
RUN pip3 install --break-system-packages \
    geojson>=2.4.1 \
    geojsonio \
    pygeoj \
    pyshp \
    pyproj \
    patool \
    traitlets \
    wheel \
    pangaeapy \
    osfclient \
    filesizelib \
    setuptools-scm>=8 \
    tqdm \
    beautifulsoup4 \
    geopy \
    python-dotenv

# Set version for setuptools-scm
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.9.0

# Install geoextent
RUN pip3 install --break-system-packages -e . --no-deps

# Verify geoextent installation
RUN python3 -m geoextent --version

# Create a non-root user for security
ARG USER=geoextent
ARG UID=1001
ENV USER=${USER}
ENV UID=${UID}
ENV HOME=/home/${USER}

RUN adduser --disabled-password \
    --gecos "Geoextent user" \
    --uid ${UID} \
    ${USER}

# Create data directory for mounting external data
RUN mkdir -p /data && \
    chown ${USER}:${USER} /data

# Switch to non-root user
USER ${USER}
WORKDIR /data

# Set the entrypoint to geoextent CLI
ENTRYPOINT ["python3", "-m", "geoextent"]
CMD ["--help"]
