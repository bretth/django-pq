__version__ = '0.1pre'


def version_hook(config):
    config['metadata']['version'] = __version__