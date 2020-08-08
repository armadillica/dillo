def new(**kwargs):
    if 'conf' in kwargs:
        conf_file = kwargs['conf']
        conf = open(conf_file).read().strip().splitlines()
    else:
        conf = []

    if 'vars' in kwargs:
        vars = kwargs['vars']
        for name, value in vars.items():
            conf.append('var ' + name + ' = ' + str(value))

    if 'source' in kwargs:
        source = kwargs['source']
        conf.append('set source = ' + source)

    if 'webhook' in kwargs:
        webhook = kwargs['webhook']
        conf.append('set webhook = ' + webhook)

    if 'outputs' in kwargs:
        outputs = kwargs['outputs']
        for format, cdn in outputs.items():
            conf.append('-> ' + format + ' = ' + cdn)

    new_conf = []
    new_conf += sorted(filter(lambda l: l.startswith('var'), conf))
    new_conf.append('')
    new_conf += sorted(filter(lambda l: l.startswith('set'), conf))
    new_conf.append('')
    new_conf += sorted(filter(lambda l: l.startswith('->'), conf))

    return "\n".join(new_conf)
