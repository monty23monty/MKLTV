from collections import defaultdict
from hashlib import sha256

from flask import request, render_template, flash, redirect, url_for, session, jsonify

from decorators import admin_required, user_required
from models import User, Team, Player, Fixture, FixtureStaff, StaffPosition, UserAvailability
from config import bcrypt, login_manager, app
from models import db
from forms import TeamForm, PlayerForm, FixtureForm, FixtureStaffForm, StaffPositionForm
from datetime import timedelta, datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/admin')
@admin_required
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('admin/index.html')


@app.route('/admin/register', methods=['get', 'POST'])
@admin_required
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_password, email=email, role=role)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('admin/register.html')


@app.route('/admin/users')
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/edit_user', methods=['GET', 'POST'])
@admin_required
def edit_user():
    if request.method == 'POST':
        user_id = request.form['user_id']
        user = User.query.filter_by(id=user_id).first()
        if user:
            user.username = request.form['username']
            password = request.form['password']
            if password:
                user.password = bcrypt.generate_password_hash(password).decode('utf-8')
            user.permission = request.form['permission']
            db.session.commit()
            return 'User updated'
        return 'User not found'
    return redirect(url_for('admin'))


@app.route('/admin/delete_user', methods=['GET'])
@admin_required
def delete_user():
    user_id = request.args.get('user_id')
    if user_id == session['user_id']:
        return 'You cannot delete yourself'
    if user_id is None:
        return 'User ID not provided'

    user = User.query.filter_by(id=user_id).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        return 'User deleted'
    return 'User not found'


@app.route('/admin/fixtures')
@admin_required
def fixtures():
    fixtures = Fixture.query.all()
    fixtures_data = []
    for fixture in fixtures:
        home_team = Team.query.get(fixture.HomeTeamID)
        away_team = Team.query.get(fixture.AwayTeamID)
        fixtures_data.append({
            'id': fixture.GameID,
            'home_team': home_team.TeamName,
            'away_team': away_team.TeamName,
            'date': fixture.Date,
            'location': fixture.Location
        })
    return render_template('admin/fixtures.html', fixtures=fixtures_data)


@app.route('/admin/fixtures/new', methods=['GET', 'POST'])
@admin_required
def new_fixture():
    if request.method == 'POST':
        home_team_id = request.form['home_team']
        away_team_id = request.form['away_team']
        date = request.form['date']
        time = request.form['time']
        location = request.form['location']

        # Combine date and time into a single datetime string
        datetime_str = f"{date} {time}:00"

        # Create a new fixture
        new_fixture = Fixture(
            Date=datetime_str,
            Location=location,
            HomeTeamID=home_team_id,
            AwayTeamID=away_team_id,
            live=False,
            completed=False
        )
        db.session.add(new_fixture)
        db.session.commit()
        flash('New fixture has been created!', 'success')
        return redirect(url_for('fixtures'))

    teams = Team.query.all()
    return render_template('admin/new_fixture.html', teams=teams)


@app.route('/admin/fixtures/<int:fixture_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_fixture(fixture_id):
    fixture = Fixture.query.get_or_404(fixture_id)
    form = FixtureForm(obj=fixture)
    form.HomeTeamID.choices = [(team.TeamID, team.TeamName) for team in Team.query.order_by('TeamName')]
    form.AwayTeamID.choices = [(team.TeamID, team.TeamName) for team in Team.query.order_by('TeamName')]

    if form.validate_on_submit():
        fixture.Date = form.DateTime.data.strftime('%Y-%m-%d %H:%M:%S')
        fixture.Location = form.Location.data
        fixture.HomeTeamID = form.HomeTeamID.data
        fixture.AwayTeamID = form.AwayTeamID.data
        fixture_end_time = form.DateTime.data + timedelta(hours=3)
        fixture.EndTime = fixture_end_time.strftime('%Y-%m-%d %H:%M:%S')
        db.session.commit()
        flash('Fixture has been updated!', 'success')
        return redirect(url_for('fixtures'))

    return render_template('admin/edit_fixture.html', form=form)


@app.route('/admin/fixtures/<int:fixture_id>/delete', methods=['POST'])
@admin_required
def delete_fixture(fixture_id):
    fixture = Fixture.query.get_or_404(fixture_id)
    db.session.delete(fixture)
    db.session.commit()
    flash('Fixture has been deleted!', 'success')
    return redirect(url_for('fixtures'))


@app.route('/admin/teams')
@admin_required
def teams():
    teams = Team.query.all()
    return render_template('admin/teams.html', teams=teams)


@app.route('/admin/teams/new', methods=['GET', 'POST'])
@admin_required
def new_team():
    form = TeamForm()
    if form.validate_on_submit():
        team = Team(TeamName=form.TeamName.data, Abbreviation=form.Abbreviation.data,
                    City=form.City.data, CoachName=form.CoachName.data, AssistantCoachName=form.AssistantCoachName.data)
        db.session.add(team)
        db.session.commit()
        flash('Team has been created!', 'success')
        return redirect(url_for('teams'))
    return render_template('admin/new_team.html', form=form)


@app.route('/admin/teams/<int:team_id>')
@admin_required
def team_detail(team_id):
    team = Team.query.get_or_404(team_id)
    return render_template('admin/team_detail.html', team=team)


@app.route('/admin/players/new', methods=['GET', 'POST'])
@admin_required
def new_player():
    form = PlayerForm()
    form.TeamID.choices = [(team.TeamID, team.TeamName) for team in Team.query.order_by('TeamName')]
    if form.validate_on_submit():
        player = Player(
            FirstName=form.FirstName.data,
            LastName=form.LastName.data,
            TeamID=form.TeamID.data,
            Position=form.Position.data,
            Shoots=form.Shoots.data,
            Height=form.Height.data,
            Weight=form.Weight.data,
            BirthDate=form.BirthDate.data,
            BirthCountry=form.BirthCountry.data
        )
        db.session.add(player)
        db.session.commit()
        flash('Player has been created!', 'success')
        return redirect(url_for('teams'))
    return render_template('admin/new_player.html', form=form)


@app.route('/admin/players/<int:player_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    form = PlayerForm(obj=player)
    form.TeamID.choices = [(team.TeamID, team.TeamName) for team in Team.query.order_by('TeamName')]
    if form.validate_on_submit():
        player.FirstName = form.FirstName.data
        player.LastName = form.LastName.data
        player.TeamID = form.TeamID.data
        player.Position = form.Position.data
        player.Shoots = form.Shoots.data
        player.Height = form.Height.data
        player.Weight = form.Weight.data
        player.BirthDate = form.BirthDate.data
        player.BirthCountry = form.BirthCountry.data
        db.session.commit()
        flash('Player has been updated!', 'success')
        return redirect(url_for('team_detail', team_id=player.TeamID))
    return render_template('admin/edit_player.html', form=form, player=player)


@app.route('/admin/staff_positions', methods=['GET', 'POST'])
@admin_required
def staff_positions():
    form = StaffPositionForm()
    if form.validate_on_submit():
        position = StaffPosition(name=form.name.data)
        db.session.add(position)
        db.session.commit()
        flash('Staff position has been created!', 'success')
        return redirect(url_for('staff_positions'))
    positions = StaffPosition.query.all()
    return render_template('admin/staff_positions.html', form=form, positions=positions)


@app.route('/admin/allocate_staff', methods=['GET', 'POST'])
@admin_required
def allocate_staff():
    form = FixtureStaffForm()
    form.fixture_id.choices = [(fixture.GameID, f"{fixture.home_team.TeamName} vs {fixture.away_team.TeamName} on {fixture.Date}") for fixture in Fixture.query.all()]
    form.user_id.choices = [(user.id, user.username) for user in User.query.all()]
    form.position_id.choices = [(position.id, position.name) for position in StaffPosition.query.all()]

    if form.validate_on_submit():
        fixture = Fixture.query.get(form.fixture_id.data)
        if fixture is None:
            flash('Selected fixture does not exist!', 'danger')
            return redirect(url_for('allocate_staff'))

        allocation = FixtureStaff(
            fixture_id=form.fixture_id.data,
            user_id=form.user_id.data,
            position_id=form.position_id.data
        )
        db.session.add(allocation)
        db.session.commit()
        flash('Staff has been allocated!', 'success')
        return redirect(url_for('allocate_staff'))

    # Fetch allocations and organize data
    allocations = FixtureStaff.query.all()
    fixtures = Fixture.query.all()
    positions = StaffPosition.query.all()

    allocation_table = {}
    user_dict = {user.id: {'username': user.username, 'user_id': user.id} for user in User.query.all()}
    for fixture in fixtures:
        allocation_table[fixture.GameID] = {position.id: None for position in positions}

    for allocation in allocations:
        allocation_table[allocation.fixture_id][allocation.position_id] = user_dict[allocation.user_id]

    return render_template('admin/allocate_staff.html', form=form, allocations=allocations, allocation_table=allocation_table, fixtures=fixtures, positions=positions)





@app.route('/admin/move_allocation', methods=['POST'])
@admin_required
def move_allocation():
    try:
        fixture_id = int(request.form.get('fixture_id'))
        user_id = int(request.form.get('user_id'))
        position_id = int(request.form.get('position_id'))
        new_position_id = int(request.form.get('new_position_id'))
    except ValueError as e:
        flash('Invalid data received!', 'danger')
        return redirect(url_for('allocate_staff'))

    print(f"Moving allocation for fixture_id: {fixture_id}, user_id: {user_id}, from position_id: {position_id} to new_position_id: {new_position_id}")

    allocation = db.session.query(FixtureStaff).filter_by(fixture_id=fixture_id, user_id=user_id, position_id=position_id).first()
    if allocation:
        allocation.position_id = new_position_id
        db.session.commit()
        flash('Staff allocation has been moved!', 'success')
    else:
        flash('Allocation not found!', 'danger')

    return redirect(url_for('allocate_staff'))


@app.route('/admin/remove_allocation', methods=['POST'])
@admin_required
def remove_allocation():
    try:
        fixture_id = int(request.form.get('fixture_id'))
        user_id = int(request.form.get('user_id'))
        position_id = int(request.form.get('position_id'))
    except ValueError as e:
        flash('Invalid data received!', 'danger')
        return redirect(url_for('allocate_staff'))

    print(f"Removing allocation for fixture_id: {fixture_id}, user_id: {user_id}, position_id: {position_id}")

    allocation = FixtureStaff.query.filter_by(fixture_id=fixture_id, user_id=user_id, position_id=position_id).first()
    if allocation:
        db.session.delete(allocation)
        db.session.commit()
        flash('Staff allocation has been removed!', 'success')
    else:
        flash('Allocation not found!', 'danger')

    return redirect(url_for('allocate_staff'))


@app.route('/')
def home():  # put application's code here
    if 'user_id' in session:
        user = User.query.filter_by(id=session['user_id']).first()
        if user.role == 'admin':
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('availability'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('admin' if user.role == 'admin' else 'home'))
        else:
            flash('Wrong username or password')
            return render_template('registration/login.html')

    if 'user_id' in session:
        user = User.query.filter_by(id=session['user_id']).first()
        if not user:
            session.pop('user_id', None)
            return "Error"
        if user.role == 'admin':
            return redirect(url_for('admin'))
        else:
            # The user is logged in but not an admin
            return render_template('some_user_homepage.html')

    return render_template('registration/login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))


@app.route('/availability', methods=['GET', 'POST'])
@user_required
def availability():
    user_id = session['user_id']
    fixtures = db.session.query(Fixture).all()
    if request.method == 'POST':
        for fixture in fixtures:
            available = request.form.get(f'fixture_{fixture.GameID}', 'off') == 'on'
            user_availability = UserAvailability.query.filter_by(user_id=user_id, fixture_id=fixture.GameID).first()
            if user_availability:
                user_availability.available = available
            else:
                new_availability = UserAvailability(user_id=user_id, fixture_id=fixture.GameID, available=available)
                db.session.add(new_availability)
        db.session.commit()
        flash('Availability updated!', 'success')
        return redirect(url_for('availability'))

    user_availabilities = {ua.fixture_id: ua.available for ua in
                           UserAvailability.query.filter_by(user_id=user_id).all()}

    # Group fixtures by month
    fixtures_by_month = defaultdict(list)
    for fixture in fixtures:
        month = datetime.strptime(fixture.Date, "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
        fixtures_by_month[month].append(fixture)

    return render_template('availability.html', fixtures_by_month=fixtures_by_month,
                           user_availabilities=user_availabilities)


@app.route('/get_available_users', methods=['GET'])
def get_available_users():
    fixture_id = request.args.get('fixture_id')
    if not fixture_id:
        return jsonify({'error': 'No fixture ID provided'}), 400

    available_users = db.session.query(User).join(UserAvailability).filter(
        UserAvailability.fixture_id == fixture_id,
        UserAvailability.available == True
    ).all()

    user_list = [{'id': user.id, 'username': user.username} for user in available_users]

    return jsonify(user_list)


@app.route('/my_allocations')
@user_required
def my_allocations():
    user_id = session['user_id']
    allocations = db.session.query(FixtureStaff).filter_by(user_id=user_id).all()
    fixtures = {allocation.fixture_id: allocation.fixture for allocation in allocations}
    positions = {allocation.position_id: allocation.position for allocation in allocations}

    return render_template('my_allocations.html', fixtures=fixtures, positions=positions, allocations=allocations)


if __name__ == '__main__':
    app.run(debug=True, host='192.168.2.205', port=5000, use_reloader=True)
