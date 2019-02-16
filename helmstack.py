import click
import ruamel.yaml as yaml
import pprint


class Config(object):
    def __init__(self):
        self.environment = None
        self.context = None
        self.helm_binary = None
        self.file = None
        self.debug = False
        self.stack = None
        self.overlay = None
        self.recreate_pods = False
        self.force = False


config = Config()


@click.command()
@click.option('--environment', '-e', default=None, help='Specify target environment')
@click.option('--context', '-c', default=None, help='kubectl context')
@click.option('--helm-binary', '-b', default='helm', help='Path to helm binary')
@click.option('--file', '-f', type=click.File('r'), default='helmstack.yaml', help='Specify stack file')
@click.option('--debug', is_flag=True, help='Enable debug')
def cli(environment, context, helm_binary, file, debug):
    """This script run helm commands"""

    config.environment = environment
    config.context = context
    config.helm_binary = helm_binary
    config.file = file
    config.debug = debug

    print("Environment: %s" % environment)
    print("Context: %s" % context)
    print("Stack file: %s" % file.name)

    try:
        stack = yaml.safe_load(file)
        if debug:
            print("Stack:")
            pprint.pprint(stack)
        config.stack = stack
    except yaml.YAMLError as exc:
        print(exc)

    if config.stack['helmDefaults']:
        if config.stack['helmDefaults']['recreatePods']:
            config.recreate_pods = config.stack['helmDefaults']['recreatePods']

    handle_repositories()
    merge_overlays()
    sync_releases()


def sync_releases():
    for release in config.stack['releases']:
        if 'enabled' in release and release['enabled']:
            helm(release)


def merge_overlays():
    if not config.environment:
        raise Exception("Environment not specified!")
    overlay_files = config.stack['environments'][config.environment]['overlay']
    for overlay_file in overlay_files:
        with open(overlay_file, 'r') as stream:
            try:
                config.overlay = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        if config.debug:
            print("Overlay:")
            pprint.pprint(config.overlay)
        merge(config.stack['releases'], config.overlay['releases'])
        if config.debug:
            print("Merged stack:")
            pprint.pprint(config.stack)


def merge(releases, overlays):
    for release in releases:
        name = release['name']
        release_overlay = overlays[name]
        for k in release_overlay:
            release[k] = release_overlay[k]


def handle_repositories():
    stack = config.stack
    if stack['repositories']:
        for repository in stack['repositories']:
            sh_exec("%s repo add %s %s" % (config.helm_binary, repository['name'], repository['url']))
        sh_exec("%s repo update" % config.helm_binary)


def sh_exec(cmd):
    print(cmd)


def helm(release):
    cmd = config.helm_binary
    if config.context:
        cmd += " --kube-context %s" % config.context
    cmd += " upgrade"
    if 'name' not in release:
        raise Exception("Release missing name attribute")
    cmd += " %s" % release['name']
    if 'chart' not in release:
        raise Exception("Release missing chart attribute")
    cmd += " %s" % release['chart']
    if 'namespace' in release:
        cmd += " --namespace %s" % release['namespace']
    if 'version' in release:
        cmd += " --version %s" % release['version']
    if config.recreate_pods:
        cmd += " --recreate-pods"
    if config.force:
        cmd += " --force"
    cmd += " --install"
    if config.debug:
        print("Helm command: %s" % cmd)
    sh_exec(cmd)
