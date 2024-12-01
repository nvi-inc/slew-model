from setuptools import setup

setup(
    name='slew-model',
    packages=['slew', 'slew.database'],
    description='Compute azimuth and elevaltion slew rate and offset for VLBI antenna',
    version='1.1.0',
    url='http://github.com/',
    author='Mario Berube',
    author_email='mario.berube@nviinc.com',
    keywords=['vlbi', 'antenna'],
    install_requires=['sqlalchemy', 'numpy', 'scipy', 'matplotlib'],
    entry_points={
        'console_scripts': [
            'slew=slew.main:main'
        ]
    },
)
