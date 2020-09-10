#!/usr/bin/env bash

cd `mktemp -d` &&\
curl -Ls https://get.helm.sh/helm-v3.2.4-linux-amd64.tar.gz -ohelm.tar.gz &&\
tar -xzvf helm.tar.gz && mv linux-amd64/helm /usr/local/bin/helm &&\
chmod +x /usr/local/bin/helm &&\
rm -rf linux-amd64 && rm helm.tar.gz
