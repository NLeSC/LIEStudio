#!/bin/sh

if [ "$1" = 'redis-cluster' ]; then
    max_port=7007
    if [ "$CLUSTER_ONLY" = "true" ]; then
      max_port=7005
    fi

    for port in `seq 7000 $max_port`; do
      mkdir -p /redis-conf/${port}
      mkdir -p /redis-data/${port}

      if [ -e /redis-data/${port}/nodes.conf ]; then
        rm /redis-data/${port}/nodes.conf
      fi

      if [ "$port" -lt "7006" ]; then
        PORT=${port} envsubst < /redis-conf/redis-cluster.tmpl > /redis-conf/${port}/redis.conf
      else
        PORT=${port} envsubst < /redis-conf/redis.tmpl > /redis-conf/${port}/redis.conf
      fi
    done

    bash /generate-supervisor-conf.sh $max_port > /etc/supervisor/supervisord.conf

    supervisord -c /etc/supervisor/supervisord.conf
    sleep 3

    # IP=0.0.0.0 # disable IP binding to bind to the host that is requested
    echo "yes" | ruby /redis/src/redis-trib.rb create --replicas 1 7000 7001 7002 7003 7004 7005
    tail -f /var/log/supervisor/redis*.log
else
  exec "$@"
fi
