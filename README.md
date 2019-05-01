# Helmstack

Helmstack is heavily inspired by [helmfile](https://github.com/roboll/helmfile).

helmfile is a great project and way more advanced than helmstack. But I found it difficult to use when dealing with multiple chart versions spanning different environments.

The idea behind helmstack is that you have a basic stack file for which you use overlays to handle different versions in different environments.
Thus making it easy to deal with having one version in dev, another in test and disabling the same chart in prod.

## Install
```bash
pip install helmstack
```

## Stack file example

Default stack file is `stackfile.yaml`
```yaml
releases:
  - name: web-env
    namespace: web
    chart: chart/web-env
    values:
      - web-env.yaml
    set:
      some: value
      yet:
        another: value

  - name: web-app
    namespace: web
    chart: chart/web-app

environments: # Optional
  dev:
    overlay:
      - env/dev.yaml
  prod:
    overlay:
      - env/prod.yaml

repositories: # Optional
  - name: chart
    url: https://chartmuseum.somewhere.dk

helmDefaults: # Optional
  recreatePods: true
  force: true
```

## Overlay example (env/dev.yaml)
```yaml
releases:
  web-env:
    version: 1.7.0
    set:
      some: new-value
  web-app:
    version: 1.39.0
    ignore: true
```

## Commands
The following commands are supported by helmstack.

### Sync
The ```sync``` command synchronizes everything in the stack file against the cluster

Zero or more releases can be listed as arguments

### Delete
The ```sync``` command deletes one or more releases from the cluster,

Zero or more releases can be listed as arguments


### Get
The ```sync``` command returns the json resource ofr one or more releases from the cluster,

Zero or more releases can be listed as arguments


## Development setup
```bash
virtualenv venv
source venv/bin/activate
pip install --editable .
```

## Release
```bash
python setup.py sdist bdist_wheel
python -m twine upload dist/*
```

## TODO

### Write tests
So far this is a POC but tests should be written

### Environment varialbes
Support .env files and regular environment variables

### Templating
Support some sort of templating language... Maybe

### s/overlay/overlays/ ?
Either stop supporting multiple overlay files or rename key to overlays

### Support referencing charts by urls... git urls

### .helmstack file for defaults
environment: dev
context: ml-dev
some: thing

### Stacks?
stacks:
 - name: sud
   url: git...
 - name: elk
   url: git...

### Support multiple stack files?
helmstack ... -f elk.yaml -f whoami.yaml sync

### values.yaml.gotmpl
Parse *.yaml.gotmpl files and use the output as value files
This could be handy when inlining xml, certs and other kind of files

https://github.com/powerman/gotmpl
https://github.com/subfuzion/envtpl

### Variables?
variables:
  name: value

And then use the above as ${name}?
