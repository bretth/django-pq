__version__ = '0.1'


def version_hook(config):
    config['metadata']['version'] = __version__