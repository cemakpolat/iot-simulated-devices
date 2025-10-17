#!/bin/sh
# A robust wait-for-it.sh script that correctly parses host and port.

set -e

hostport="$1"
shift
cmd="$@"

# Use cut to separate HOST and PORT
host=$(echo "$hostport" | cut -d: -f1)
port=$(echo "$hostport" | cut -d: -f2)

# Wait for the service to be available
until nc -z "$host" "$port"; do
  >&2 echo "Service at $host:$port is unavailable - sleeping"
  sleep 1
done

>&2 echo "Service at $host:$port is up - executing command"
exec $cmd