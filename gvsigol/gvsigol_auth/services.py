'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.core.exceptions import ImproperlyConfigured
from .models import UserGroup, UserGroupUser
from gvsigol_core.models import LayerGroup
from django.utils.translation import ugettext as _
from gvsigol.settings import GVSIGOL_LDAP
from django.contrib.auth.models import User
import ldap.modlist as modlist
from gvsigol import settings
import shutil
import ldap
import sys
import os
import imp

LDAP_ENCODING = 'utf-8'

class GvSigOnlineServices():
    
    def __init__(self, is_enabled, host, port, domain, username, password):
        self.is_enabled = is_enabled
        self.host = host
        self.port = port
        self.domain = domain
        self.username = username
        self.password = password
        
        if sys.getdefaultencoding() != 'utf-8':
            imp.reload(sys)  # Reload does the trick!
            sys.setdefaultencoding('utf-8')
        
        if is_enabled:
            self.ldap = ldap.initialize('ldap://' + host + ':' + port)
            self.ldap.simple_bind_s(username, password)
            
            
    def ldap_create_admin_group(self):
        if self.is_enabled:
            try:
                
                dn=str("cn=admin,ou=groups," + self.domain)                    
                attrs = {}
                attrs['objectclass'] = ['top'.encode(LDAP_ENCODING),'posixGroup'.encode(LDAP_ENCODING)]
                attrs['cn'] = 'admin'.encode(LDAP_ENCODING)
                attrs['gidNumber'] = '501'.encode(LDAP_ENCODING)
        
                ldif = modlist.addModlist(attrs)
                self.ldap.add_s(dn,ldif)
            except ldap.LDAPError as e:
                pass
            try:
                if not UserGroup.objects.filter(name="admin").exists():
                    group = UserGroup(
                        name = 'admin',
                        description = _('Group for admin users')
                    )
                    group.save()                
            except Exception as e:
                pass           
            
    def ldap_create_admin_user(self):
        if self.is_enabled:
            try:
                
                dn=str("cn=root,ou=users," + self.domain)
                attrs = {}
                attrs['cn'] = 'root'.encode(LDAP_ENCODING)
                attrs['gidNumber'] = '501'.encode(LDAP_ENCODING)
                attrs['givenName'] = ''.encode(LDAP_ENCODING)
                attrs['homeDirectory'] = '/home/users/root'.encode(LDAP_ENCODING)
                attrs['objectclass'] = ['top'.encode(LDAP_ENCODING),'posixAccount'.encode(LDAP_ENCODING),'inetOrgPerson'.encode(LDAP_ENCODING),'extensibleObject'.encode(LDAP_ENCODING)]
                attrs['userPassword'] = self.password.encode(LDAP_ENCODING)
                attrs['oclExtraAttrs'] = 'CAT_ALL_Administrator'.encode(LDAP_ENCODING)
                attrs['uidNumber'] = '1000'.encode(LDAP_ENCODING)
                attrs['sn'] = 'root'.encode(LDAP_ENCODING)
                attrs['uid'] = 'root'.encode(LDAP_ENCODING)
            
                ldif = modlist.addModlist(attrs)
                self.ldap.add_s(dn,ldif)
                
            except ldap.LDAPError as e:
                pass
            try:
                # ensure the user exists both on django and ldap
                if not User.objects.filter(username="root").exists():
                    admin_user = User.objects.create_superuser(username='root', password=self.password, email='info@scolab.es')
                    admin_user.is_superuser = True
                    admin_user.is_staff = True
                    admin_group = UserGroup.objects.get(name__exact='root')
                    usergroup_user = UserGroupUser(
                        user = admin_user,
                        user_group = admin_group
                    )
                    usergroup_user.save()
                
                    self.ldap_add_default_group_member(admin_user)
                    self.ldap_add_admin_group_member(admin_user)
            except Exception as exc:
                pass
        
    def ldap_create_default_group(self):
        if self.is_enabled:
            try:
                dn=str("cn=default,ou=groups," + self.domain)
                    
                attrs = {}
                attrs['objectclass'] = ['top'.encode(LDAP_ENCODING),'posixGroup'.encode(LDAP_ENCODING)]
                attrs['cn'] = 'default'.encode(LDAP_ENCODING)
                attrs['gidNumber'] = '500'.encode(LDAP_ENCODING)
        
                ldif = modlist.addModlist(attrs)
                self.ldap.add_s(dn,ldif)
                
            except ldap.LDAPError as e:
                pass
        
    def ldap_add_group(self, group):
        if self.is_enabled:
            try:
                last_gid = self.ldap_get_last_gid()
                last_gid = last_gid + 1
                dn=str("cn=" + group.name + ",ou=groups," + self.domain)
                    
                attrs = {}
                attrs['objectclass'] = ['top'.encode(LDAP_ENCODING),'posixGroup'.encode(LDAP_ENCODING)]
                attrs['cn'] = group.name.encode(LDAP_ENCODING)
                attrs['gidNumber'] = str(last_gid).encode(LDAP_ENCODING)
                attrs['description'] = group.description.encode(LDAP_ENCODING)
        
                ldif = modlist.addModlist(attrs)
                self.ldap.add_s(dn,ldif)                        
                
            except ldap.LDAPError as e:
                print(e)
                return False
        
        
    def ldap_modify_group(self, old_group_name, new_group_name):
        if self.is_enabled:
            print('group modified')
        
    def ldap_delete_group(self, group):    
        if self.is_enabled:   
            try:
                dn = "cn=" + group.name + ",ou=groups," + self.domain
                self.ldap.delete_s(dn)
                
            except ldap.LDAPError as e:
                print(e)
        
    def ldap_add_user(self, user, password, is_superuser):
        if self.is_enabled:
            # The dn of our new entry/object
            dn = "cn=" + user.username + ",ou=users," + self.domain
            
            # A dict to help build the "body" of the object
            attrs = {}
            attrs['cn'] = user.username.encode(LDAP_ENCODING)
            attrs['gidNumber'] = '500'.encode(LDAP_ENCODING)
            attrs['givenName'] = user.first_name.encode(LDAP_ENCODING)
            attrs['homeDirectory'] = ('/home/users/' + user.username).encode(LDAP_ENCODING)
            if is_superuser:
                attrs['objectclass'] = ['top'.encode(LDAP_ENCODING),'posixAccount'.encode(LDAP_ENCODING),'inetOrgPerson'.encode(LDAP_ENCODING),'extensibleObject'.encode(LDAP_ENCODING)]
                attrs['olcExtraAttrs'] = 'CAT_ALL_Administrator'.encode(LDAP_ENCODING)
            else:
                attrs['objectclass'] = ['top'.encode(LDAP_ENCODING),'posixAccount'.encode(LDAP_ENCODING),'inetOrgPerson'.encode(LDAP_ENCODING)]
            attrs['userPassword'] = password.encode(LDAP_ENCODING)
            attrs['uidNumber'] = str(self.ldap_get_last_uid() + 1).encode('utf-8')
            attrs['sn'] = user.username.encode(LDAP_ENCODING)
            attrs['uid'] = user.username.encode(LDAP_ENCODING)
            
            # Convert our dict to nice syntax for the add-function using modlist-module
            ldif = modlist.addModlist(attrs)
            
            # Do the actual synchronous add-operation to the ldapserver
            self.ldap.add_s(dn,ldif)
            
            self.ldap_add_default_group_member(user)
        
    def ldap_modify_user(self, group_id, group_name):
        if self.is_enabled:
            print('User modified')
        
    def ldap_delete_user(self, user):
        if self.is_enabled:
            try:
                dn = "cn=" + user.username + ",ou=users," + self.domain
                self.ldap.delete_s(dn)
                
            except ldap.LDAPError as e:
                print(e)
            
    def ldap_add_group_member(self, user, group):
        if self.is_enabled:
            try:
                add_member = [(ldap.MOD_ADD, 'memberUid', user.username.encode(LDAP_ENCODING))]
                group_dn = str("cn=" + group.name + ",ou=groups," + self.domain)
                self.ldap.modify_s(group_dn, add_member)
                    
            except ldap.LDAPError as e:
                print(e)
                return False
            
    def ldap_add_default_group_member(self, user):
        if self.is_enabled:
            add_member = [(ldap.MOD_ADD, 'memberUid', user.username.encode(LDAP_ENCODING))]
    
            try:
                group_dn = str("cn=default,ou=groups," + self.domain)
                self.ldap.modify_s(group_dn, add_member)
                    
            except ldap.LDAPError as e:
                print(e)
                return False
            
    def ldap_add_admin_group_member(self, user):
        if self.is_enabled:
            add_member = [(ldap.MOD_ADD, 'memberUid'.encode(LDAP_ENCODING), user.username.encode(LDAP_ENCODING))]
    
            try:
                group_dn = str("cn=admin,ou=groups," + self.domain)
                self.ldap.modify_s(group_dn, add_member)
                    
            except ldap.LDAPError as e:
                print(e)
                return False
        
    def ldap_delete_group_member(self, user, group):
        if self.is_enabled:
            delete_member = [(ldap.MOD_DELETE, 'memberUid', user.username.encode(LDAP_ENCODING))]
    
            try:
                group_dn = str("cn=" + group.name + ",ou=groups," + self.domain)
                self.ldap.modify_s(group_dn, delete_member)
                    
            except ldap.LDAPError as e:
                print(e)
                return False
            
    def ldap_delete_default_group_member(self, user):
        if self.is_enabled:
            delete_member = [(ldap.MOD_DELETE, 'memberUid', user.username.encode(LDAP_ENCODING))]
    
            try:
                group_dn = str("cn=default,ou=groups," + self.domain)
                self.ldap.modify_s(group_dn, delete_member)
                    
            except ldap.LDAPError as e:
                print(e)
                return False
        
    def ldap_get_last_gid(self):
        
        self.ldap.protocol_version = ldap.VERSION3        
        baseDN = "ou=groups," + self.domain
        searchScope = ldap.SCOPE_SUBTREE
        searchFilter = "cn=*"
        retrieveAttributes = None
        
        gids = []
        try:
            ldap_result_id = self.ldap.search(baseDN, searchScope, searchFilter, retrieveAttributes)
            while 1:
                result_type, result_data = self.ldap.result(ldap_result_id, 0)
                if (result_data == []):
                    break
                
                else:            
                    gid = result_data[0][1]['gidNumber'][0]
                    gids.append(int(gid))
            
            last_gid = 500
            if len(gids) > 0:
                gids.sort()
                last_gid = gids[-1]
            return int(last_gid)
            
        except ldap.LDAPError as e:
            print(e)
    
       
    def ldap_get_last_uid(self):
        
        self.ldap.protocol_version = ldap.VERSION3        
        baseDN = "ou=users," + self.domain
        searchScope = ldap.SCOPE_SUBTREE
        searchFilter = "cn=*"
        retrieveAttributes = None
        
        uids = []
        try:
            ldap_result_id = self.ldap.search(baseDN, searchScope, searchFilter, retrieveAttributes)
            while 1:
                result_type, result_data = self.ldap.result(ldap_result_id, 0)
                if (result_data == []):
                    break
                
                else:            
                    uid = result_data[0][1]['uidNumber'][0]
                    uids.append(int(uid))
            
            last_uid = 5000
            if len(uids) > 0:
                uids.sort()
                last_uid = uids[-1]
            return int(last_uid)
            
        except ldap.LDAPError as e:
            print(e)
            
            
    def ldap_get_uid(self, user_name):
        
        self.ldap.protocol_version = ldap.VERSION3        
        baseDN = "ou=users," + self.domain
        searchScope = ldap.SCOPE_SUBTREE
        searchFilter = "cn=" + user_name
        retrieveAttributes = None
        
        uids = []
        try:
            ldap_result_id = self.ldap.search(baseDN, searchScope, searchFilter, retrieveAttributes)
            while 1:
                result_type, result_data = self.ldap.result(ldap_result_id, 0)
                if (result_data == []):
                    break
                
                else:            
                    uid = result_data[0][1]['uidNumber'][0]
                    uids.append(int(uid))
            
            last_uid = 5000
            if len(uids) > 0:
                uids.sort()
                last_uid = uids[-1]
            return int(last_uid)
            
        except ldap.LDAPError as e:
            print(e)
            
            
    def ldap_change_user_password(self, user, password):
        if self.is_enabled:
            user_dn = str("cn=" + user.username + ",ou=users," + self.domain)
            new_password = [(ldap.MOD_REPLACE, 'userPassword', password.encode('utf-8'))]
    
            try:
                self.ldap.modify_s(user_dn, new_password)
                    
            except ldap.LDAPError as e:
                print(e)
                return False

    
    def create_default_layer_group(self):
        if not LayerGroup.objects.filter(name="__default__").exists():
            lg = LayerGroup()
            lg.name = "__default__"
            lg.description = "Default group"
            lg.save()
      
            
    def add_data_directory(self, group):
        aux = settings.MEDIA_ROOT
        if aux.endswith('/'):
            aux = aux[:-1]
        path = aux + "/data/" + group.name
        try: 
            os.makedirs(path, mode=0o777)
            
        except OSError as e:
            if not os.path.isdir(path):
                raise
            
    def delete_data_directory(self, group):
        try: 
            path = settings.MEDIA_ROOT + "data/" + group.name
            if os.path.exists(path):
                shutil.rmtree(path)
                    
            return True
         
        except Exception as e:
            print(('Error: %s' % e))
            return False
            
# Hacemos override de la clase para implementar la autenticacion pass-through con AD

class GvSigOnlineServicesAD(GvSigOnlineServices):
    
    # override
    def ldap_add_user(self, user, password, is_superuser):
        ad_suffix = GVSIGOL_LDAP['AD']
        if self.is_enabled:
            # The dn of our new entry/object
            dn=str("cn=" + user.username + ",ou=users," + self.domain)
            
            # A dict to help build the "body" of the object
            attrs = {}
            attrs['cn'] = str(user.username)
            attrs['gidNumber'] = str('500')
            attrs['givenName'] = str(user.first_name)
            attrs['homeDirectory'] = str('/home/users/' + user.username)
            if is_superuser:
                attrs['objectclass'] = ['top','posixAccount','inetOrgPerson','extensibleObject']
                attrs['olcExtraAttrs'] = 'CAT_ALL_Administrator'
            else:
                attrs['objectclass'] = ['top','posixAccount','inetOrgPerson']
            attrs['userPassword'] = '{SASL}' + str(user.username) + ad_suffix
            attrs['uidNumber'] = str(GvSigOnlineServices.ldap_get_last_uid(self) + 1)
            attrs['sn'] = str(user.username)
            attrs['uid'] = str(user.username)
            
            # Convert our dict to nice syntax for the add-function using modlist-module
            ldif = modlist.addModlist(attrs)
            
            # Do the actual synchronous add-operation to the ldapserver
            self.ldap.add_s(dn,ldif)
            
            self.ldap_add_default_group_member(user)
            #print "Creando usuario ..." + attrs['userPassword']
     
__gvsigOnline = None
def get_services():
    global __gvsigOnline
    if __gvsigOnline:
        return __gvsigOnline
    try:
        is_enabled = GVSIGOL_LDAP['ENABLED']
        host = GVSIGOL_LDAP['HOST']
        port = GVSIGOL_LDAP['PORT']
        domain = GVSIGOL_LDAP['DOMAIN']
        username = GVSIGOL_LDAP['USERNAME']
        password = GVSIGOL_LDAP['PASSWORD']
        ad_suffix = GVSIGOL_LDAP['AD']
    except:
        raise ImproperlyConfigured
    
    if not ad_suffix:
        __gvsigOnline = GvSigOnlineServices(is_enabled, host, port, domain, username, password)
    else:        
        __gvsigOnline = GvSigOnlineServicesAD(is_enabled, host, port, domain, username, password)
        
    if is_enabled:
        __gvsigOnline.ldap_create_default_group()
        __gvsigOnline.ldap_create_admin_group()
        __gvsigOnline.ldap_create_admin_user()
    __gvsigOnline.create_default_layer_group()
    return __gvsigOnline

