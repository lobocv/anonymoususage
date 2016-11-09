__author__ = 'lobocv'

import os
from setuptools import setup
from anonymoususage import __version__


setup(
    name='anonymoususage',
    packages=['anonymoususage', 'anonymoususage.tables'],  # this must be the same as the name above
    version=__version__,
    description='Anonymously track user usage patterns and statistics.',
    author='Calvin Lobo',
    author_email='calvinvlobo@gmail.com',
    url='https://github.com/lobocv/anonymoususage',
    download_url='https://github.com/lobocv/anonymoususage/tarball/%s' % __version__,
    keywords=['logging', 'usage', 'tracking', 'statistics', 'anonymous'],
    classifiers=[],
    install_requires=['requests==2.8.1', 'cherrypy==8.1.2']
)
