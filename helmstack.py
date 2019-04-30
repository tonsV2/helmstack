import collections.abc as collections_abc
import os
import pprint
import subprocess
import sys
import tempfile
from pathlib import Path

import click
import ruamel.yaml as yaml


class Config(object):
    def __init__(self):
        self.environment = None
        self.context = None
        self.helm_binary = None
        self.kubectl_binary = None
        self.file = None
        self.skip_repos = False
        self.debug = False
        self.dry_run = False
        self.stack = None
        self.overlay = None
        self.recreate_pods = False
        self.force = False
        self.keep_tmp_value_files = False
        self.garbage_files = []


config = Config()


def get_current_context():
    return subprocess.run([config.kubectl_binary, 'config', 'current-context'], stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip()


@click.group()
@click.option('--environment', '-e', default=None, help='Specify target environment')
@click.option('--context', '-c', default=None, help='kubectl context')
@click.option('--helm-binary', '-b', default='helm', help='Path to helm binary')
@click.option('--kubectl-binary', '-k', default='kubectl', help='Path to kubectl binary')
@click.option('--file', '-f', type=click.File('r'), default='helmstack.yaml', help='Specify stack file')
@click.option('--skip-repos', is_flag=True, help='Skip adding repositories')
@click.option('--debug', is_flag=True, help='Enable debug')
@click.option('--dry-run', is_flag=True, help='Don\'t execute commands')
def cli(environment, context, helm_binary, kubectl_binary, file, skip_repos, debug, dry_run):
    """This script run helm commands"""

    config.environment = environment
    config.context = context
    config.helm_binary = helm_binary
    config.kubectl_binary = kubectl_binary
    config.file = file
    config.skip_repos = skip_repos
    config.debug = debug
    config.dry_run = dry_run

    print("Environment: %s" % environment)
    print("Context: %s" % (context if context else get_current_context()))
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


def trim_releases(targets):
    def trim_ignored(stack):
        releases = [release for release in stack['releases'] if not release.get('ignore', False)]
        return releases

    def trim_non_targets(releases, targets):
        if len(targets):
            releases = [release for release in releases if release['name'] in targets]
        return releases

    stack = config.stack
    releases = trim_ignored(stack)
    releases = trim_non_targets(releases, targets)

    stack['releases'] = releases

    if config.debug:
        print("Trimmed stack:")
        pprint.pprint(config.stack)
    if not len(stack['releases']):
        print("WARNING: No releases found!")


@cli.command()
@click.option('--recreate-pods', is_flag=True, help='Recreate pods')
@click.option('--keep-tmp-value-files', is_flag=True, help='Don\'t clean up tmp value files')
@click.argument('targets', nargs=-1, default=None)
def sync(targets, recreate_pods, keep_tmp_value_files):
    """Synchronise one or more releases"""

    if recreate_pods:
        config.recreate_pods = recreate_pods

    config.keep_tmp_value_files = keep_tmp_value_files

    if config.environment:
        merge_overlays()

    trim_releases(targets)
    if not config.skip_repos:
        handle_repositories()

    for release in config.stack['releases']:
        transform_set_to_file(release)
        helm_upgrade(release)
    unlink_garbage_files()


def transform_set_to_file(release):
    if 'set' in release:
        set_file = to_file(release['set'])
        config.garbage_files.append(set_file)
        if 'values' in release:
            release['values'].append(set_file)
        else:
            release['values'] = [set_file]


# TODO: Not my proudest code. There will always be only one set file and therefor only one garbage file. Also the logic
#  for this is scattered all over this file
def unlink_garbage_files():
    if not config.keep_tmp_value_files:
        for file in config.garbage_files:
            os.unlink(file)
        config.garbage_files = []


@cli.command()
@click.option('--purge', is_flag=True, help='Purge releases')
@click.option('--all', is_flag=True, help='Confirm complete stack deletion')
@click.argument('targets', nargs=-1, default=None)
def delete(targets, purge, all):
    """Delete one or more releases"""

    if not targets and not all:
        exit_with_error("Can't delete entire stack without passing --all")

    if config.environment:
        merge_overlays()

    trim_releases(targets)
    for release in config.stack['releases']:
        helm_delete(release, purge)


def helm_delete(release, purge):
    cmd = config.helm_binary
    if config.context:
        cmd += " --kube-context %s" % config.context
    cmd += " delete"
    if purge:
        cmd += " --purge"
    if 'name' not in release:
        exit_with_error("Release missing name attribute")
    name = release['name']
    cmd += " %s" % name
    print("Deleting: %s" % name)
    sh_exec(cmd)


@cli.command()
@click.argument('targets', nargs=-1, default=None)
def get(targets):
    """Show actual resources present in the cluster"""

    if config.environment:
        merge_overlays()

    trim_releases(targets)
    for release in config.stack['releases']:
        helm_get(release)


def helm_get(release):
    cmd = config.helm_binary
    if config.context:
        cmd += " --kube-context %s" % config.context
    cmd += " get"
    if 'name' not in release:
        exit_with_error("Release missing name attribute")
    name = release['name']
    cmd += " %s" % name
    print("Getting: %s" % name)
    sh_exec(cmd)


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
    def dict_merge(left, right):
        """
        Inspiration: https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
        """
        for k, v in right.items():
            if isinstance(left.get(k), dict) and isinstance(v, collections_abc.Mapping):
                left[k] = dict_merge(left[k], v)
            else:
                left[k] = v
        return left

    def merge_values(overlay, release):
        release_values = []
        overlay_values = []
        if 'values' in release:
            release_values = release['values']
            del release['values']
        if 'values' in overlay:
            overlay_values = overlay['values']
            del overlay['values']
        release_values.extend(overlay_values)
        return release_values

    for release in releases:
        name = release['name']
        values = []
        if name in overlays:
            overlay = overlays[name]
            values = merge_values(overlay, release)
            dict_merge(release, overlay)
        if values:
            release['values'] = values


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


def to_file(value):
    fp = tempfile.NamedTemporaryFile(delete=False)
    if isinstance(value, str):
        fp.write(bytes(value, encoding='utf8'))
    else:
        dump = yaml.round_trip_dump(value, None, default_style='"')
        fp.write(bytes(dump, encoding='utf8'))
    return fp.name


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
            if not Path(value).is_file():
                exit_with_error("File not found: %s" % value)
            else:
                cmd += " --values %s" % value
    print("Upgrading: %s (%s)" % (name, chart))
    sh_exec(cmd)


def sh_exec(cmd):
    if config.debug:
        print("Command: %s" % cmd)
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


if __name__ == '__main__':
    cli()
