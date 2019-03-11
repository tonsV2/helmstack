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
        self.skip_repos = False
        self.debug = False
        self.dry_run = False
        self.stack = None
        self.overlay = None
        self.recreate_pods = False
        self.force = False


config = Config()


@click.group()
@click.option('--environment', '-e', default=None, help='Specify target environment')
@click.option('--context', '-c', default=None, help='kubectl context')
@click.option('--helm-binary', '-b', default='helm', help='Path to helm binary')
@click.option('--file', '-f', type=click.File('r'), default='helmstack.yaml', help='Specify stack file')
@click.option('--skip-repos', is_flag=True, help='Skip adding repositories')
@click.option('--debug', is_flag=True, help='Enable debug')
@click.option('--dry-run', is_flag=True, help='Don\'t execute commands')
def cli(environment, context, helm_binary, file, skip_repos, debug, dry_run):
    """This script run helm commands"""

    config.environment = environment
    config.context = context
    config.helm_binary = helm_binary
    config.file = file
    config.skip_repos = skip_repos
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

    stack = config.stack
    if 'helmDefaults' in stack:
        helm_defaults = stack['helmDefaults']
        if helm_defaults:
            if 'recreatePods' in helm_defaults:
                config.recreate_pods = helm_defaults['recreatePods']
            if 'force' in helm_defaults:
                config.force = helm_defaults['force']

    if config.environment:
        merge_overlays()


def trim_releases(targets):
    if len(targets):
        stack = config.stack
        releases = stack['releases']
        stack['releases'] = [release for release in releases if release['name'] in targets]
        if config.debug:
            print("Trimmed stack:")
            pprint.pprint(config.stack)


@cli.command()
@click.option('--recreate-pods', is_flag=True, help='Recreate pods')
@click.argument('targets', nargs=-1, default=None)
def sync(targets, recreate_pods):
    """Synchronise everything listed in the state file"""
    config.recreate_pods = recreate_pods

    trim_releases(targets)
    if not config.skip_repos:
        handle_repositories()

    for release in config.stack['releases']:
        if ('ignore' in release and not release['ignore']) or 'ignore' not in release:
            helm_upgrade(release)


@cli.command('template')
def template():
    """Locally render templates"""
    exit_with_error("Not implemented yet")


def merge_overlays():
    if 'environments' not in config.stack:
        exit_with_error("No environments found!")
    environment = config.environment
    environments = config.stack['environments']
    if environment not in environments:
        exit_with_error("Environment '%s' not found!" % environment)
    if 'overlay' not in environments[environment]:
        exit_with_error("No overlay found in environment '%s'!" % environment)
    overlay_files = environments[environment]['overlay']
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
        if name in overlays:
            release_overlay = overlays[name]
            for k in release_overlay:
                release[k] = release_overlay[k]


def handle_repositories():
    stack = config.stack
    if 'repositories' in stack:
        for repository in stack['repositories']:
            name = repository['name']
            url = repository['url']
            print("Adding repo %s %s" % (name, url))
            sh_exec("%s repo add %s %s" % (config.helm_binary, name, url))
            print("Repository added!")
        sh_exec("%s repo update" % config.helm_binary)


def helm_upgrade(release):
    cmd = config.helm_binary
    if config.context:
        cmd += " --kube-context %s" % config.context
    cmd += " upgrade"
    if 'name' not in release:
        exit_with_error("Release missing name attribute")
    name = release['name']
    cmd += " %s" % name
    if 'chart' not in release:
        exit_with_error("Release missing chart attribute")
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
        exit_with_error("Helm returned non-zero return code")


def exit_with_error(err_msg):
    sys.exit("Error: %s" % err_msg)
