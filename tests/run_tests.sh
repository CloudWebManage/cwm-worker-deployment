#!/usr/bin/env bash

ALL_RES=0
for TEST in tests/test_*.sh; do
    echo "-- ${TEST}"
    if $TEST; then
        echo OK
    else
        echo FAILED
        ALL_RES=1
    fi
done
[ "${ALL_RES}" != "0" ] && exit 1
exit 0