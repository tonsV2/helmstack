# Helmstack

## Setup
```bash
virtualenv venv
source venv/bin/activate
pip install --editable .
```

## Stack file exmaple
```yaml
environments:
  dev:
    overlay:
      - env/dev.yaml
  prod:
    overlay:
      - env/prod.yaml

releases:
  - name: web-env
    namespace: web
    chart: chart/web-env

  - name: web-app
    namespace: web
    chart: chart/web-app

repositories:
  - name: chart
    url: https://chartmuseum.somewhere.dk

helmDefaults:
  recreatePods: true
  force: true
```

## Overlay example (env/dev.yaml)
```yaml
releases:
  web-env:
    version: 1.7.0
    enabled: true
  web-app:
    version: 1.39.0
    enabled: true
```

## TODO
### Bug?
Is it a bug the values can't start with "{{"?
https://bitbucket.org/ruamel/yaml/issues?status=new&status=open

### Write tests
So far this is a POC but tests should be written

### Skip repo's
Add flag --skip-repos
