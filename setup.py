try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'Himlar command line tool',
    'author': 'Raymond Kristiansen',
    'url': 'https://github.com/norcams/himlarcli',
    'download_url': 'https://github.com/norcams/himlarcli',
    'author_email': 'raymond.kristiansen@uib.no',
    'version': '0.1',
    'install_requires': [],
    'packages': ['himlarcli'],
    'scripts': [],
    'name': 'himlarcli'
}

setup(**config)
