from collections import defaultdict
from flask import request, render_template, flash, redirect, url_for, session, jsonify
from decorators import admin_required, user_required
from models import User, Team, Player, Fixture, FixtureStaff, StaffPosition, UserAvailability, FixtureStaffDraft
from config import bcrypt, login_manager, app, send_allocation_email, generate_token, confirm_token
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


@app.route('/admin/register', methods=['get', 'POST'])
@admin_required
def register():
    if request.method == 'POST':
        username = request.form['username'].upper()
        email = request.form['email']
        role = request.form['role']

        # Create a new user without a password initially
        user = User(username=username, email=email, role=role, password='')
        db.session.add(user)
        db.session.commit()

        # Generate a token
        token = generate_token(user.email)

        # Construct the URL for setting the password
        set_password_url = url_for('set_password', token=token, _external=True)

        # Send the email via AWS SES
        subject = "Complete Your Registration"
        body_text = f"Dear {username},\n\nPlease click the link below to set your password and complete your registration:\n\n{set_password_url}\n\nThank you."

        send_allocation_email(user.email, subject, body_text)

        flash('A registration email has been sent to the user.', 'success')
        return redirect(url_for('admin'))
    return render_template('admin/register.html')


@app.route('/set_password/<token>', methods=['GET', 'POST'])
def set_password(token):
    email = confirm_token(token)
    if not email:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first_or_404()

    if request.method == 'POST':
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user.password = hashed_password
        db.session.commit()

        flash('Your password has been set. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('registration/set_password.html')


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username'].upper()
        user = User.query.filter_by(username=username).first()

        if user:
            # Generate a token
            token = generate_token(user.email)

            # Construct the URL for resetting the password
            reset_password_url = url_for('reset_password', token=token, _external=True)

            # Send the email via AWS SES
            subject = "Password Reset Request"
            body_text = f"Dear {user.username},\n\nPlease click the link below to reset your password:\n\n{reset_password_url}\n\nIf you did not request this password reset, please ignore this email.\n\nThank you."

            send_allocation_email(user.email, subject, body_text)

            flash('An email has been sent with instructions to reset your password.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username not found.', 'danger')

    return render_template('registration/forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = confirm_token(token)
    if not email:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first_or_404()

    if request.method == 'POST':
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user.password = hashed_password
        db.session.commit()

        flash('Your password has been reset. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('registration/reset_password.html')


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

    if request.method == 'POST':
        fixture.HomeTeamID = request.form['HomeTeamID']
        fixture.AwayTeamID = request.form['AwayTeamID']
        fixture.Date = f"{request.form['Date']} {request.form['Time']}:00"
        fixture.Location = request.form['Location']
        fixture_end_time = datetime.strptime(fixture.Date, '%Y-%m-%d %H:%M:%S') + timedelta(hours=3)
        fixture.EndTime = fixture_end_time.strftime('%Y-%m-%d %H:%M:%S')

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

        # Create a new team
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

        # Create a new player
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
        # Retrieve form data from the request
        first_name = request.form['FirstName']
        last_name = request.form['LastName']
        team_id = request.form['TeamID']
        position = request.form['Position']
        shoots = request.form['Shoots']
        height = request.form['Height']
        weight = request.form['Weight']
        birth_date = request.form['BirthDate']
        birth_country = request.form['BirthCountry']

        # Update the player's details
        player.FirstName = first_name
        player.LastName = last_name
        player.TeamID = team_id
        player.Position = position
        player.Shoots = shoots
        player.Height = height
        player.Weight = weight
        player.BirthDate = birth_date
        player.BirthCountry = birth_country

        db.session.commit()
        flash('Player has been updated!', 'success')
        return redirect(url_for('team_detail', team_id=player.TeamID))

    # Get list of teams for the dropdown
    teams = Team.query.order_by('TeamName').all()
    return render_template('admin/edit_player.html', player=player, teams=teams)


@app.route('/admin/staff_positions', methods=['GET', 'POST'])
@admin_required
def staff_positions():
    if request.method == 'POST':
        position_name = request.form['name']

        # Create a new staff position
        position = StaffPosition(name=position_name)
        db.session.add(position)
        db.session.commit()
        flash('Staff position has been created!', 'success')
        return redirect(url_for('staff_positions'))

    # Fetch all staff positions to display
    positions = StaffPosition.query.all()
    return render_template('admin/staff_positions.html', positions=positions)


@app.route('/admin/allocate_staff', methods=['GET', 'POST'])
@admin_required
def allocate_staff():
    if request.method == 'POST':
        fixture_id = request.form['fixture_id']
        user_id = request.form['user_id']
        position_id = request.form['position_id']

        # Check if the fixture exists
        fixture = Fixture.query.get(fixture_id)
        if fixture is None:
            flash('Selected fixture does not exist!', 'danger')
            return redirect(url_for('allocate_staff'))

        # Save the allocation to the draft table
        draft_allocation = FixtureStaffDraft.query.filter_by(fixture_id=fixture_id, user_id=user_id).first()
        if draft_allocation:
            draft_allocation.position_id = position_id
        else:
            draft_allocation = FixtureStaffDraft(
                fixture_id=fixture_id,
                user_id=user_id,
                position_id=position_id
            )
            db.session.add(draft_allocation)

        db.session.commit()
        flash('Staff allocation draft saved!', 'success')
        return redirect(url_for('allocate_staff'))

    fixtures = Fixture.query.all()
    users = User.query.all()
    positions = StaffPosition.query.all()

    # Prepare choices for the select fields
    fixture_choices = [
        (fixture.GameID, f"{fixture.home_team.TeamName} vs {fixture.away_team.TeamName} on {fixture.Date}") for fixture
        in fixtures]
    user_choices = [(user.id, user.username) for user in users]
    position_choices = [(position.id, position.name) for position in positions]

    # Fetch only draft allocations and organize data
    draft_allocations = FixtureStaffDraft.query.all()

    allocation_table = {}
    user_dict = {user.id: {'username': user.username, 'user_id': user.id} for user in users}
    unpublished_fixtures = set()

    for fixture in fixtures:
        allocation_table[fixture.GameID] = {position.id: None for position in positions}

    for draft_allocation in draft_allocations:
        allocation_table[draft_allocation.fixture_id][draft_allocation.position_id] = user_dict[draft_allocation.user_id]
        unpublished_fixtures.add(draft_allocation.fixture_id)

    return render_template(
        'admin/allocate_staff.html',
        fixture_choices=fixture_choices,
        user_choices=user_choices,
        position_choices=position_choices,
        allocation_table=allocation_table,
        fixtures=fixtures,
        positions=positions,
        unpublished_fixtures=unpublished_fixtures
    )


@app.route('/admin/publish_allocations/<int:fixture_id>', methods=['POST'])
@admin_required
def publish_allocations(fixture_id):
    # Remove existing allocations for this fixture in the published table
    FixtureStaff.query.filter_by(fixture_id=fixture_id).delete()

    # Copy draft allocations to the published table without clearing the draft table
    draft_allocations = FixtureStaffDraft.query.filter_by(fixture_id=fixture_id).all()

    for draft in draft_allocations:
        published_allocation = FixtureStaff(
            fixture_id=draft.fixture_id,
            user_id=draft.user_id,
            position_id=draft.position_id
        )
        db.session.add(published_allocation)

        # Fetch the position name
        position = StaffPosition.query.get(draft.position_id)
        position_name = position.name if position else "Unknown Position"

        # Send email notification to the affected user
        user = User.query.get(draft.user_id)
        fixture = Fixture.query.get(fixture_id)
        subject = "Allocation Change Notification"
        body_text = f"Dear {user.username},\n\nYour allocation for the fixture between {fixture.home_team.TeamName} and {fixture.away_team.TeamName} on {fixture.Date} has been updated. Your new position is {position_name}.\n\nThank you."
        send_allocation_email(user.email, subject, body_text)

    db.session.commit()
    flash('Allocations have been published and notifications sent!', 'success')
    return redirect(url_for('allocate_staff'))


@app.route('/admin/move_allocation', methods=['POST'])
@admin_required
def move_allocation():
    try:
        fixture_id = int(request.form.get('fixture_id'))
        user_id = int(request.form.get('user_id'))
        position_id = int(request.form.get('position_id'))
        new_position_id = int(request.form.get('new_position_id'))
    except ValueError:
        flash('Invalid data received!', 'danger')
        return redirect(url_for('allocate_staff'))

    allocation = db.session.query(FixtureStaffDraft).filter_by(fixture_id=fixture_id, user_id=user_id, position_id=position_id).first()
    if allocation:
        allocation.position_id = new_position_id
        db.session.commit()
        flash('Draft allocation has been moved!', 'success')
    else:
        flash('Draft allocation not found!', 'danger')

    return redirect(url_for('allocate_staff'))

@app.route('/admin/remove_allocation', methods=['POST'])
@admin_required
def remove_allocation():
    try:
        fixture_id = int(request.form.get('fixture_id'))
        user_id = int(request.form.get('user_id'))
        position_id = int(request.form.get('position_id'))
    except ValueError:
        flash('Invalid data received!', 'danger')
        return redirect(url_for('allocate_staff'))

    allocation = FixtureStaffDraft.query.filter_by(fixture_id=fixture_id, user_id=user_id, position_id=position_id).first()
    if allocation:
        db.session.delete(allocation)
        db.session.commit()
        flash('Draft allocation has been removed!', 'success')
    else:
        flash('Draft allocation not found!', 'danger')

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

    # Fetch only the published allocations
    allocations = db.session.query(FixtureStaff).filter_by(user_id=user_id).all()

    # Get the related fixtures and positions
    fixtures = {allocation.fixture_id: allocation.fixture for allocation in allocations}
    positions = {allocation.position_id: allocation.position for allocation in allocations}

    return render_template('my_allocations.html', fixtures=fixtures, positions=positions, allocations=allocations)


if __name__ == '__main__':
    app.run(debug=True, host='192.168.2.205', port=5000, use_reloader=True)
