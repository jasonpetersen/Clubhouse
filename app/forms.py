# login form and checkin form

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, HiddenField, DateField
from wtforms.validators import DataRequired
from flask_babel import lazy_gettext as _l
from helpers import binary_search
from .db import *

# login forms

class LoginForm(FlaskForm):
    user = StringField(_l('Username'), validators = [DataRequired()])
    password = PasswordField(_l('Password'), validators = [DataRequired()])
    remember = BooleanField(_l('Remember Me'))
    submit = SubmitField(_l('Sign In'))

class AuthenticateForm(FlaskForm):
    password = PasswordField(_l("Re-enter your password"), validators = [DataRequired()])
    submit = SubmitField(_l('Sign In'))

# form to view and manage clubhouse members
class MemberViewForm(FlaskForm):
    memberselect = SelectField(_l("Member List"), choices = [])
    edit = SubmitField(_l("View/Edit"))
    new_member = SubmitField(_l("New Member"))

# wrapper class for MemberViewForm
class MemberManager:
    def __init__(self, clubhouse=None):
        if clubhouse:
            self.clubhouse=clubhouse
        else:
            self.clubhouse = 1 # for testing only
        self.member_form = MemberViewForm()
        self.display_last = False # TODO: pull from clubhouse
        # get all members in desired format
        if self.display_last:
            self.memberlist = [(num, last + ", " + first) for num, first, last in get_clubhouse_members(self.clubhouse)]
        else:
            self.memberlist = [(num, first + " " + last) for num, first, last in get_clubhouse_members(self.clubhouse)]
        # set member list selection options
        self.member_form.memberselect.choices = self.memberlist

# form and handler for adding or editing member
class MemberAddForm(FlaskForm):
    mem_id = HiddenField() # store member id for post request when editing member
    club_id = HiddenField() # store club id
    first_name = StringField(_l('First Name'), validators = [DataRequired()])
    last_name = StringField(_l('Last Name'), validators = [DataRequired()])
    street_address = StringField(_l('Street Address'))
    city = StringField(_l('City'))
    state = StringField(_l('State'))
    zip_code = StringField(_l('Zip/Postal Code'))
    country = StringField(_l('Country'))
    member_email = StringField(_l('Email'))
    member_phone = StringField(_l('Phone'))
    join_date = DateField(_l('Join Date (y-m-d)'),format="'%Y-%m-%d'")
    birthday = DateField(_l('Birthday (y-m-d)'), format="'%Y-%m-%d'")
    school = StringField(_l('School'))
    gender = StringField(_l('Gender'))
    race_ethnicity = StringField(_l('Race and Ethnicity'))
    guardian_first_name = StringField(_l('Guardian First Name'))
    guardian_last_name = StringField(_l('Guardian Last Name'))
    guardian_relation = StringField(_l('Guardian Relationship to Member'))
    guardian_email = StringField(_l('Guardian Email'))
    guardian_phone = StringField(_l('Guardian Phone'))
    add_btn = SubmitField(_l('Add Member'))
    update_btn = SubmitField(_l('Update Member Info'))
    cancel_btn = SubmitField(_l('Cancel'))
    # two delete buttons to handle confirmation of member deletion
    delete_btn1 = SubmitField(_l('Remove Member'))
    delete_btn2 = SubmitField(_l('Remove Member'))

# handle form pre-population, loading data, etc.
class MemberInfoHandler:
    def __init__(self, data):
        self.form = MemberAddForm()
        # painfully load all data
        mem_id, firstname, lastname, address, city, state, zipcode, country, email, phone, joindate, birthday, school, gender, race, guardianfirstname, guardianlastname, guardianrelationship, guardianemail, guardianphone, club_id, checked_in_now = data
        # someone please find a better way to do this
        # load default data, disable some fields
        self.mem_id = mem_id
        self.club_id = club_id
        self.form.mem_id.render_kw = {'value': mem_id}
        self.form.club_id.render_kw = {'value': club_id}
        if firstname:
            self.form.first_name.render_kw = {'value': firstname, 'disabled': 'disabled'}
        if lastname:
            self.form.last_name.render_kw = {'value': lastname, 'disabled': 'disabled'}
        if address:
            self.form.street_address.render_kw = {'value': address}
        if city:
            self.form.city.render_kw = {'value': city}
        if state:
            self.form.state.render_kw = {'value': state}
        if zipcode:
            self.form.zip_code.render_kw = {'value': zipcode}
        # TODO: uncomment once implemented and add to form
#        if country:
#            self.form.country.render_kw = {'value': country}
        if email:
            self.form.member_email.render_kw = {'value': email}
        if phone:
            self.form.member_phone.render_kw = {'value': phone}
        if joindate:
            self.form.join_date.render_kw = {'value': joindate, 'disabled': 'disabled'}
        if birthday:
            self.form.birthday.render_kw = {'value': birthday, 'disabled': 'disabled'}
        if school:
            self.form.school.render_kw = {'value': school}
        if gender:
            self.form.gender.render_kw = {'value': gender}
        if race:
            self.form.race_ethnicity.render_kw = {'value': race}
        if guardianfirstname:
            self.form.guardian_first_name.render_kw = {'value': guardianfirstname}
        if guardianlastname:
            self.form.guardian_last_name.render_kw = {'value': guardianlastname}
        if guardianrelationship:
            self.form.guardian_relation.render_kw = {'value': guardianrelationship}
        if guardianemail:
            self.form.guardian_email.render_kw = {'value': guardianemail}
        if guardianphone:
            self.form.guardian_phone.render_kw = {'value': guardianphone}

# forms to view and manage clubhouses

# these are mostly copied from the member view
class ClubhouseViewForm(FlaskForm):
    all_clubhouses = get_all_clubhouses()
    clubhouseselect = SelectField(_l("Clubhouse List"), choices = all_clubhouses)
    view = SubmitField(_l("View as Clubhouse"))
    new_clubhouse = SubmitField(_l("New Clubhouse"))

class ClubhouseAddForm(FlaskForm):
    full_name = StringField(_l('Clubhouse Full Name'), validators = [DataRequired()])
    short_name = StringField(_l('Clubhouse Short Name (optional)'))
    # TODO: image field for logo upload
    add_btn = SubmitField(_l('Add Clubhouse'))
    cancel_btn = SubmitField(_l('Cancel'))

# check-in form and handler, these are up and running
class CheckinForm(FlaskForm):
    '''create the checkin form template, not specialized for any data'''
    # key members by id for form submission
    members_in = []
    members_out = []
    # field for members to check in
    check_in_id = SelectField(_l("Member List"), choices = members_out)
    # field for checked-in members to check out
    check_out_id = SelectField(_l("Members Currently in Clubhouse"), choices = members_in)
    check_in = SubmitField(_l('Check In'))
    check_out = SubmitField(_l('Check Out'))

# handle all check in/out operations
class CheckinManager:
    def __init__(self, clubhouse=None):
        self.check_in_form = CheckinForm()
        if clubhouse:
            self.clubhouse = clubhouse # clubhouse is id number
            # TODO: actually set this field
            self.display_last = False # whether to display last name first
            # get list of all members and key by member id
            self.id_to_name = {}
            self.members_out = []
            for mem_id, first, last in get_clubhouse_members(self.clubhouse):
                # separate first and last names for sorting purposes
                self.id_to_name[str(mem_id)] = (first, last)
                # list is already sorted, initialize members_out here
                self.members_out.append(self.get_member_display(mem_id))
            self.members_in = []
            # parse checked-in members and remove them from checked-out list
            for mem_id, name in get_checked_in_members(self.clubhouse):
                member = self.get_member_display(mem_id)
                self.members_in.append(member)
                self.members_out.remove(member)
            # uncomment if sorting is broken
#            self.members_in.sort(key = lambda x: self.id_to_name[x[0]][1] + ", " + self.id_to_name[x[0]][0])
        if not clubhouse: # testing purposes
            self.members_in = [(123,"manager signed-in 1"), (234,"manager signed-in 2")]
            self.members_out = [(12,"manager signed-out 3"),(23,"manager signed-out 4")]
            # dictionary linking member id to member name
            self.id_to_name = {
                    123: "manager signed-in 1",
                    234: "manager signed-in 2",
                    12: "manager signed-out 3",
                    23: "manager signed-out 4"}
        self.setfields()

    # reset the SelectField choices
    def setfields(self):
        self.check_in_form.check_in_id.choices = self.members_out
        self.check_in_form.check_out_id.choices = self.members_in

    # return (id_num, first last) or (id_num, last first)
    # id_num gets cast to a string
    def get_member_display(self, id_num):
        mem_id = str(id_num)
        first, last = self.id_to_name[mem_id]
        if self.display_last:
            return (mem_id, last + ", " + first)
        return (mem_id, first + " " + last)

    # check in member id_num
    # move from out list to in list
    def checkin_member(self, id_num):
        # extract member to be removed
        member = self.get_member_display(id_num)
        self.members_out.remove(member)
        # check-in to database
        add_checkin(id_num, self.clubhouse)
        # insert member into sorted members_in list
        # x[0] gets member id, the rest gets last, first for sorting order
        self.members_in.insert(binary_search(self.members_in, member, key = lambda x: self.id_to_name[x[0]][1] + ", " + self.id_to_name[x[0]][0]), member)
#        self.members_in.insert(binary_search(self.members_in, self.id_to_name[id_num], key = lambda x: x[1]), member)
        self.setfields() # update visual

    # check out member id_num
    # move from in list to out list
    def checkout_member(self, id_num):
        # extract member to be removed
        member = self.get_member_display(id_num)
        self.members_in.remove(member)
        add_checkout(id_num, self.clubhouse)
        self.members_out.insert(binary_search(self.members_out, member, key = lambda x: self.id_to_name[x[0]][1] + ", " + self.id_to_name[x[0]][0]), member)
#       self.members_out.insert(binary_search(self.members_out, self.id_to_name[id_num], key = lambda x: x[1]), member)
        self.setfields()
