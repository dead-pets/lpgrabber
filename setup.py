#!/usr/bin/env python

PROJECT = 'lpgrabber'

VERSION = '0.1'

from setuptools import find_packages
from setuptools import setup

try:
    long_description = open('README.rst', 'rt').read()
except IOError:
    long_description = ''

setup(
    name=PROJECT,
    version=VERSION,

    description='Yet another stats collector for Launchpad',
    long_description=long_description,

    author='Dmitry Pyzhov',
    author_email='dpyzhov@mirantis.com',

    url='https://github.com/dmi-try/lpgrabber',
    download_url='https://github.com/dmi-try/lpgrabber/tarball/master',

    classifiers=['Development Status :: 3 - Alpha',
                 'License :: OSI Approved :: Apache Software License',
                 'Programming Language :: Python',
                 'Environment :: Console',
                 ],

    platforms=['Any'],

    scripts=[],

    provides=[],
    install_requires=['cliff', 'pandas', 'launchpadlib'],

    namespace_packages=[],
    packages=find_packages(),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'lpgrabber = lpgrabber.main:main'
        ],
        'lpgrabber.app': [
            'simple = lpgrabber.simple:Simple',
            'two_part = lpgrabber.simple:Simple',
            'error = lpgrabber.simple:Error',
            'list files = lpgrabber.list:Files',
            'files = lpgrabber.list:Files',
            'file = lpgrabber.show:File',
            'show file = lpgrabber.show:File',
            'unicode = lpgrabber.encoding:Encoding',
            'teams = lpgrabber.teams:Teams',
            'bugs = lpgrabber.bugs:Bugs',
        ],
    },

    zip_safe=False,
)
