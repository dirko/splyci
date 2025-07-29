#FROM python:3.9-slim
FROM python:3.7-bullseye
LABEL maintainer="Dirko Coetsee <dpcoetsee@gmail.com>"
#ENV http_proxy=deb.debian.org/debian
# Install swipl:
# The following steps taken from https://github.com/SWI-Prolog/docker-swipl/blob/master/8.2.0/stretch/Dockerfile
#  (Removed libspatialindex4v5 install and libmariadbclient18)
#RUN apt-get update && \
#sed -i 's|deb.debian.org/debian|ftp.debian.org/debian|g' /etc/apt/sources.list && \
#RUN for f in /etc/apt/sources.list.d/*.list; do \
#      sed -i 's|deb.debian.org/debian|ftp.debian.org/debian|g' "$f"; \
#    done && \
RUN rm -f /etc/apt/sources.list.d/* && \
    printf "\
deb https://deb.debian.org/debian           bookworm         main\n\
deb https://deb.debian.org/debian           bookworm-updates main\n\
deb https://security.debian.org             bookworm-security main\n" \
    > /etc/apt/sources.list
RUN apt-get update -o Acquire::Retries=3 && \
    apt-get install -y --no-install-recommends \
    libtcmalloc-minimal4 \
    libarchive13 \
    libyaml-dev \
    libgmp10 \
    #libossp-uuid16 \
    #libssl1.1 \
    libuuid1              \
    libssl3               \
    ca-certificates \
    libdb5.3 \
    libpcre3 \
    libedit2 \
    libgeos-c1v5 \
    unixodbc \
    odbc-postgresql \
    tdsodbc \
    libsqlite3-0 \
    libserd-0-0 \
    libraptor2-0 && \
    dpkgArch="$(dpkg --print-architecture)" && \
    rm -rf /var/lib/apt/lists/*
ENV LANG=C.UTF-8
RUN set -eux; \
    SWIPL_VER=8.2.0; \
    SWIPL_CHECKSUM=d8c9f3adb9cd997a5fed7b5f5dbfe971d2defda969b9066ada158e4202c09c3c; \
    BUILD_DEPS='make cmake ninja-build gcc g++ wget git autoconf libarchive-dev libgmp-dev libossp-uuid-dev libpcre3-dev libreadline-dev libedit-dev libssl-dev zlib1g-dev libdb-dev unixodbc-dev libsqlite3-dev libserd-dev libraptor2-dev libgeos++-dev libspatialindex-dev libgoogle-perftools-dev'; \
    dpkgArch="$(dpkg --print-architecture)"; \
    apt-get update; apt-get install -y --no-install-recommends $BUILD_DEPS; rm -rf /var/lib/apt/lists/*; \
    mkdir /tmp/src; \
    cd /tmp/src; \
    wget -q https://www.swi-prolog.org/download/stable/src/swipl-$SWIPL_VER.tar.gz; \
    echo "$SWIPL_CHECKSUM  swipl-$SWIPL_VER.tar.gz" >> swipl-$SWIPL_VER.tar.gz-CHECKSUM; \
    sha256sum -c swipl-$SWIPL_VER.tar.gz-CHECKSUM; \
    tar -xzf swipl-$SWIPL_VER.tar.gz; \
    mkdir swipl-$SWIPL_VER/build; \
    cd swipl-$SWIPL_VER/build; \
    cmake -DCMAKE_BUILD_TYPE=Release \
          -DSWIPL_PACKAGES_X=OFF \
	  -DSWIPL_PACKAGES_JAVA=OFF \
	  -DCMAKE_INSTALL_PREFIX=/usr \
	  -G Ninja \
          ..; \
    ../scripts/pgo-compile.sh; \
    ninja; \
    ninja install; \
    rm -rf /tmp/src; \
    mkdir -p /usr/share/swi-prolog/pack; \
    cd /usr/share/swi-prolog/pack; \
    # usage: install_addin addin-name git-url git-commit
    install_addin () { \
        git clone "$2" "$1"; \
        git -C "$1" checkout -q "$3"; \
        # the prosqlite plugin lib directory must be removed?
        if [ "$1" = 'prosqlite' ]; then rm -rf "$1/lib"; fi; \
        swipl -g "pack_rebuild($1)" -t halt; \
        find "$1" -mindepth 1 -maxdepth 1 ! -name lib ! -name prolog ! -name pack.pl -exec rm -rf {} +; \
        find "$1" -name .git -exec rm -rf {} +; \
        find "$1" -name '*.so' -exec strip {} +; \
    }; \
    dpkgArch="$(dpkg --print-architecture)"; \
    install_addin prosqlite https://github.com/nicos-angelopoulos/prosqlite.git 816cb2e45a5fb53290a763a3306e430b72c40794; \
    [ "$dpkgArch" = 'armhf' ] || [ "$dpkgArch" = 'armel' ] || install_addin rocksdb https://github.com/JanWielemaker/rocksdb.git f110766ee97cfbc6fddd4c33b7238f00e76ecc18; \
    [ "$dpkgArch" = 'armhf' ] || [ "$dpkgArch" = 'armel' ] ||  install_addin hdt https://github.com/JanWielemaker/hdt.git e0a0eff87fc3318434cb493690c570e1255ed30e; \
    install_addin rserve_client https://github.com/JanWielemaker/rserve_client.git 2af6c08fb1b59709dbc48b44f339b06f1217b4a5; \
    apt-get purge -y --auto-remove $BUILD_DEPS


# Install minizinc
RUN apt-get update && apt-get install -y wget
# Taken from https://github.com/pantonante/notebook-constraint-programming/blob/master/docker/Dockerfile
# Retrieve MiniZinc IDE distribution
#  (Replace ADD with wget so the download is cached by docker)
RUN wget -O /minizinc.tgz https://github.com/MiniZinc/MiniZincIDE/releases/download/2.4.3/MiniZincIDE-2.4.3-bundle-linux-x86_64.tgz

# Unpack compressed MiniZinc archive and renamed folder
RUN tar -zxf /minizinc.tgz && \
    mv /MiniZincIDE-2.4.3-bundle-linux-x86_64 /minizinc

# Add MiniZinc's binary path to PATH
ENV PATH="/minizinc:/minizinc/bin:${PATH}"

# Add MiniZinc's library path to LD_LIBRARY_PATH
ENV LD_LIBRARY_PATH="/minizinc/lib:${LD_LIBRARY_PATH}"

# Copy SpLyCI
RUN mkdir /src
WORKDIR /src
COPY requirements_pip.txt .
RUN pip install -r requirements_pip.txt
COPY requirements_dev.txt .
RUN pip install -r requirements_dev.txt
COPY . .
ENV PYTHONPATH="${PYTHONPATH}:/src"


