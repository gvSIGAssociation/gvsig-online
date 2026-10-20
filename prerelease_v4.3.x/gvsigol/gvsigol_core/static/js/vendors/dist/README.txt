Compressed gvsigol JS dependencies
==================================

JS files in this folder as generated using jsbuild for a subset of libraries, using the following commands:

source ~/virtualenvs/gvsigonline/bin/activate
pip install jstools==1.0
cd $WORKSPACE/gvsigol/build
mkdir -p ../gvsigol_core/static/js/vendors/dist ; jsbuild -v -o ../gvsigol_core/static/js/vendors/dist  deps-js.cfg 
