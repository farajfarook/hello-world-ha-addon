#!/usr/bin/with-contenv bashio

bashio::log.info "Starting web UI on port 8099..."
python3 /server.py &

INTERVAL=$(bashio::config 'log_interval')
while true; do
  MESSAGE=$(bashio::config 'message')
  bashio::log.info "${MESSAGE}"
  sleep "${INTERVAL}"
done
