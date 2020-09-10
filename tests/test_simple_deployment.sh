#!/usr/bin/env bash

echo deploying simple deployment test1 &&\
echo '
cwm-worker-deployment:
  type: minio
  namespace: test1
minio:
  createPullSecret: |
    '${PULL_SECRET}'
' | cwm_worker_deployment deploy &&\
echo waiting for deployment to be ready &&\
tests/wait_for.sh "cwm_worker_deployment is_ready test1 minio" "30" "watied too long for simple deployment to be ready" &&\
echo getting deployment details &&\
cwm_worker_deployment details test1 minio &&\
echo getting deployment history &&\
cwm_worker_deployment history test1 minio &&\
echo getting deployment hostname &&\
[ "$(cwm_worker_deployment get_hostname test1 minio)" == "minio.test1.svc.cluster.local" ] &&\
echo deleting deployment &&\
cwm_worker_deployment delete test1 minio --delete-namespace &&\
echo waiting for namespace to be deleted &&\
tests/wait_for.sh "! kubectl get ns test1" "30" "waited too long for namesapce to be deleted" &&\
