from ruamel import yaml
import click


@click.group()
def main():
    pass


@click.group()
def deployment():
    pass


main.add_command(deployment)


@deployment.command()
@click.argument('NAMESPACE_NAME')
@click.argument('DEPLOYMENT_TYPE', default='minio')
def get_health(**kwargs):
    from .deployment import get_health
    print(yaml.safe_dump(get_health(**kwargs), default_flow_style=False))
