from setuptools import setup, find_packages
setup(
    name='nga-binaural',
    description='Binaural NGA Renderer',
    version='1.0.0',
    license='MIT',
    long_description=open('README.md').read() + '\n' + open('CHANGELOG.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        'numpy~=1.14',
        'pydub~=0.23.1',
        'scipy~=1.0',
        'ear~=2.0.0',
        'h5py==2.10.0'
    ],
    packages=find_packages(),
    package_data={
         "nga_binaural": ["data/*"],
    },
    entry_points={
        'console_scripts': [
            'nga-binaural = nga_binaural.cmdline:render_file',
        ]
    },
)