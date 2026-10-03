# Ubuntu 20.04 build environment for the phh-treble Android 12 tree
FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
    bc bison build-essential ccache curl flex g++-multilib gcc-multilib git git-lfs gnupg gperf \
    imagemagick lib32ncurses5-dev lib32readline-dev lib32z1-dev liblz4-tool libncurses5 libncurses5-dev \
    libsdl1.2-dev libssl-dev libxml2 libxml2-utils lzop pngcrush rsync schedtool squashfs-tools xsltproc \
    zip unzip zlib1g-dev openjdk-8-jdk python python3 python-is-python2 ca-certificates sudo xxd file cpio \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://storage.googleapis.com/git-repo-downloads/repo -o /usr/local/bin/repo && chmod +x /usr/local/bin/repo
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID builder && useradd -m -u $UID -g $GID -s /bin/bash builder \
    && echo "builder ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/builder
USER builder
ENV USE_CCACHE=1 CCACHE_EXEC=/usr/bin/ccache CCACHE_DIR=/ccache
WORKDIR /src
