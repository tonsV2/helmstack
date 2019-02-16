import click
import ruamel.yaml as yaml
import pprint


@click.command()
@click.option('--environment', '-e', default=None, help='Specify target environment')
@click.option('--file', '-f', default='helmstack.yaml', help='Specify stack file')
@click.option('--debug', default=False, help='Enable debug')
def cli(environment, file, debug):
    """This script run helm commands"""
    print("Environment: %s" % environment)
    print("Stack file: %s" % file)

    with open(file, 'r') as stream:
        try:
            stack = yaml.safe_load(stream)
            if debug:
                pprint.pprint(stack)

        except yaml.YAMLError as exc:
            print(exc)
