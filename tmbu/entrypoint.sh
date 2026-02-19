#!/bin/bash
set -e

# Wait for Milvus to be available
until nc -z milvus-standalone 19530; do
  echo "Waiting for Milvus on milvus-standalone:19530..."
  sleep 2
done

echo "Milvus is up!"

python3 manage.py migrate
python3 manage.py load_milvus_collection

# Start your Django app (change "yourproject" to your Django project name!)
exec gunicorn --config tmbu/gunicorn.conf.py tmbu.wsgi:application 
