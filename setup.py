__author__ = 'lobocv'

from distutils.core import setup
from anonymoususage import __version__

setup(
    name='anonymoususage',
    packages=['anonymoususage'],  # this must be the same as the name above
    version=__version__,
    description='Anonymously track user usage patterns and statistics.',
    author='Calvin Lobo',
    author_email='calvinvlobo@gmail.com',
    url='https://github.com/lobocv/anonymoususage',
    download_url='https://github.com/lobocv/anonymoususage/tarball/%s' % __version__,
    keywords=['logging', 'usage', 'tracking', 'statistics', 'anonymous'],
    classifiers=[],
)
