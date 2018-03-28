#!/bin/sh

if [ "$1" = 'redis-cluster' ]; then
    for port in `seq 7010 7017`; do
      mkdir -p /redis-conf/${port}
      mkdir -p /redis-data/${port}

      if [ -e /redis-data/${port}/nodes.conf ]; then
        rm /redis-data/${port}/nodes.conf
      fi
    done

    for port in `seq 7010 7015`; do
      PORT=${port} envsubst < /redis-conf/redis-cluster.tmpl > /redis-conf/${port}/redis.conf
    done

    for port in `seq 7016 7017`; do
      PORT=${port} envsubst < /redis-conf/redis.tmpl > /redis-conf/${port}/redis.conf
    done

    supervisord -c /etc/supervisor/supervisord.conf
    sleep 3

    echo "yes" | ruby /redis/src/redis-trib.rb create --replicas 1 7010 7011 7012 7013 7014 7015
    tail -f /var/log/supervisor/redis*.log
else
  exec "$@"
fi
