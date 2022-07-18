FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    USER=calitp

    # create non-root $USER and home directory
RUN useradd --create-home --shell /bin/bash $USER && \
    # setup $USER permissions for nginx
    mkdir -p /var/cache/nginx && \
    chown -R $USER /var/cache/nginx && \
    mkdir -p /var/lib/nginx && \
    chown -R $USER /var/lib/nginx && \
    mkdir -p /var/log/nginx && \
    chown -R $USER /var/log/nginx && \
    touch /var/log/nginx/error.log && \
    chown $USER /var/log/nginx/error.log && \
    touch /var/run/nginx.pid && \
    chown -R $USER /var/run/nginx.pid && \
    # setup directories and permissions for Django and gunicorn
    mkdir -p /home/$USER/app/config && \
    mkdir -p /home/$USER/app/run && \
    mkdir -p /home/$USER/app/static && \
    chown -R $USER /home/$USER && \
    # install server components
    apt-get update && \
    # install git for use when installing dependencies from VCS (https://pip.pypa.io/en/stable/topics/vcs-support/)
    apt-get install -qq --no-install-recommends build-essential gettext git nginx

# enter app directory
WORKDIR /home/$USER/app
# switch to non-root $USER
USER $USER

# install python dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# copy config files
COPY gunicorn.conf.py gunicorn.conf.py
COPY manage.py manage.py

# overwrite default nginx.conf
COPY nginx.conf /etc/nginx/nginx.conf

# update PATH for local pip installs
ENV PATH "$PATH:/home/$USER/.local/bin"

# copy source files
COPY bin/ bin/
COPY benefits/ benefits/

# ensure $USER can compile messages in the locale directories
USER root
RUN chmod -R 777 benefits/locale
USER $USER

# configure container executable
ENTRYPOINT ["/bin/bash"]
CMD ["bin/start.sh"]
