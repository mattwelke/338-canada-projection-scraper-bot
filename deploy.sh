#!/bin/bash

# Build virtual env
rm -r virtualenv 2&> /dev/null
echo "Deleted old virtual env if it existed."

rm myaction.zip 2&> /dev/null
echo "Deleted old deployment ZIP file if it existed."

set -e
zip -r myaction.zip __main__.py requirements.txt

ibmcloud target -g Default
ibmcloud fn namespace target 338-canada-scraper-bot
ibmcloud fn action update bot myaction.zip \
  --docker openwhisk/action-python-v3.11:4707653 \
  --timeout 60000 \
  --memory 256
