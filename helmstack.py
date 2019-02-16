import click
import ruamel.yaml as yaml
import pprint


@click.command()
@click.option('--environment', '-e', default=None, help='Specify target environment')
@click.option('--file', '-f', type=click.File('r'), default='helmstack.yaml', help='Specify stack file')
@click.option('--debug', is_flag=True, help='Enable debug')
def cli(environment, file, debug):
    """This script run helm commands"""
    print("Environment: %s" % environment)
    print("Stack file: %s" % file.name)

    try:
        stack = yaml.safe_load(file)
        if debug:
            pprint.pprint(stack)
        handle_repositories(stack)
    except yaml.YAMLError as exc:
        print(exc)


def handle_repositories(stack):
    if stack['repositories']:
        for repository in stack['repositories']:
            helm("helm repo add %s %s" % (repository['name'], repository['url']))
        helm("helm repo update")


def helm(cmd):
    print(cmd)
