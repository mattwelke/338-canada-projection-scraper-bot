#!/bin/bash

# Build virtual env
rm -r virtualenv 2&> /dev/null
echo "Deleted old virtual env if it existed."

set -e

virtualenv --without-pip virtualenv
pip install -r requirements.txt --target virtualenv/lib/python3.11/site-packages
zip -r myaction.zip __main__.py virtualenv

ibmcloud target -g Default
ibmcloud fn namespace target python311test
ibmcloud fn action update 338-canada-scraper-bot myaction.zip \
  --docker openwhisk/action-python-v3.11:4707653
