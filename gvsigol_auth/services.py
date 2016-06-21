'''
    gvSIG Online.
    Copyright (C) 2007-2015 gvSIG Association.

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
from models import UserGroup, UserGroupUser
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

class GvSigOnlineServices():
    
    def __init__(self, is_enabled, host, port, domain, username, password):
        self.is_enabled = is_enabled
        self.host = host
        self.port = port
        self.domain = domain
        self.username = username
        self.password = password
        
        if sys.getdefaultencoding() != 'utf-8':
            reload(sys)  # Reload does the trick!
            sys.setdefaultencoding('utf-8')
        
        if is_enabled:
            self.ldap = ldap.initialize('ldap://' + host + ':' + port)
            self.ldap.simple_bind_s(username, password)
            
            
    def ldap_create_admin_group(self):
        if self.is_enabled:
            try:
                
                dn=str("cn=admin,ou=groups," + self.domain)                    
                attrs = {}
                attrs['objectclass'] = ['top','posixGroup']
                attrs['cn'] = str('admin')
                attrs['gidNumber'] = str('501')  
        
                ldif = modlist.addModlist(attrs)
                self.ldap.add_s(dn,ldif)
            except ldap.LDAPError, e:
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
                
                dn=str("cn=admin,ou=users," + self.domain)
                attrs = {}
                attrs['cn'] = 'admin'
                attrs['gidNumber'] = '501'
                attrs['givenName'] = ''
                attrs['homeDirectory'] = '/home/users/admin'
                attrs['objectclass'] = ['top','posixAccount','inetOrgPerson','extensibleObject']
                attrs['userPassword'] = 'admin52'
                attrs['oclExtraAttrs'] = 'CAT_ALL_Administrator'
                attrs['uidNumber'] = '1000'
                attrs['sn'] = 'admin'
                attrs['uid'] = 'admin'
            
                ldif = modlist.addModlist(attrs)
                self.ldap.add_s(dn,ldif)
                
            except ldap.LDAPError, e:
                pass
            try:
                # ensure the user exists both on django and ldap
                if not User.objects.filter(username="admin").exists():
                    admin_user = User.objects.create_superuser(username='admin', password='admin52', email='jrodrigo@scolab.es')
                    admin_group = UserGroup.objects.get(name__exact='admin')
                    usergroup_user = UserGroupUser(
                        user = admin_user,
                        user_group = admin_group
                    )
                    usergroup_user.save()
                
                    self.add_default_group_member(admin_user)
                    self.add_admin_group_member(admin_user)
            except Exception as exc:
                pass
        
    def ldap_create_default_group(self):
        if self.is_enabled:
            try:
                dn=str("cn=default,ou=groups," + self.domain)
                    
                attrs = {}
                attrs['objectclass'] = ['top','posixGroup']
                attrs['cn'] = str('default')
                attrs['gidNumber'] = str('500')  
        
                ldif = modlist.addModlist(attrs)
                self.ldap.add_s(dn,ldif)
                
            except ldap.LDAPError, e:
                pass
        
    def ldap_add_group(self, group):
        if self.is_enabled:
            last_gid = self.ldap_get_last_gid()    
            
            try:
                last_gid = last_gid + 1
                dn=str("cn=" + group.name + ",ou=groups," + self.domain)
                    
                attrs = {}
                attrs['objectclass'] = ['top','posixGroup']
                attrs['cn'] = str(group.name)
                attrs['gidNumber'] = str(last_gid)
                attrs['description'] = str(group.description)  
        
                ldif = modlist.addModlist(attrs)
                self.ldap.add_s(dn,ldif)                        
                
            except ldap.LDAPError, e:
                print e 
        
        
    def ldap_modify_group(self, old_group_name, new_group_name):
        if self.is_enabled:
            print 'group modified'
        
    def ldap_delete_group(self, group):    
        if self.is_enabled:   
            try:
                dn = "cn=" + group.name + ",ou=groups," + self.domain
                self.ldap.delete_s(dn)
                
            except ldap.LDAPError, e:
                print e
        
    def ldap_add_user(self, user, password, is_admin):
        if self.is_enabled:
            # The dn of our new entry/object
            dn=str("cn=" + user.username + ",ou=users," + self.domain)
            
            # A dict to help build the "body" of the object
            attrs = {}
            attrs['cn'] = str(user.username)
            attrs['gidNumber'] = str('500')
            attrs['givenName'] = str(user.first_name)
            attrs['homeDirectory'] = str('/home/users/' + user.username)
            if is_admin:
                attrs['objectclass'] = ['top','posixAccount','inetOrgPerson','extensibleObject']
                attrs['olcExtraAttrs'] = 'CAT_ALL_Administrator'
            else:
                attrs['objectclass'] = ['top','posixAccount','inetOrgPerson']
            attrs['userPassword'] = str(password)
            attrs['uidNumber'] = str(self.get_last_uid() + 1)
            attrs['sn'] = str(user.username)
            attrs['uid'] = str(user.username)
            
            # Convert our dict to nice syntax for the add-function using modlist-module
            ldif = modlist.addModlist(attrs)
            
            # Do the actual synchronous add-operation to the ldapserver
            self.ldap.add_s(dn,ldif)
            
            self.add_default_group_member(user)
        
    def ldap_modify_user(self, group_id, group_name):
        if self.is_enabled:
            print 'User modified'
        
    def ldap_delete_user(self, user):
        if self.is_enabled:
            try:
                dn = "cn=" + user.username + ",ou=users," + self.domain
                self.ldap.delete_s(dn)
                
            except ldap.LDAPError, e:
                print e
            
    def ldap_add_group_member(self, user, group):
        if self.is_enabled:
            add_member = [(ldap.MOD_ADD, 'memberUid', str(user.username))]
    
            try:
                group_dn = str("cn=" + group.name + ",ou=groups," + self.domain)
                self.ldap.modify_s(group_dn, add_member)
                    
            except ldap.LDAPError, e:
                print e
                return False
            
    def ldap_add_default_group_member(self, user):
        if self.is_enabled:
            add_member = [(ldap.MOD_ADD, 'memberUid', str(user.username))]
    
            try:
                group_dn = str("cn=default,ou=groups," + self.domain)
                self.ldap.modify_s(group_dn, add_member)
                    
            except ldap.LDAPError, e:
                print e
                return False
            
    def ldap_add_admin_group_member(self, user):
        if self.is_enabled:
            add_member = [(ldap.MOD_ADD, 'memberUid', str(user.username))]
    
            try:
                group_dn = str("cn=admin,ou=groups," + self.domain)
                self.ldap.modify_s(group_dn, add_member)
                    
            except ldap.LDAPError, e:
                print e
                return False
        
    def ldap_delete_group_member(self, user, group):
        if self.is_enabled:
            delete_member = [(ldap.MOD_DELETE, 'memberUid', str(user.username))]
    
            try:
                group_dn = str("cn=" + group.name + ",ou=groups," + self.domain)
                self.ldap.modify_s(group_dn, delete_member)
                    
            except ldap.LDAPError, e:
                print e
                return False
            
    def ldap_delete_default_group_member(self, user):
        if self.is_enabled:
            delete_member = [(ldap.MOD_DELETE, 'memberUid', str(user.username))]
    
            try:
                group_dn = str("cn=default,ou=groups," + self.domain)
                self.ldap.modify_s(group_dn, delete_member)
                    
            except ldap.LDAPError, e:
                print e
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
            
        except ldap.LDAPError, e:
            print e
    
       
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
            
        except ldap.LDAPError, e:
            print e
            
            
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
            
        except ldap.LDAPError, e:
            print e
            
            
    def ldap_change_user_password(self, user, password):
        if self.is_enabled:
            user_dn = str("cn=" + user.username + ",ou=users," + self.domain)
            new_password = [(ldap.MOD_REPLACE, 'userPassword', str(password))]
    
            try:
                self.ldap.modify_s(user_dn, new_password)
                    
            except ldap.LDAPError, e:
                print e
                return False

    
    def create_default_layer_group(self):
        if not LayerGroup.objects.filter(name="__default__").exists():
            lg = LayerGroup()
            lg.name = "__default__"
            lg.description = "Default group"
            lg.save()
      
            
    def add_data_directory(self, group):
        path = settings.MEDIA_ROOT + "data/" + group.name
        try: 
            os.makedirs(path, mode=0777)
            
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
            print('Error: %s' % e)
            return False
            
    
            
def get_services():
    try:
        is_enabled = GVSIGOL_LDAP['ENABLED']
        host = GVSIGOL_LDAP['HOST']
        port = GVSIGOL_LDAP['PORT']
        domain = GVSIGOL_LDAP['DOMAIN']
        username = GVSIGOL_LDAP['USERNAME']
        password = GVSIGOL_LDAP['PASSWORD']
    except:
        raise ImproperlyConfigured

    gvsigOnline = GvSigOnlineServices(is_enabled, host, port, domain, username, password)
    if is_enabled:
        gvsigOnline.ldap_create_default_group()
        gvsigOnline.ldap_create_admin_group()
        gvsigOnline.ldap_create_admin_user()

    gvsigOnline.create_default_layer_group()

    return gvsigOnline

services = get_services()