#!/bin/bash

celery -A mysite worker -l info -Q periodic_queue -n periodic_queue@%h
