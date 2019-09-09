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
@author: Javi Rodrigo <jrodrigo@scolab.es>
'''
import backend_geoserver
import logging

logger = logging.getLogger("gvsigol")


from models import Server, Node
           
class GeographicServers:
    def __init__(self):
        self.servers = []
        for s in Server.objects.all():
            master_node = None
            slave_nodes = []
            for n in Node.objects.filter(server=s):
                if n.is_master:
                    master_node = n.url
                else:
                    slave_nodes.append(n.url)
                    
            gs = backend_geoserver.Geoserver(s.id, s.default, s.name, s.user, s.password, master_node, slave_nodes)
            self.servers.append(gs)
        
    def get_servers(self):
            return self.servers
        
    def add_server(self, sv_conf):
        ''' TO CHANGE '''
        master_node = None
        slave_nodes = []
        for n in Node.objects.filter(server=sv_conf):
            if n.is_master:
                master_node = n.url
            else:
                slave_nodes.append(n.url)
                
        geoserver = backend_geoserver.Geoserver(sv_conf.id, sv_conf.default, sv_conf.name, sv_conf.user, sv_conf.password, master_node, slave_nodes)
        self.servers.append(geoserver)
    
    def get_server_by_name(self, name):
        for s in self.servers:
            if s.name == name:
                return s
    
    def get_server_by_id(self, id):
        for s in self.servers:
            if s.id == int(id):
                return s
    
    def get_default_server(self):
        for s in self.servers:
            if s.default:
                return s
            
    def get_master_node(self, id):
        for n in Node.objects.filter(server_id=int(id)):
            if n.is_master:
                return n   
            
    def get_all_nodes(self, id):
        return Node.objects.filter(server_id=int(id))

__geographic_servers = None

def get_instance():
    global __geographic_servers
    if __geographic_servers is None:
        __geographic_servers = GeographicServers()
    return __geographic_servers
