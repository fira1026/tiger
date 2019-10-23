#!/bin/bash

until python manage.py makemigrations && python manage.py migrate
do
  echo "Try again"
done &&

# Loaddata should be executed after migration is done
python manage.py loaddata product_demo
python manage.py loaddata shop_demo

#python manage.py runserver 0.0.0.0:8000
uwsgi --ini /uwsgi/uwsgi.ini
