from gvsigol_services.models import Layer, Server
#from gvsigol_services.utils import _get_user
from gvsigol_auth.auth_backend import get_roles, to_provider_rolename, get_admin_role, get_all_roles
from django.contrib.auth.models import AnonymousUser, User
from .models import LayerReadRole, LayerWriteRole, LayerManageRole, LayerGroupRole, LayerGroup
from gvsigol_services import geographic_servers
from gvsigol_services import apps as gvsigol_services_apps
import logging

LOGNAME = 'gvsigol'

"""
Shortcut authorization server for classic deployments which use PlainAuthorizationService,
to improve performance for the typical use case
"""
AUTHZ_SERVER_CACHE = {}

def shortcut_authz_server():
    """
    Shorcut authz service instance when using PlainAuthorizationService which
    does not require any server-specific config
    """
    from gvsigol_services.models import Server
    if Server.objects.filter(authz_service_conf__isnull=False).exists():
        AUTHZ_SERVER_CACHE['instance'] = None
    else:
        from gvsigol_services.authorization import PlainAuthorizationService
        AUTHZ_SERVER_CACHE['instance'] = PlainAuthorizationService()

def get_authz_servers():
    """
    This is a hack to avoid performance penalties in the most common use
    case where gs-acl is not used
    """
    if not 'instance' in AUTHZ_SERVER_CACHE:
        shortcut_authz_server()
    instance = AUTHZ_SERVER_CACHE.get('instance')
    if instance:
        return [instance]
    else:
        authz_servers = []
        for server in Server.objects.all():
            gs = geographic_servers.get_instance().get_server_by_id(server.id)
            authz_servers.append(gs.getAuthorizationService())
        return authz_servers

def get_authz_server_for_layer(layer):
    if not 'instance' in AUTHZ_SERVER_CACHE:
        shortcut_authz_server()
    instance = AUTHZ_SERVER_CACHE.get('instance')
    if instance:
        return instance
    else:
        if not isinstance(layer, Layer):
            try:
                layer = Layer.objects.select_related("datastore__workspace__server").get(id=layer)
            except:
                # for external layers
                layer = Layer.objects.get(id=layer)
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        return gs.getAuthorizationService()

def _get_user(request_or_user):
    if isinstance(request_or_user, User):
        return request_or_user
    elif isinstance(request_or_user, str):
        return User.objects.get(username=request_or_user)
    else:
        return request_or_user.user

def can_use_layergroup(request_or_user, layergroup, permission):
    """
    Checks whether the user has permissions to manage the provided layergroup.
    It accepts a layergroup instance or a layergroup id.

    Parameters
    ----------
    request_or_user: Request | HttpRequest | User | str
        A Django Request object | A DRF HttpRequest object | A Django User object | A username
    layergroup: LayerGroup | int
        A Django LayerGroup instance or a LayerGroup id
    permission: str
        The permission to check for the user and layergroup
    """
    try:
        user = _get_user(request_or_user)
        if not isinstance(layergroup, LayerGroup):
            layergroup = LayerGroup.objects.get(id=layergroup)
        if user.is_superuser:
            return True
        if layergroup.created_by == user.username:
            return True
        elif user.is_staff:
            if layergroup.name == "__default__":
                return True
            user_roles = get_roles(request_or_user)
            return layergroup.layergrouprole_set.filter(permission=permission, role__in=user_roles).exists()
    except Exception as e:
        print(e)
    return False

"""
AQUÍ ME QUEDO 2024/10/04
Pensar responsabilidades para método set_layer_data_rules:
    def set_layer_data_rules(self, layer, read_roles, write_roles):
¿ debe llamar internamente al AuthorizationService para que se establezcan según el plugin que toca?
--> entonces crearemos una dependencia de PlainAuthorizationService sobre backend_geoserver => analizar si es problematico
¿crear API extra para definir los LayerLimits? ¿siguiendo modelo de GS-ACL o con más abstracción?
--> pensar cómo se establecen actualmente set_data_rules y cómo lo transladaríamos a la implementación con GS-ACL
--> revisar si todo funcionaría como conceptualmente había pensado

"""
class PlainAuthorizationService():
    def __init__(authn_server_conf):
        pass
    
    def get_write_restrictions(self, request_or_user, layer_id):
        """
        Sample output:
        {
            "grant" : "ALLOW",
            "catalogMode" : "CHALLENGE",
            "cqlFilterRead" : "(tipo_estfc=5) OR (tipo_estfc=3)",
            "cqlFilterWrite" : "(tipo_estfc=5) OR (tipo_estfc=3)",
            "attributes" : [ {
                "name" : "cod_est",
                "dataType" : "String",
                "access" : "READONLY" 
            }, {
                "name" : "estadofisd",
                "dataType" : "String",
                "access" : "READWRITE" 
            }, {
                "name" : "fecha_alta",
                "dataType" : "Date",
                "access" : "READONLY" 
            }, {
                "name" : "tipo_estfc",
                "dataType" : "integer",
                "access" : "NONE" 
            }
        }
        """
        try:
            if self.can_write_layer(request_or_user, layer_id):
                return {
                    "grant" : "ALLOW",
                    "catalogMode" : "CHALLENGE"
                }
        except Exception as e:
            print(e)
        return {
            "grant" : "DENY",
            "catalogMode" : "CHALLENGE"
        }

    def get_read_restrictions(self, request_or_user, layer_id):
        """
        Sample output:
        {
            "grant" : "ALLOW",
            "catalogMode" : "CHALLENGE",
            "cqlFilterRead" : "(tipo_estfc=5) OR (tipo_estfc=3)",
            "attributes" : [ {
                "name" : "cod_est",
                "dataType" : "String",
                "access" : "READONLY" 
            }, {
                "name" : "estadofisd",
                "dataType" : "String",
                "access" : "READWRITE" 
            }, {
                "name" : "fecha_alta",
                "dataType" : "Date",
                "access" : "READONLY" 
            }, {
                "name" : "tipo_estfc",
                "dataType" : "integer",
                "access" : "NONE" 
            }
        }
        """
        # comparar con utils.can_write_layer(request_or_user, layer)
        # y utils.can_read_layer(request_or_user, layer)

        # pensar modelo:
        # - obtener restricciones cql (útil para el API)
        # VS
        # - ¿puedo leer o escribir la feature x? Por ejemplo para views.upload_resources
        try:
            if self.can_read_layer(request_or_user, layer_id):
                return {
                    "grant" : "ALLOW",
                    "catalogMode" : "CHALLENGE"
                }
        except Exception as e:
            print(e)
        return {
            "grant" : "DENY",
            "catalogMode" : "CHALLENGE"
        }

    def can_read_layer(self, request_or_user, layer):
        """
        Checks whether the user has permissions to read the provided layer.

        Parameters
        ----------
        request_or_user: Request | HttpRequest | User | str
            A Django Request object | A DRF HttpRequest object | A Django User object | A username
        layer: Layer | int
            A Django Layer instance or a layer id
        """
        try:
            if not isinstance(layer, Layer):
                layer = Layer.objects.get(id=layer)
            if layer.public:
                return True
            user = _get_user(request_or_user)
            if  user.is_superuser:
                return True
            if isinstance(user, AnonymousUser):
                return False
            roles = get_roles(request_or_user)
            return LayerReadRole.objects.filter(layer=layer, role__in=roles).exists()
        except Exception as e:
            print(e)
        return False

    def can_read_feature(self, request, layer, feature):
        try:
            return self.can_read_layer(request, layer)
        except Layer.DoesNotExist:
            # TODO
            pass

    def can_write_layer(self, request_or_user, layer):
        """
        Checks whether the user has permissions to write the provided layer.

        Parameters
        ----------
        request_or_user: Request | HttpRequest | User | str
            A Django Request object | A DRF HttpRequest object | A Django User object | A username
        layer: Layer | int
            A Django Layer instance or a layer id
        """
        try:
            user = _get_user(request_or_user)
            if user.is_superuser:
                return True
            if isinstance(user, AnonymousUser):
                return False
            if not isinstance(layer, Layer):
                layer = Layer.objects.get(id=layer)
            roles = get_roles(request_or_user)
            return LayerWriteRole.objects.filter(layer=layer, role__in=roles).exists()
        except Exception as e:
            print(e)
        return False

    def can_write_feature(self, request, layer, feature_id, geojson_feature):
        try:
            return self.can_write_layer(request, layer)
        except Layer.DoesNotExist:
            # TODO
            pass

    def can_create_feature(self, request, layer, geojson_feature):
        try:
            return self.can_write_layer(request, layer)
        except Layer.DoesNotExist:
            # TODO
            pass

    def get_readable_feature_ids(self, request, layer):
        """
        Returns a list of the PK values (ids) for the readable features
        of the layer for the authenticated user  (i.e. all the features
        are readable for the user), or None if there are no
        restrictions on the layer
        """
        if self.can_read_layer(request, layer):
            return None
        return []

    def _set_data_rules(self, server):
        """
        (Re)Sets data rules in Geoserver for all layers, based on gvSIG Online
        permissions
        """
        layers = Layer.objects.filter(external=False, datastore__workspace__server=server)
        for layer in layers:
            read_roles = LayerReadRole.objects.filter(layer=layer).values_list('role', flat=True).distinct()
            self.set_layer_read_rules(layer, read_roles)

            write_roles = LayerWriteRole.objects.filter(layer=layer).values_list('role', flat=True).distinct()
            self.set_layer_write_rules(layer, write_roles)
        self._setWfsTransactionRules(server)

    def set_data_rules(self):
        """
        (Re)Sets data rules in Geoserver for all layers, based on gvSIG Online
        permissions
        """
        for s in Server.objects.all():
            self._set_data_rules(s)

    def set_layer_data_rules(self, layer, read_roles=None, write_roles=None, set_transaction_rules=True):
        """
        (Re)sets data rules in Geoserver for the provided layer, based in the
        provided read and write roles and whether layer is public
        """
        if read_roles is not None:
            self.set_layer_read_rules(layer, read_roles)
        if write_roles is not None:
            self.set_layer_write_rules(layer, write_roles)
            if set_transaction_rules:
                self._setWfsTransactionRules(layer.datastore.workspace.server)
    
    def set_layer_read_rules(self, layer, read_roles):
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        url = gs.rest_catalog.get_service_url() + "/security/acl/layers.json"
        if layer.public:
            who_can_read = [ "*" ]
        else:
            geoserver_admin_role = to_provider_rolename(get_admin_role(), provider='geoserver')
            if len(read_roles) > 0:
                who_can_read = [ to_provider_rolename(g, provider="geoserver") for g in read_roles]
                if not geoserver_admin_role in who_can_read:
                    who_can_read.append(geoserver_admin_role)
            else:
                who_can_read = [ geoserver_admin_role ]
        who_can_read = set(who_can_read)
        read_rule_path = layer.datastore.workspace.name + "." + layer.name + ".r"
        read_rule_roles = ",".join(who_can_read)
        data = { read_rule_path: read_rule_roles}
        # try to modify the rule
        result = gs.rest_catalog.get_session().put(url, json=data, verify=False, auth=(gs.user, gs.password))
        if result.status_code == 409:
            # If modifying failed, try to add the rule.
            # We could delete and then add, but it is safer in this way (the layer remains protected in every instant)
            # It also safe if the geoserver/gvsigol rules get incoherent
            result = gs.rest_catalog.get_session().post(url, json=data, verify=False, auth=(gs.user, gs.password))
    
    def set_layer_write_rules(self, layer, write_roles):
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        url = gs.rest_catalog.get_service_url() + "/security/acl/layers.json"
        who_can_write = [ to_provider_rolename(g, provider="geoserver") for g in write_roles ]
        admin_role = to_provider_rolename(get_admin_role(), provider='geoserver')
        if admin_role not in who_can_write:
            who_can_write.append(admin_role)
        who_can_write = set(who_can_write)
        write_rule_path = layer.datastore.workspace.name + "." + layer.name + ".w"
        # now add the rule if necessary
        if len(who_can_write)>0:
            write_rule_roles =  ",".join(who_can_write)
            data = { write_rule_path: write_rule_roles}
            # try to modify the rule
            result = gs.rest_catalog.get_session().put(url, json=data, verify=False, auth=(gs.user, gs.password))
            if result.status_code == 409:
                # If modifying failed, try to add the rule.
                # We could delete and then add, but it is safer in this way (the layer remains protected in every instant)
                # It also safe if the geoserver/gvsigol rules get incoherent 
                result = gs.rest_catalog.get_session().post(url, json=data, verify=False, auth=(gs.user, gs.password))
        else:
            # clean any existing write rule for the layer 
            gs.rest_catalog.get_session().delete(gs.rest_catalog.get_service_url() + "/security/acl/layers/" + write_rule_path, verify=False, auth=(gs.user, gs.password))
    
    def _setWfsTransactionRules(self, server):
        write_roles = LayerWriteRole.objects.filter(layer__datastore__workspace__server=server, layer__external=False).values_list('role', flat=True).distinct()
        gs = geographic_servers.get_instance().get_server_by_id(server.id)
        #write_roles = LayerWriteRole.objects.all().values_list('role', flat=True).distinct()
        transaction_roles = [ to_provider_rolename(role, provider="geoserver") for role in write_roles ]
        if  len(transaction_roles) > 0:
            services_url = gs.rest_catalog.get_service_url() + "/security/acl/services.json"
            service = {}
            service_write_roles =  ",".join(transaction_roles)
            service['wfs.Transaction'] = service_write_roles
            result = gs.rest_catalog.get_session().put(services_url, json=service, verify=False, auth=(gs.user, gs.password))
            if result.status_code == 409:
                gs.rest_catalog.get_session().post(services_url, json=service, verify=False, auth=(gs.user, gs.password))

    def setWfsTransactionRules(self):
        for s in Server.objects.all():
            self._setWfsTransactionRules(s)

    def delete_layer_rules(self, layer):
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        url = gs.rest_catalog.get_service_url() + "/security/acl/layers/"
        read_rule_path = layer.datastore.workspace.name + "." + layer.name + ".r"
        gs.rest_catalog.get_session().delete(url + read_rule_path, verify=False, auth=(gs.user, gs.password))
        write_rule_path = layer.datastore.workspace.name + "." + layer.name + ".w"
        gs.rest_catalog.get_session().delete(url + write_rule_path, verify=False, auth=(gs.user, gs.password))
        self.setWfsTransactionRules()

    def set_layer_permissions(self, layer, is_public, assigned_read_roles, assigned_write_roles, assigned_manage_roles):
        layer.public = is_public
        layer.save()
        admin_role = get_admin_role()
        assigned_read_roles.append(admin_role)
        if layer.type.startswith('c_'):
            assigned_write_roles = []
        else:
            assigned_write_roles.append(admin_role)

        read_roles = []
        write_roles = []

        LayerReadRole.objects.filter(layer=layer, external=False).delete()
        all_roles = get_all_roles()
        for role in assigned_read_roles:
            try:
                if role in all_roles:
                    try:
                        lyr_read_role = LayerReadRole()
                        lyr_read_role.layer = layer
                        lyr_read_role.role = role
                        lyr_read_role.save()
                        read_roles.append(role)
                    except:
                        logging.getLogger(LOGNAME).exception('Probably tried to create a LayerReadRole for a externally managed permission')
            except:
                logging.getLogger(LOGNAME).exception('Error creating layer read permissions')
                pass

        LayerWriteRole.objects.filter(layer=layer, external=False).delete()
        for role in assigned_write_roles:
            try:
                if role in all_roles:
                    try:
                        layer_write_role = LayerWriteRole()
                        layer_write_role.layer = layer
                        layer_write_role.role = role
                        layer_write_role.save()
                        write_roles.append(role)
                    except:
                        logging.getLogger(LOGNAME).exception('Probably tried to create a LayerWriteRole for a externally managed permission')
            except:
                logging.getLogger(LOGNAME).exception('Error creating layer write permissions')
                pass
        LayerManageRole.objects.filter(layer=layer).delete()
        for role in assigned_manage_roles:
            try:
                if role in all_roles:
                    layer_manage_role = LayerManageRole()
                    layer_manage_role.layer = layer
                    layer_manage_role.role = role
                    layer_manage_role.save()
            except:
                logging.getLogger(LOGNAME).exception('Error creating layer manage permissions')
                pass
        self.set_layer_data_rules(layer, read_roles, write_roles)
