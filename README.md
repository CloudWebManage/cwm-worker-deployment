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

### Start infrastructure

start a Minikube cluster

```
bin/minikube_start.sh && bin/minikube_wait.sh
``` 

Make sure you are connected to the minikube cluster

```
kubectl get nodes
```

Set secret env vars (you can get them from Jenkins):

```
export PACKAGES_READER_GITHUB_USER=
export PACKAGES_READER_GITHUB_TOKEN=
```

Deploy a testing instance of Prometheus on the minikube cluster and wait for it to be ready 

```
bin/prometheus_deploy_wait.sh
```

### Run tests

Activate the virtualenv

```
. venv/bin/activate
```

Run all tests

```
pytest
```

Run a tests with full output, by specifying part of the test method name

```
pytest -sk test_history
```

Or by specifying the specific test file name:

```
pytest -s tests/test_helm.py
```

Pytest has many options, check the help message or [pytest documentation](https://docs.pytest.org/en/latest/) for details
