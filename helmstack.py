import pprint
import subprocess
import sys

import click
import ruamel.yaml as yaml


class Config(object):
    def __init__(self):
        self.environment = None
        self.context = None
        self.helm_binary = None
        self.file = None
        self.debug = False
        self.dry_run = False
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
@click.option('--dry-run', is_flag=True, help='Don\'t execute commands')
def cli(environment, context, helm_binary, file, debug, dry_run):
    """This script run helm commands"""

    config.environment = environment
    config.context = context
    config.helm_binary = helm_binary
    config.file = file
    config.debug = debug
    config.dry_run = dry_run

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
        if config.stack['helmDefaults']['force']:
            config.force = config.stack['helmDefaults']['force']

    handle_repositories()
    if config.environment:
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
            name = repository['name']
            url = repository['url']
            print("Adding repo %s %s" % (name, url))
            sh_exec("%s repo add %s %s" % (config.helm_binary, name, url))
            print("Repository added!")
        sh_exec("%s repo update" % config.helm_binary)


def helm(release):
    cmd = config.helm_binary
    if config.context:
        cmd += " --kube-context %s" % config.context
    cmd += " upgrade"
    if 'name' not in release:
        raise Exception("Release missing name attribute")
    name = release['name']
    cmd += " %s" % name
    if 'chart' not in release:
        raise Exception("Release missing chart attribute")
    chart = release['chart']
    cmd += " %s" % chart
    if 'namespace' in release:
        cmd += " --namespace %s" % release['namespace']
    if 'version' in release:
        cmd += " --version %s" % release['version']
    if config.recreate_pods:
        cmd += " --recreate-pods"
    if config.force:
        cmd += " --force"
    cmd += " --install"
    if 'values' in release:
        for value in release['values']:
            cmd += " --values %s" % value
    print("Upgrading: %s (%s)" % (name, chart))
    sh_exec(cmd)


def sh_exec(cmd):
    if config.debug:
        print("Shell command: %s" % cmd)
    if config.dry_run:
        return
    p = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE)
    while True:
        out = p.stderr.read(1)
        if out == b'' and p.poll() is not None:
            break
        if out != b'':
            sys.stdout.buffer.write(out)
            sys.stdout.flush()
    if p.returncode != 0:
        raise Exception("None zero return code")
