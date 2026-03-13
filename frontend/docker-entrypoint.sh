#!/bin/sh
# Replace only $API_URL in nginx template, leave nginx vars ($uri, $host, etc.) untouched
envsubst '$API_URL' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
