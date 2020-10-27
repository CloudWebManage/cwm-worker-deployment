import os
import time
import base64
import datetime
import subprocess


PACKAGES_READER_GITHUB_USER = os.environ.get("PACKAGES_READER_GITHUB_USER")
PACKAGES_READER_GITHUB_TOKEN = os.environ.get("PACKAGES_READER_GITHUB_TOKEN")
PULL_SECRET = '{"auths":{"docker.pkg.github.com":{"auth":"__AUTH__"}}}'.replace("__AUTH__", base64.b64encode("{}:{}".format(PACKAGES_READER_GITHUB_USER, PACKAGES_READER_GITHUB_TOKEN).encode()).decode())


def wait_for_cmd(cmd, expected_returncode, ttl_seconds, error_msg, expected_output=None):
    start_time = datetime.datetime.now()
    while True:
        returncode, output = subprocess.getstatusoutput(cmd)
        if returncode == expected_returncode and (expected_output is None or expected_output == output):
            break
        if (datetime.datetime.now() - start_time).total_seconds() > ttl_seconds:
            print(output)
            raise Exception(error_msg)
        time.sleep(1)


def wait_for_func(func, expected_result, ttl_seconds, error_msg):
    start_time = datetime.datetime.now()
    while True:
        result = func()
        if result == expected_result:
            break
        if (datetime.datetime.now() - start_time).total_seconds() > ttl_seconds:
            print(result)
            raise Exception(error_msg)
        time.sleep(1)


def init_wait_namespace(namespace_name, delete=False):
    if delete:
        returncode, output = subprocess.getstatusoutput('kubectl get ns {}'.format(namespace_name))
        if returncode == 0:
            returncode, output = subprocess.getstatusoutput('kubectl delete ns {}'.format(namespace_name))
            assert returncode == 0, output
            wait_for_cmd('kubectl get ns {}'.format(namespace_name), 1, 30,
                         'waited too long for namespace to be deleted')
    returncode, output = subprocess.getstatusoutput('kubectl get ns {}'.format(namespace_name))
    if returncode == 1:
        returncode, output = subprocess.getstatusoutput('kubectl create ns {}'.format(namespace_name))
        assert returncode == 0, output
        wait_for_cmd('kubectl get ns {}'.format(namespace_name), 0, 30,
                     'waited too long for test namespace to be created')
