import click


@click.command()
@click.option('--environment', '-e', default=None, help='Specify target environment')
@click.option('--file', '-f', default='helmstack.yaml', help='Specify stack file')
def cli(environment):
    print("Environment: %s" % environment)
    print("Stack file: %s" % environment)
