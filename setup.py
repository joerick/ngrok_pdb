from setuptools import setup

setup(
    name='ngrok_pdb',
    version='0.1',
    url='http://github.com/joerick/ngrok_pdb',
    packages=['ngrok_pdb'],
    package_data={
        'ngrok_pdb': ['resources/*'],
    },
    zip_safe=False,
)

