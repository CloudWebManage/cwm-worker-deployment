#!/usr/bin/env bash

tests/wait_for.sh "minikube start --driver=docker --kubernetes-version=v1.16.14" "240" "waited too long for minikube to start" &
