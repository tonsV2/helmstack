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

    except yaml.YAMLError as exc:
        print(exc)
