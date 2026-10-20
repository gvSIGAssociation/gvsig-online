from setuptools import setup, find_packages

VERSION = '0.0.1' 
DESCRIPTION = 'Example Python package'
LONG_DESCRIPTION = 'Example Python package long description'

# Setting up
setup(
       # the name must match the folder name 'verysimplemodule'
        name="gvsigol_plugin_sampleapi", 
        version=VERSION,
        author="jvhigon",
        author_email="<jvhigon@scolab.es>",
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        packages=find_packages(),
        install_requires=[], # add any additional packages that 
        # needs to be installed along with your package. Eg: 'caer'
        
        keywords=['python', 'sample'],
        classifiers= [
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Not defined",            
            "Programming Language :: Python :: 3",
            "Operating System :: Linux",            
        ]
)