from collections import defaultdict
from hashlib import sha256

from flask import request, render_template, flash, redirect, url_for, session, jsonify

from decorators import admin_required, user_required
from models import User, Team, Player, Fixture, FixtureStaff, StaffPosition, UserAvailability, FixtureStaffDraft
from config import bcrypt, login_manager, app
from models import db
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


@app.route('/admin/register', methods=['GET', 'POST'])
@admin_required
def register():
    if request.method == 'POST':
        username = request.form['username'].upper()
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
        home_team_id = request.form['HomeTeamID']
        away_team_id = request.form['AwayTeamID']
        datetime_str = request.form['DateTime']
        location = request.form['Location']

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

    if request.method == 'POST':
        fixture.Date = request.form['DateTime']
        fixture.Location = request.form['Location']
        fixture.HomeTeamID = request.form['HomeTeamID']
        fixture.AwayTeamID = request.form['AwayTeamID']
        fixture.EndTime = (datetime.strptime(fixture.Date, '%Y-%m-%d %H:%M:%S') +
                           timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')

        db.session.commit()
        flash('Fixture has been updated!', 'success')
        return redirect(url_for('fixtures'))

    teams = Team.query.order_by('TeamName').all()
    return render_template('admin/edit_fixture.html', fixture=fixture, teams=teams)


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
    if request.method == 'POST':
        team_name = request.form['TeamName']
        abbreviation = request.form['Abbreviation']
        city = request.form['City']
        coach_name = request.form['CoachName']
        assistant_coach_name = request.form['AssistantCoachName']

        team = Team(
            TeamName=team_name,
            Abbreviation=abbreviation,
            City=city,
            CoachName=coach_name,
            AssistantCoachName=assistant_coach_name
        )
        db.session.add(team)
        db.session.commit()
        flash('Team has been created!', 'success')
        return redirect(url_for('teams'))

    return render_template('admin/new_team.html')



@app.route('/admin/teams/<int:team_id>')
@admin_required
def team_detail(team_id):
    team = Team.query.get_or_404(team_id)
    return render_template('admin/team_detail.html', team=team)


@app.route('/admin/players/new', methods=['GET', 'POST'])
@admin_required
def new_player():
    if request.method == 'POST':
        first_name = request.form['FirstName']
        last_name = request.form['LastName']
        team_id = request.form['TeamID']
        position = request.form['Position']
        shoots = request.form['Shoots']
        height = request.form['Height']
        weight = request.form['Weight']
        birth_date = request.form['BirthDate']
        birth_country = request.form['BirthCountry']

        player = Player(
            FirstName=first_name,
            LastName=last_name,
            TeamID=team_id,
            Position=position,
            Shoots=shoots,
            Height=height,
            Weight=weight,
            BirthDate=birth_date,
            BirthCountry=birth_country
        )
        db.session.add(player)
        db.session.commit()
        flash('Player has been created!', 'success')
        return redirect(url_for('teams'))

    teams = Team.query.order_by('TeamName').all()
    return render_template('admin/new_player.html', teams=teams)



@app.route('/admin/players/<int:player_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    if request.method == 'POST':
        player.FirstName = request.form['FirstName']
        player.LastName = request.form['LastName']
        player.TeamID = request.form['TeamID']
        player.Position = request.form['Position']
        player.Shoots = request.form['Shoots']
        player.Height = request.form['Height']
        player.Weight = request.form['Weight']
        player.BirthDate = request.form['BirthDate']
        player.BirthCountry = request.form['BirthCountry']
        db.session.commit()
        flash('Player has been updated!', 'success')
        return redirect(url_for('team_detail', team_id=player.TeamID))

    teams = Team.query.order_by('TeamName').all()
    return render_template('admin/edit_player.html', player=player, teams=teams)



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
    if request.method == 'POST':
        fixture_id = request.form['fixture_id']
        user_id = request.form['user_id']
        position_id = request.form['position_id']

        draft = FixtureStaffDraft(
            fixture_id=fixture_id,
            user_id=user_id,
            position_id=position_id
        )
        db.session.add(draft)
        db.session.commit()
        flash('Staff has been allocated in draft!', 'success')
        return redirect(url_for('allocate_staff'))

    fixtures = Fixture.query.all()
    positions = StaffPosition.query.all()
    users = User.query.all()

    draft_allocations = FixtureStaffDraft.query.all()
    allocation_table = {}
    for fixture in fixtures:
        allocation_table[fixture.GameID] = {position.id: None for position in positions}

    for allocation in draft_allocations:
        allocation_table[allocation.fixture_id][allocation.position_id] = allocation

    return render_template(
        'admin/allocate_staff.html',
        allocation_table=allocation_table,
        fixtures=fixtures,
        positions=positions,
        users=users
    )



@app.route('/admin/fixtures/publish_allocation/<int:fixture_id>', methods=['POST'])
@admin_required
def publish_allocation(fixture_id):
    # Get all draft records for this fixture
    draft_allocations = FixtureStaffDraft.query.filter_by(fixture_id=fixture_id).all()

    if not draft_allocations:
        flash('No draft allocations found for this fixture!', 'warning')
        return redirect(url_for('allocate_staff'))

    # Delete existing published allocations for this fixture
    FixtureStaff.query.filter_by(fixture_id=fixture_id).delete()

    # Copy draft allocations to published allocations
    for draft in draft_allocations:
        published = FixtureStaff(
            fixture_id=draft.fixture_id,
            user_id=draft.user_id,
            position_id=draft.position_id,
            published=True  # Mark as published
        )
        db.session.add(published)

    # Commit changes to the database
    db.session.commit()
    flash('All draft allocations for this fixture have been published successfully!', 'success')
    return redirect(url_for('allocate_staff'))


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

    print(f"Moving allocation for fixture_id: {fixture_id}, user_id: {user_id}, from position_id: {position_id}"
          f" to new_position_id: {new_position_id}")

    allocation = db.session.query(FixtureStaffDraft).filter_by(fixture_id=fixture_id, user_id=user_id,
                                                          position_id=position_id).first()
    if allocation:
        allocation.position_id = new_position_id
        db.session.commit()
        flash('Draft allocation has been moved!', 'success')
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

    allocation = FixtureStaffDraft.query.filter_by(fixture_id=fixture_id, user_id=user_id, position_id=position_id).first()
    if allocation:
        db.session.delete(allocation)
        db.session.commit()
        flash('Draft allocation has been removed!', 'success')
    else:
        flash('Allocation not found!', 'danger')

    return redirect(url_for('allocate_staff'))


@app.route('/')
def home():
    if 'user_id' in session:
        user = User.query.filter_by(id=session['user_id']).first()
        if not user:
            session.pop('user_id', None)
            return redirect(url_for('login'))
        is_admin = user.role == 'admin'
        return render_template('user_homepage.html', is_admin=is_admin)
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].upper()
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('admin' if user.role == 'admin' else 'home'))
        else:
            flash('Wrong username or password', 'danger')

    if 'user_id' in session:
        user = User.query.filter_by(id=session['user_id']).first()
        if not user:
            session.pop('user_id', None)
            return "Error"
        if user.role == 'admin':
            return redirect(url_for('admin'))
        else:
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

    user_availabilities = {ua.fixture_id: ua.available for ua in UserAvailability.query.filter_by(user_id=user_id).all()}

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
    allocations = db.session.query(FixtureStaff).filter_by(user_id=user_id, published=True).all()
    fixtures = {allocation.fixture_id: allocation.fixture for allocation in allocations}
    positions = {allocation.position_id: allocation.position for allocation in allocations}

    return render_template('my_allocations.html', fixtures=fixtures, positions=positions, allocations=allocations)


if __name__ == '__main__':

    app.run(debug=True, host='192.168.2.205', port=5000, use_reloader=True)

