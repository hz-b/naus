from setuptools import setup #, find_packages
desc = '''naus: ship. A utilitly to explore an environment using bluesky
'''
setup(
    #full_name = "Berlin accelerator commissioning tools: BESSY II device information",
    name = "naus",
    version = "0.0.0",
    author = "Pierre Schnizer",
    author_email= "pierre.schnizer@helmholtz-berlin.de",
    description = desc,
    license = "GPL",
    keywords = "keras, bluesky",
    url="https://github.com/hz-b/naus",
    packages = ['naus'],
    
    classifiers = [
        "Development Status :: 2 - Pre - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Informatics",
    ]
)
