#!/bin/bash

celery -A ghost worker -l info -Q periodic_queue -n periodic_queue@%h &
