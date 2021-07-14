#!/usr/bin/env bash

tests/wait_for.sh "minikube start --driver=docker --kubernetes-version=v1.18.15" "240" "waited too long for minikube to start" &
