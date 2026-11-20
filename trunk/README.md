# gvsig-online

gvSIG Online is a platform for the publication and management of geographic information, by providing 
an integrated interface for publishing new layers, defining symbology, creating new mapviewers and defining
permissions for each published resource. gvSIG Online is a web application written in Python using the
Django framework. It integrates with Geoserver and optionally also with Geonetwork.

gvSIG Online has been developed by [Scolab](http://www.scolab.es) and the [gvSIG Association](http://www.gvsig.com/) and it is available under the [Affero GPL license](https://www.gnu.org/licenses/agpl.html).

## User documentation

The [user manual](https://demo.gvsigonline.com/gvsigonline/core/documentation/) is available online in our 
[demo server](https://demo.gvsigonline.com/gvsigonline). It is generated from the sources contained
under the [docs subfolder](https://github.com/gvSIGAssociation/gvsig-online/tree/master/docs).

There is also a number of online presentations and videos about the gvSIG Online platform and how it has been
applied for very different scenarios and organization types:
* [gvSIG Online: solution for SDI in Open Source software](https://www.youtube.com/watch?v=mM6QPZmg92M) (1st gvSIG Festival)
* [Emergency management and prevention with gvSIG Online](https://www.youtube.com/watch?v=XgQqhmt66n8) (3rd gvSIG Festival)
* [gvSIG Online, la plataforma de infraestructura de datos espaciales y SIG corporativo en software libre (Spanish)](https://www.youtube.com/watch?v=47rEuQtAnaA)
* [Herramientas de gestión de gvSIG Online (Spanish)](https://www.youtube.com/watch?v=IOjsMA8iEdU)
* [gvSIG Online: la solución gvSIG para Infraestructuras de Datos Espaciales (Spanish)](https://www.youtube.com/watch?v=pfb_KlI3n8o) (11as Jornadas Int. gvSIG)

## Installing

Warning: this section is a work in progress.

gvSIG Online has been tested on CentOS 7 and Debian 8.

### Downloading the code:

```shell
cd $INSTALL_DIR
git clone https://github.com/gvSIGAssociation/gvsig-online.git
cd gvsigol
# include the default styles and welcome page
ln -s ../app_dev/gvsigol_app_dev
# include edition plugin
ln -s ../plugin_edition/gvsigol_plugin_edition
# do a ln -s for each plugin you want to use
```

### Dependencies

The following libraries must be installed:

```shell
sudo aptitude install python-dev libxml2 libxml2-dev libxslt-dev
```
(The command above is valid for Debian 8).

gvSIG Online requires Geoserver and Postgres (with PostGIS) to be installed on the system.
LDAP is not mandatory, but it makes gvSIG Online much more useful.
Please refer to the documentation of these projects to install them.

### Creating a Python virtual env

```shell
sudo aptitude install python-virtualenv virtualenvwrapper python-pip
cd /home/user
mkdir virtualenvs
cd virtualenvs
virtualenv gvsigonline
```
These commands will create a virtual env in the path `/home/user/virtualenvs/gvsigonline`.
Now we need to activate the virtual env.

```shell
cd /home/user/virtualenvs/gvsigonline
source bin/activate
```
Then we can start installing the Python dependencies:

```shell
cd $INSTALL_DIR/gvsig-online
pip install -r requirements.txt
```

Next, we need to configure some settings, by creating a `settings_passwords.py` file:

```shell
cd $INSTALL_DIR/gvsig-online/gvsigol/gvsigol
cat > settings_passwords.py << EOF
BING_KEY_DEVEL=''
DB_USER_DEVEL='yourdbuser'
DB_PW_DEVEL='yourdbpass'
LDAP_USER_DEVEL='cn=yourbinduser,dc=yoursubdomain,dc=yourdomain,dc=com'
LDAP_PW_DEVEL='yourldappass'
GEOSERVER_USER_DEVEL='admin'
GEOSERVER_PW_DEVEL='yourgeoserverpass'
EOF
```
Then, edit `settings.py` to decide which Django applications and gvSIG plugins must be enabled
(`INSTALLED_APPS` is your friend). Depending on your particular installation, you might need to
customize some additiona properties, such as your database host and port.

Finally, we need to apply Django migrations to create the DB structure. 
This has to be done every time gvSIG Online is updated (if there is any change on the data model).

```shell
cd $INSTALL_DIR/gvsig-online
manage.py migrate
```

### Execution: development and production

gvSIG Online can be executed from Eclipse PyDev plugin as a PyDev Django application.

In production, it is usually executed using [uWSGI application server](https://uwsgi-docs.readthedocs.io/en/latest/)
combined with Apache and Tomcat (Geoserver).

## Professional support and gvSIG Online in the cloud 

The [gvSIG Association](http://www.gvsig.com/) provides gvSIG Online hosting and maintenance services:
* SaaS: software as a service (hosting+maintenance)
* In Situ: installation on client server(s)

It also offers professional services for develoment of additional plugins and customizations. Please contact
us at info@gvsig.com for additional information.


