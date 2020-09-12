#!/usr/bin/env bash

[ "$(cwm_worker_deployment chart_cache_init cwm-worker-deployment-minio 0.0.0-20200829T091900 minio)" == "${CWM_WORKER_DEPLOYMENT_HELM_CACHE_DIR:-/var/cache/cwm-worker-deployment-helm-cache}/cwm-worker-deployment-minio/0.0.0-20200829T091900/cwm-worker-deployment-minio" ]
