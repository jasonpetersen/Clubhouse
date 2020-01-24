# handle all routing things

# not sure what the imports should be but these seem to work?
import jsonpickle
from functools import wraps
from datetime import datetime
from flask import render_template, flash, redirect, request, url_for, session
from app import app
from app.forms import LoginForm, CheckinManager, MemberManager, MemberAddForm, MemberInfoHandler, AuthenticateForm, ClubhouseViewForm, ClubhouseAddForm, PasswordChangeForm
from flask_babel import lazy_gettext as _l
from flask_login import current_user, login_user, logout_user
from .db import *
from .plot import *
from .models import *

# function for two-level authentication
# also handles clubhouse impersonation
def login_required(access="basic", impersonate = False):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated: # user not logged in
                return login_manager.unauthorized()
            # access is either basic or admin
            if current_user.access != access and access != "basic":
                flash(_l("Insufficient credentials."))
                return redirect('/')
            # club_id is always in session for a clubhouse account
            if impersonate and 'club_id' not in session: # impersonation not met
                flash(_l("Please select a clubhouse to impersonate."))
                return redirect('/admin/clubhouseselect')
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

def fresh_login_required(access="basic", impersonate = False):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.access != access and access !="basic":
                flash(_l("Insufficient credentials."))
                return redirect('/')
            # TODO: determine if login_fresh is needed
            if not session['fresh']:
                return login_manager.needs_refresh()
            if impersonate and 'club_id' not in session: # same logic as above
                flash(_l("Please select a clubhouse to impersonate."))
                return redirect('/admin/clubhouseselect')
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

### homepages

# test page
# TODO: remove
@app.route('/test')
def auto_test():
    testform = CheckinManager(1)
    return render_template('test.html',form=testform.check_in_form)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/clubhouse')
@fresh_login_required(impersonate = True)
def club_home():
    return render_template('/clubhouse/home.html')

@app.route('/admin')
@fresh_login_required(access="admin")
def admin_home():
    return render_template('/admin/home.html')

# view data pages
@app.route('/clubhouse/view', methods=['GET','POST'])
@fresh_login_required(impersonate = True)
def coord_view():
    # the time_range will return the number of days to be considered
    # [1, 7, 30, 365] corresponding to day, week, month, year
    time_ranges = [(1,_l("Last 24 hours")), (7,_l("Last 7 days")), (30,_l("Last month")), (365,_l("Last year"))]
    # TODO: name things better, come up with a better indexing system?
    # 0 is meant to be raw data, e.g. number of people on each day
    data_format = [(0, _l("Check-ins")), (1, _l("Time of day")), (2, _l("Day of week"))]
    if request.method == 'POST':
        # TODO: title the graph and update to getting checkins for a given clubhouse
        # extract relevant information
        cur_range = request.form['range']
        cur_format = request.form['format']
        # pass cur_range, cur_format to template
        # to keep them displayed on the page (minimize confusion)
        return render_template('/clubhouse/view.html', time_ranges=time_ranges, data_format=data_format, plot=plot(cur_range, cur_format), cur_range =int(cur_range), cur_format = int(cur_format))
    if request.method == 'GET':
        # default cur_range, cur_format to be the first in the list
        return render_template('/clubhouse/view.html', time_ranges=time_ranges, data_format=data_format, cur_range = time_ranges[0][0], cur_format = data_format[0][0])

@app.route('/admin/view', methods=['GET', 'POST'])
@fresh_login_required(access="admin")
def admin_view():
    # copied from coord_view
    time_ranges = [(1,_l("Last 24 hours")), (7,_l("Last 7 days")), (30,_l("Last month")), (365,_l("Last year"))]
    data_format = [(0, _l("Check-ins")), (1, _l("Time of day")), (2, _l("Day of week"))]
    if request.method == 'POST':
        #TODO: actually pull data
        cur_range = request.form['range']
        cur_format = request.form['format']
        return "this method has not been implemented"
    if request.method == 'GET':
        return render_template('/admin/view.html', time_ranges=time_ranges, data_format=data_format, cur_range = time_ranges[0][0], cur_format = data_format[0][0])

# logins and logouts

# logout routing
@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')

# basic login form, it doesn't post anything yet
@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated: # already logged in, redirect based on account type
        if current_user.access == "admin":
            return redirect('/admin')
        return redirect('/clubhouse')
    form = LoginForm()
    if form.validate_on_submit():
        # read user input to form
        username = request.form['user']
        password = request.form['password']
        club_id = get_id_from_username(username)
        if club_id: # valid user
            user = User(club_id) # generate user object
            if user.check_password(password): # login success
                login_user(user, remember=form.remember.data)
                session['fresh'] = True # manually set fresh session
                # redirect based on user status
                if user.access == "admin":
                    # reset stored club id and impersonation name
                    if 'club_id' in session:
                        session.pop('club_id')
                    if 'impersonation' in session:
                        session.pop('impersonation')
                    return redirect('/admin')
                # otherwise this user is a clubhouse coordinator
                session['club_id'] = club_id # store club id in use
                return redirect('/clubhouse')
        # display that credentials are incorrect
        flash(_l("Username/password combination incorrect."))
        return redirect('/login')
    return render_template('login.html', form=form, refresh = False)

# page for reauthentication
@app.route('/reauthenticate', methods=['GET','POST'])
@login_required()
def reauthenticate():
    form = AuthenticateForm()
    if form.validate_on_submit():
        # read user input to form
        password = request.form['password']
        if current_user.check_password(password): # login success
            session['fresh'] = True # session is now fresh
            # redirect based on user status
            # TODO: redirect to 'next' page
            if current_user.access == "admin":
                return redirect('/admin')
            return redirect('/clubhouse')
        # display that credentials are incorrecrt
        flash(_l("Incorrect password."))
        return redirect('/reauthenticate')
    return render_template('login.html', form=form, refresh = True)

# rest of app routes for clubhouse home page

# add new member
@app.route('/clubhouse/addmember', methods=['GET','POST']) # might need a method -- better to make html name informative if different?
@fresh_login_required(impersonate = True)
def create_member():
    form = MemberAddForm()
    # default join date
    form.join_date.render_kw = {'value': datetime.now().date()}
    if request.method == 'POST':
        if "cancel_btn" in request.form:
            return redirect('/clubhouse/members')
        elif form.validate_on_submit():
        # TODO: add member info to database, parse form and remove empty fields
            flash(_l(add_member(session['club_id'],form)))
            # TODO: pull new member id for this GET request to work
            return redirect('/clubhouse/editmember') # shows the posted data of newly created member
    return render_template('/clubhouse/edit.html', form=form, new_member=True)

@app.route('/clubhouse/members', methods=['GET','POST'])
@fresh_login_required(impersonate = True)
def manage_members():
    club_id = session['club_id'] 
    form_manager = MemberManager(club_id)
    if request.method == "POST":
        if "new_member" in request.form: # add new member
            return redirect('/clubhouse/addmember')
        if form_manager.member_form.validate_on_submit(): # confirm member selected for edit
            # temporarily store member id
            session['edit_member_id'] = int(request.form['memberselect'])
            return redirect('/clubhouse/editmember')
    return render_template('/clubhouse/membership.html', form=form_manager.member_form)

@app.route('/clubhouse/editmember',methods=['GET','POST'])
@fresh_login_required(impersonate = True)
def edit_member_info():
    if 'edit_member_id' not in session:
        # this page is not accessible without choosing a member to edit
        return redirect('/clubhouse/members')
    club_id = session['club_id']
    mem_id = session['edit_member_id']
    if request.method == 'POST':
        if "cancel_btn" in request.form: # cancel the updates
            session.pop('edit_member_id') 
            return redirect('/clubhouse/members')
        if "delete_btn1" in request.form: # first click of delete button
            # go to confirmation step
            flash(_l("WARNING: Attempting to delete member - this action is irreversible. Click 'Remove Member' again to confirm."))
            # display message and require resubmit
            # note this will also clear all fields
            # TODO: store data if remove is clicked but then canceled?
            # alternatively just find a better confirmation solution
            handle = MemberInfoHandler(get_specific_member(club_id, mem_id))
            return render_template('/clubhouse/edit.html',form=handle.form, new_member=False, second_del = True)
        if "delete_btn2" in request.form: # delete member from active members
            flash(_l(delete_specific_member(club_id, mem_id))) # delete from db, returns success/error message
            session.pop('edit_member_id') # clear stored id
            return redirect('/clubhouse/members')
        # otherwise update info
        if "update_btn" in request.form:
            # convert to mutable dictionary
            update_dict = dict(request.form) # WARNING: values are in list form
            # remove all empty/unnecessary fields
            to_remove = ["csrf_token", "update_btn"]
            for key in update_dict:
                if type(update_dict[key]) == list and len(update_dict[key]) == 1:
                    update_dict[key] = update_dict[key][0]
            for field in update_dict:
                if len(update_dict[field]) == 0:
                    to_remove.append(field)
            for field in to_remove:
                del update_dict[field]
            flash(edit_member(club_id, mem_id, update_dict))
            # clear stored info
            session.pop('edit_member_id')
            return redirect('/clubhouse/members')
    # handle get portion - viewing info
    if request.method == "GET":
        # pull stored information
        handle = MemberInfoHandler(get_specific_member(club_id, mem_id))
        return render_template('/clubhouse/edit.html', form=handle.form, new_member=False)

# check-in page, main functionality of website
@app.route('/clubhouse/checkin', methods=['GET','POST'])
@login_required(impersonate = True)
def checkin_handler():
    # manually set session to stale
    session['fresh'] = False
    if request.method == "GET":
        # get checkin manager for this specific clubhouse
        testform = CheckinManager(session['club_id'])
    if request.method == "POST":
        # deserialize testform and rebind fields
        testform = jsonpickle.decode(session['testform'])
        testform.check_in_form.__init__()
        testform.setfields()
        # TODO: find a better solution to form resubmission error
        try:
            if "check_in" in request.form and "check_in_id" in request.form: # check-in button clicked
                testform.checkin_member(int(request.form["check_in_id"]))
            elif "check_out_id" in request.form: # check-out button
                testform.checkout_member(int(request.form["check_out_id"]))
            # serialize for persistence
            session['testform'] = jsonpickle.encode(testform)
            return render_template('/clubhouse/checkin.html',form=testform.check_in_form)
        except ValueError: # cheating way to handle form resubmission
            return redirect('/clubhouse/checkin')
    session['testform'] = jsonpickle.encode(testform) # serialize, persistence
    return render_template('/clubhouse/checkin.html',form=testform.check_in_form)


# rest of app routes for admin home page

# largely copied from clubhouse/members
@app.route('/admin/clubhouses', methods=['GET','POST'])
@fresh_login_required(access="admin")
def manage_clubhouses():
    form = ClubhouseViewForm()
    if request.method == "POST":
        if "new_clubhouse" in request.form: # add new clubhouse
            return redirect('/admin/addclubhouse')
        if form.validate_on_submit():
            if "view" in request.form: # impersonate clubhouse
                session['club_id'] = int(request.form['clubhouseselect'])
                session['impersonation'] = get_clubhouse_from_id(session['club_id'])
                return redirect('/clubhouse')
            # otherwise edit button pressed, edit clubhouse
            # get and save id of clubhouse being edited
            session['edit_club_id'] = int(request.form['clubhouseselect'])
            return redirect('/admin/editclubhouse')
#            return render_template('/admin/change.html', form=PasswordChangeForm(), clubhouse_name = get_clubhouse_from_id(club_id))
    return render_template('/admin/clubhouses.html', form=form)

# page to select clubhouse to impersonate
# basically the same as above but with fewer things to handle
@app.route('/admin/clubhouseselect', methods=['GET','POST'])
@fresh_login_required(access="admin")
def choose_clubhouse():
    form = ClubhouseViewForm()
    if form.validate_on_submit():
        session['club_id'] = int(request.form['clubhouseselect'])
        session['impersonation'] = get_clubhouse_from_id(session['club_id'])
        return redirect('/clubhouse')
    return render_template('/admin/clubhouses.html', form=form, select_only = True)

@app.route('/admin/editclubhouse', methods=['GET','POST'])
@fresh_login_required(access="admin")
def change_clubhouse_password():
    if 'edit_club_id' not in session:
        # this page is not accessible without choosing a clubhouse to edit
        return redirect('/admin/clubhouses')
    form = PasswordChangeForm()
    working_id = session['edit_club_id']
    club_name = get_clubhouse_from_id(working_id)
    if request.method == 'POST': 
        if "cancel_btn" in request.form: # cancel update
            session.pop('edit_club_id')
            return redirect('/admin/clubhouses')
        # first check if password is valid
        if User(working_id).check_password(request.form['old_password']):
            if form.validate_on_submit():
                update_password(working_id, request.form['password'])
                session.pop('edit_club_id') # remove club_id from memory
                flash(_l("Password changed successfully."))
                return redirect('/admin/clubhouses')
        else:
            flash(_l("Incorrect password."))
    return render_template('/admin/change.html', form=form, clubhouse_name=club_name)

@app.route('/admin/addclubhouse', methods=['GET','POST'])
@fresh_login_required(access="admin")
def admin_clubhouses():
    form = ClubhouseAddForm()
    if request.method == "POST":
        if "cancel_btn" in request.form: # cancel clubhouse add
            return redirect('/admin/clubhouses')
        elif form.validate_on_submit():
            # TODO: add new clubhouse in database
            return redirect('/admin/clubhouses')
    return render_template('/admin/add.html', form=form)
