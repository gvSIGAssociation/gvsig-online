from django.test import TestCase
from gvsigol_auth.models import UserGroup, UserGroupUser
from django.contrib.auth.models import User

class CreateUserEnvironmentTest(TestCase):
    
    def create_user(self, username="username", first_name="firstname", last_name="lastname", email="test@gmail.com", is_superuser=True, is_staff=True, password="aassddff"):
        user = User.objects.create(
            username=username, 
            first_name=first_name, 
            last_name=last_name, 
            email=email, 
            is_superuser=is_superuser, 
            is_staff=is_staff,
            password=password
        )
        return user
    
    def create_usergroup(self, name="name", description="description"):
        usergroup = UserGroup.objects.create(
            name=name, 
            description=description
        )
        return usergroup
    
    def create_usergroupuser(self, user, user_group):
        usergroup_user = UserGroupUser.objects.create(
            user=user, 
            user_group=user_group
        )
        return usergroup_user

    def test_user_environment_creation(self):
        user = self.create_user()
        
        usergroup = self.create_usergroup()
        
        usergroup_user = self.create_usergroupuser(user, usergroup)
        
        self.assertTrue(isinstance(user, User))
        self.assertTrue(isinstance(usergroup, UserGroup))
        self.assertTrue(isinstance(usergroup_user, UserGroupUser))

