# cwm-worker-deployment

## Local development

### Install

Create virtualenv

```
python3 -m venv venv
```

Install dependencies

```
venv/bin/python -m pip install -r requirements.txt
```

Install the Python module

```
venv/bin/python -m pip install -e .
```

### Usage

Activate the virtualenv

```
. venv/bin/activate
```

Make sure you are connected to a local / testing Kubernetes cluster before running any commands

Debug a workload - will only print the actions that will be performed

```
echo '
cwm-worker-deployment:
  type: minio
  namespace: example007--com
  version: 0.0.0

minio:
  volumes:
    storage: |
      persistentVolumeClaim:
        claimName: example007--com
    cache: |
      hostPath:
        path: /remote/cache/example007--com
        type: DirectoryOrCreate

extraObjects:
- apiVersion: v1
  kind: PersistentVolume
  name: example007--com
  spec: |
    accessModes:
    - ReadWriteMany
    capacity:
      storage: 1Ti
    csi:
      driver: shbs.csi.kamatera.com
      volumeAttributes:
        foo: bar
        baz: bax
      volumeHandle: example007--com
    persistentVolumeReclaimPolicy: Retain
    volumeMode: Filesystem
- apiVersion: v1
  kind: PersistentVolumeClaim
  name: example007--com
  spec: |
    accessModes:
    - ReadWriteMany
    resources:
      requests:
        storage: 1Ti
    storageClassName: ""
    volumeMode: Filesystem
    volumeName: example007--com
' | cwm_worker_deployment deploy --dry-run
```

Set your personal GitHub access token in env vars

```
PACKAGES_READER_GITHUB_USER=
PACKAGES_READER_GITHUB_TOKEN=
```

Set the pull secret in env var

```
PULL_SECRET='{"auths":{"docker.pkg.github.com":{"auth":"'"$(echo -n "${PACKAGES_READER_GITHUB_USER}:${PACKAGES_READER_GITHUB_TOKEN}" | base64 -w0)"'"}}}'
```

Deploy a workload from local helm chart

Following example assumes you have the other chart at `../cwm-worker-deployment-minio/helm`

```
echo '
cwm-worker-deployment:
  type: minio
  namespace: test2
  chart-path: ../cwm-worker-deployment-minio/helm

minio:
  createPullSecret: |
    '${PULL_SECRET}'
' | cwm_worker_deployment deploy
```

Deploy a workload from the remote repository using latest version

Deploy

```
echo '
cwm-worker-deployment:
  type: minio
  namespace: example007--com

minio:
  createPullSecret: "'"${PULL_SECRET}"'"
' | cwm_worker_deployment deploy
```
