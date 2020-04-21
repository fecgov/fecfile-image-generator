FROM weboaks/node-karma-protractor-chrome
# FROM debian:stretch

ENV PATH /usr/local/bin:$PATH

RUN wget -qO - https://raw.githubusercontent.com/yarnpkg/releases/gh-pages/debian/pubkey.gpg | apt-key add - && \
DEBIAN_FRONTEND=nointeractive apt-get update && apt-get install -y apt-utils && \ 
    apt-get install -y --no-install-recommends libffi-dev \
    build-essential libreadline-gplv2-dev \
    libncursesw5-dev libssl-dev libsqlite3-dev tk-dev \
    libgdbm-dev libc6-dev libbz2-dev xvfb xauth \
    locales gcc libc6 libgcc1 libstdc++6 pdftk \
    tk-dev uuid-dev wget ca-certificates gnupg dirmngr

RUN rm -rf /var/lib/apt/lists/* \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

RUN wget --quiet -O wkhtmltopdf.tar.xz "https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.4/wkhtmltox-0.12.4_linux-generic-amd64.tar.xz"
RUN tar -xvf wkhtmltopdf.tar.xz
RUN mv wkhtmltox/bin/wkhtmlto* /usr/bin/

ENV LANG en_US.utf8


ENV GPG_KEY 0D96DF4D4110E5C43FBFB17F2D347EA6AA65421D
ENV PYTHON_VERSION 3.7.2

RUN set -ex \ 
    \
     && wget --quiet -O python.tar.xz "https://www.python.org/ftp/python/${PYTHON_VERSION%%[a-z]*}/Python-$PYTHON_VERSION.tar.xz" \
     && mkdir -p /usr/src/python \
     && tar -xJC /usr/src/python --strip-components=1 -f python.tar.xz \
     && rm python.tar.xz \
     \
    && cd /usr/src/python \
    && gnuArch="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)" \
    && ./configure \
      --build="$gnuArch" \
      --enable-loadable-sqlite-extensions \
      --enable-shared \
      --with-system-expat \
      --with-system-ffi \
      --without-ensurepip \
   && make -j "$(nproc)" \
   && make install \
   && ldconfig \
  \
     && find /usr/local -depth \
     \( \
       \( -type d -a \( -name test -o -name tests \) \) \
        -o \
    \( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
     \) -exec rm -rf '{}' + \
 && rm -rf /usr/src/python

RUN cd /usr/local/bin \
    && ln -s idle3 idle \
    && ln -s pydoc3 pydoc \
    && ln -s python3 python \
    && ln -s python3-config python-config

ENV PYTHON_PIP_VERSION 19.0.3

RUN set -ex; \
    \
    wget --quiet -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'; \
   \
  python3 get-pip.py \
          --disable-pip-version-check \
          --no-cache-dir \
          "pip==$PYTHON_PIP_VERSION" \
     ; \
  pip install --upgrade pip \
 pip --version; \
 \
 find /usr/local -depth \
  \( \
  \( -type d -a \( -name test -o -name tests \) \) \
  -o \
  \( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
 \) -exec rm -rf '{}' +; \
rm -f get-pip.py


RUN mkdir /opt/imagegenerator
WORKDIR /opt/imagegenerator
ADD . /opt/imagegenerator


RUN pip install --upgrade pip && pip install -r requirements.txt
# remove the default xvfb-run file and replace it with our own. 
RUN rm /usr/bin/xvfb-run
ADD ./lib/xvfb-run /usr/bin/
ADD ./lib/wkhtmltopdf.sh /usr/bin/

RUN chmod a+x /usr/bin/wkhtmltopdf.sh && sh -c 'if [ ! -e "/usr/local/bin/wkhtmltopdf" ]; then ln -s /usr/bin/wkhtmltopdf.sh /usr/local/bin/wkhtmltopdf; fi'
#RUN flake8 .

RUN useradd igen --no-create-home --home /opt/imagegenerator && chown -R igen:igen /opt/imagegenerator
USER igen

EXPOSE 8080
ENTRYPOINT ["gunicorn", "-w", "4", "--bind", "0.0.0.0:8080", "wsgi:APP"]


