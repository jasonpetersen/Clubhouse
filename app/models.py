# none of this works
# this file should handle user login information and user accounts, etc.

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .db import *
from app import login_manager

@login_manager.user_loader
def load_user(id_num):
    return User(int(id_num))

# user class, this is needed for compatibility with flask-login
class User(UserMixin):
    def __init__(self, id_num):
        super()
        # get user information
        num, username, password_hash, is_admin, last_name = get_user_from_id(id_num)
        if username: # valid id
            self.username = username
            self.id = id_num
            self.hash = password_hash
            self.last_name_first = last_name
            # set user access level
            if is_admin:
                self.access = "admin"
                self.name = "Administrator"
            else:
                self.access = "clubhouse"
                self.name = get_clubhouse_from_id(self.id)
        else: # this shouldn't happen
            raise ValueError

    def check_password(self, password):
        if check_password_hash(self.hash, password): # correct combo
            return True
        return False
