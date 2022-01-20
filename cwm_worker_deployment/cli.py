import sys
from ruamel import yaml

from cwm_worker_deployment import deployment


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        args = sys.argv[2:]
        dry_run = "--dry-run" in args
        deployment.init(dry_run=dry_run)
    elif len(sys.argv) > 1 and sys.argv[1] == "deploy":
        spec = yaml.safe_load(sys.stdin)
        args = sys.argv[2:]
        dry_run = "--dry-run" in args
        atomic_timeout_string = None
        last_arg = None
        for arg in args:
            if last_arg == "--atomic-timeout":
                atomic_timeout_string = arg
            last_arg = arg
        deployment.deploy(spec, dry_run=dry_run, atomic_timeout_string=atomic_timeout_string)
    elif len(sys.argv) > 1 and sys.argv[1] == "delete":
        args = sys.argv[2:]
        namespace_name = args[0]
        deployment_type = args[1]
        dry_run = "--dry-run" in args
        delete_namespace = "--delete-namespace" in args
        timeout_string = None
        last_arg = None
        for arg in args:
            if last_arg == "--timeout":
                timeout_string = arg
            last_arg = arg
        deployment.delete(namespace_name, deployment_type, dry_run=dry_run, timeout_string=timeout_string, delete_namespace=delete_namespace)
    elif len(sys.argv) > 1 and sys.argv[1] == "is_ready":
        args = sys.argv[2:]
        namespace_name = args[0]
        deployment_type = args[1]
        if deployment.is_ready(namespace_name, deployment_type):
            print("Ready")
        else:
            print("Not Ready")
            exit(10)
    elif len(sys.argv) > 1 and sys.argv[1] == "details":
        args = sys.argv[2:]
        namespace_name = args[0]
        deployment_type = args[1]
        yaml.safe_dump(deployment.details(namespace_name, deployment_type), sys.stdout, default_flow_style=False)
    elif len(sys.argv) > 1 and sys.argv[1] == "history":
        args = sys.argv[2:]
        namespace_name = args[0]
        deployment_type = args[1]
        yaml.safe_dump(deployment.history(namespace_name, deployment_type), sys.stdout, default_flow_style=False)
    elif len(sys.argv) > 1 and sys.argv[1] == "get_hostname":
        args = sys.argv[2:]
        namespace_name = args[0]
        deployment_type = args[1]
        protocol = args[2]
        print(deployment.get_hostname(namespace_name, deployment_type, protocol))
    elif len(sys.argv) > 1 and sys.argv[1] == "chart_cache_init":
        print(deployment.chart_cache_init(*sys.argv[2:]))
    else:
        from . import click_cli
        click_cli.main()

