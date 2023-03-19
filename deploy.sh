#!/bin/bash

# Build virtual env
rm -r virtualenv 2&> /dev/null
echo "Deleted old virtual env if it existed."
virtualenv --without-pip virtualenv
pip install -r requirements.txt --target virtualenv/lib/python3.11/site-packages
zip -j -r myaction.zip __main__.py virtualenv

ibmcloud fn namespace target python311test
ibmcloud fn action update test myaction.zip \
  --docker openwhisk/action-python-v3.11:4707653
