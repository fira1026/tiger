FROM python:3.6.0

WORKDIR /app
EXPOSE 8000

ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install vim gettext -y \
    unzip

RUN pip install --upgrade pip

COPY ./app /app
COPY requirements.txt requirements.txt
COPY ./conf.d/uwsgi.ini /uwsgi/uwsgi.ini
# install service required module
RUN pip install -r requirements.txt

# "set no compatible" is used to fix arrow keys error in vim insert mode
# timeout is in case for non-nullable fields input return to throw an error
RUN timeout 30 yes | python manage.py makemigrations && \
    python manage.py compilemessages

ENTRYPOINT ["/app/dev-entrypoint.sh"]
