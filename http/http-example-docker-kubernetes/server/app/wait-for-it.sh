#!/bin/sh
# wait-for-it.sh

set -e

host="$1"
shift
cmd="$@"

until nc -z "$host" 80; do
  >&2 echo "Server is unavailable - sleeping"
  sleep 1
done

>&2 echo "Server is up - executing command"
exec $cmd