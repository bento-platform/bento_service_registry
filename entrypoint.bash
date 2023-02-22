#!/bin/bash

cd /service-registry || exit

# Create bento_user + home
source /create_service_user.bash

# Fix permissions on /service-registry and /env
chown -R bento_user:bento_user /service-registry
if [[ -d /env ]]; then
  chown -R bento_user:bento_user /env
fi

# Drop into bento_user from root and execute the CMD specified for the image
exec gosu bento_user "$@"
