from flask import request, render_template, flash, redirect, url_for, session, jsonify
import requests
from flask import request, render_template, flash, redirect, url_for, session, jsonify

from config import bcrypt, login_manager, app, send_allocation_email, generate_token, confirm_token, socketio
from decorators import admin_required, user_required
from models import User, Team, Player, FixtureStaff, StaffPosition, UserAvailability, FixtureStaffDraft, \
    GameStats, Game, LiveGame, Scoreboard
from models import db


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
def register():
    if request.method == 'POST':
        username = request.form['username'].upper()
        email = request.form['email']
        role = request.form['role']

        user = User(username=username, email=email, role=role, password='')
        db.session.add(user)
        db.session.commit()

        token = generate_token(user.email)
        set_password_url = url_for('set_password', token=token, _external=True)

        subject = "Complete Your Registration"
        body_text = (f"Dear {username},\n\n You have been registered for a lightning TV {role} account.\n\n"
                     f"Your username is: {username}\n\n"
                     f"Please click the link below to set your password and complete your registration:\n\n"
                     f"{set_password_url}\n\nIf you have any questions, please contact Leo\n\nThank you.")

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
            token = generate_token(user.email)
            reset_password_url = url_for('reset_password', token=token, _external=True)

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
    fixtures = Game.query.filter(Game.completed == False).order_by(Game.Date.asc()).all()

    fixtures_data = []
    for fixture in fixtures:
        status = "Scheduled"
        if fixture.live:
            status = "Live"

        home_team = Team.query.get(fixture.HomeTeamID)
        away_team = Team.query.get(fixture.AwayTeamID)
        fixtures_data.append({
            'id': fixture.GameID,
            'home_team': home_team.TeamName,
            'away_team': away_team.TeamName,
            'date': fixture.Date,
            'location': fixture.Location,
            'status': status
        })

    return render_template('admin/fixtures.html', fixtures=fixtures_data)


@app.route('/admin/games/new', methods=['GET', 'POST'])
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
        start_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')

        # Calculate end time as 3 hours after start time
        end_time = start_time + timedelta(hours=3)

        # Create a new game
        new_game = Game(
            Date=start_time.strftime('%Y-%m-%d %H:%M:%S'),
            EndTime=end_time.strftime('%Y-%m-%d %H:%M:%S'),  # Set end time to 3 hours after start time
            Location=location,
            HomeTeamID=home_team_id,
            AwayTeamID=away_team_id,
            live=False,
            completed=False
        )
        db.session.add(new_game)
        db.session.commit()
        flash('New game has been created!', 'success')
        return redirect(url_for('fixtures'))

    teams = Team.query.all()
    return render_template('admin/new_fixture.html', teams=teams)


@app.route('/admin/fixtures/<int:fixture_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_fixture(fixture_id):
    fixture = Game.query.get_or_404(fixture_id)

    if request.method == 'POST':
        fixture.HomeTeamID = request.form['HomeTeamID']
        fixture.AwayTeamID = request.form['AwayTeamID']

        # Here, we capture the combined date and time from the DateTime input
        fixture.Date = request.form['DateTime'].replace('T', ' ') + ":00"

        fixture.Location = request.form['Location']

        # Calculate the fixture end time, assuming it's 3 hours after the start time
        fixture_end_time = datetime.strptime(fixture.Date, '%Y-%m-%d %H:%M:%S') + timedelta(hours=3)
        fixture.EndTime = fixture_end_time.strftime('%Y-%m-%d %H:%M:%S')

        # Update live status based on checkbox
        fixture.live = 'Live' in request.form

        db.session.commit()
        flash('Fixture has been updated!', 'success')
        return redirect(url_for('fixtures'))

    teams = Team.query.order_by('TeamName').all()
    return render_template('admin/edit_fixture.html', fixture=fixture, teams=teams)




@app.route('/admin/fixtures/<int:fixture_id>/delete', methods=['POST'])
@admin_required
def delete_fixture(fixture_id):
    fixture = Game.query.get_or_404(fixture_id)
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
    # Fetch the team by ID, or return a 404 error if not found
    team = Team.query.get_or_404(team_id)

    # Fetch all players associated with this team
    players = Player.query.filter_by(TeamID=team.TeamID).all()

    # Render the template and pass the team and players data to it
    return render_template('admin/team_detail.html', team=team, players=players)



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
        first_name = request.form['FirstName']
        last_name = request.form['LastName']
        team_id = request.form['TeamID']
        position = request.form['Position']
        shoots = request.form['Shoots']
        height = request.form['Height']
        weight = request.form['Weight']
        birth_date = request.form['BirthDate']
        birth_country = request.form['BirthCountry']

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

    teams = Team.query.order_by('TeamName').all()
    return render_template('admin/edit_player.html', player=player, teams=teams)


@app.route('/admin/staff_positions', methods=['GET', 'POST'])
@admin_required
def staff_positions():
    if request.method == 'POST':
        position_name = request.form['name']

        position = StaffPosition(name=position_name)
        db.session.add(position)
        db.session.commit()
        flash('Staff position has been created!', 'success')
        return redirect(url_for('staff_positions'))

    positions = StaffPosition.query.all()
    return render_template('admin/staff_positions.html', positions=positions)


@app.route('/admin/allocate_staff', methods=['GET', 'POST'])
@admin_required
def allocate_staff():
    if request.method == 'POST':
        game_id = request.form['game_id']
        user_id = request.form['user_id']
        position_id = request.form['position_id']
        app.logger.debug(f"Received game_id: {game_id}, user_id: {user_id}, position_id: {position_id}")
        game = Game.query.get(game_id)
        if game is None:
            flash('Selected game does not exist!', 'danger')
            return redirect(url_for('allocate_staff'))

        draft_allocation = FixtureStaffDraft.query.filter_by(game_id=game_id, user_id=user_id).first()
        if draft_allocation:
            draft_allocation.position_id = position_id
        else:
            draft_allocation = FixtureStaffDraft(
                game_id=game_id,
                user_id=user_id,
                position_id=position_id
            )
            db.session.add(draft_allocation)

        db.session.commit()
        flash('Staff allocation draft saved!', 'success')
        return redirect(url_for('allocate_staff'))

    games = Game.query.order_by(Game.Date.asc()).all()  # Sort games by date
    users = User.query.all()
    positions = StaffPosition.query.all()

    game_choices = [
        (game.GameID, f"{game.home_team.TeamName} vs {game.away_team.TeamName} on {game.Date}") for game in games
    ]
    user_choices = [(user.id, user.username) for user in users]
    position_choices = [(position.id, position.name) for position in positions]

    draft_allocations = FixtureStaffDraft.query.all()

    allocation_table = {}
    user_dict = {user.id: {'username': user.username, 'user_id': user.id} for user in users}
    unpublished_games = set()

    for game in games:
        allocation_table[game.GameID] = {position.id: None for position in positions}

    for draft_allocation in draft_allocations:
        allocation_table[draft_allocation.game_id][draft_allocation.position_id] = user_dict[draft_allocation.user_id]
        unpublished_games.add(draft_allocation.game_id)

    return render_template(
        'admin/allocate_staff.html',
        game_choices=game_choices,
        user_choices=user_choices,
        position_choices=position_choices,
        allocation_table=allocation_table,
        games=games,
        positions=positions,
        unpublished_games=unpublished_games
    )


@app.route('/admin/publish_allocations/<int:game_id>', methods=['POST'])
@admin_required
def publish_allocations(game_id):
    # Remove existing allocations for this game in the published table
    FixtureStaff.query.filter_by(game_id=game_id).delete()  # Changed fixture_id to game_id

    # Copy draft allocations to the published table without clearing the draft table
    draft_allocations = FixtureStaffDraft.query.filter_by(game_id=game_id).all()  # Changed fixture_id to game_id

    for draft in draft_allocations:
        published_allocation = FixtureStaff(
            game_id=draft.game_id,  # Changed fixture_id to game_id
            user_id=draft.user_id,
            position_id=draft.position_id
        )
        db.session.add(published_allocation)

        # Fetch the position name
        position = StaffPosition.query.get(draft.position_id)
        position_name = position.name if position else "Unknown Position"

        # Send email notification to the affected user
        user = User.query.get(draft.user_id)
        game = Game.query.get(game_id)  # Changed Fixture to Game and fixture_id to game_id
        subject = "Allocation Change Notification"
        body_text = f"Dear {user.username},\n\nYour allocation for the game between {game.home_team.TeamName} and {game.away_team.TeamName} on {game.Date} has been updated. Your new position is {position_name}.\n\nThank you."
        send_allocation_email(user.email, subject, body_text)

    db.session.commit()
    flash('Allocations have been published and notifications sent!', 'success')
    return redirect(url_for('allocate_staff'))


@app.route('/admin/move_allocation', methods=['POST'])
@admin_required
def move_allocation():
    try:
        game_id = int(request.form.get('game_id'))  # Updated to game_id
        user_id = int(request.form.get('user_id'))
        position_id = int(request.form.get('position_id'))
        new_position_id = int(request.form.get('new_position_id'))
    except ValueError:
        flash('Invalid data received!', 'danger')
        return redirect(url_for('allocate_staff'))

    allocation = db.session.query(FixtureStaffDraft).filter_by(game_id=game_id, user_id=user_id, position_id=position_id).first()  # Updated to game_id
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
        game_id = int(request.form.get('game_id'))  # Updated to game_id
        user_id = int(request.form.get('user_id'))
        position_id = int(request.form.get('position_id'))
    except ValueError:
        flash('Invalid data received!', 'danger')
        return redirect(url_for('allocate_staff'))

    allocation = FixtureStaffDraft.query.filter_by(game_id=game_id, user_id=user_id, position_id=position_id).first()  # Updated to game_id
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


from collections import defaultdict


@app.route('/availability', methods=['GET', 'POST'])
@user_required
def availability():
    user_id = session['user_id']
    games = db.session.query(Game).order_by(Game.Date.asc()).all()  # Sort the games by date

    if request.method == 'POST':
        for game in games:
            available = request.form.get(f'game_{game.GameID}', 'off') == 'on'
            user_availability = UserAvailability.query.filter_by(user_id=user_id, game_id=game.GameID).first()

            if user_availability:
                user_availability.available = available
            else:
                new_availability = UserAvailability(user_id=user_id, game_id=game.GameID, available=available)
                db.session.add(new_availability)

        db.session.commit()
        flash('Availability updated!', 'success')
        return redirect(url_for('availability'))

    user_availabilities = {ua.game_id: ua.available for ua in UserAvailability.query.filter_by(user_id=user_id).all()}

    games_by_month = defaultdict(list)
    for game in games:
        month = datetime.strptime(game.Date, "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
        games_by_month[month].append(game)

    return render_template('availability.html', games_by_month=games_by_month, user_availabilities=user_availabilities)


@app.route('/get_available_users', methods=['GET'])
def get_available_users():
    game_id = request.args.get('game_id')
    if not game_id:
        return jsonify({'error': 'No game ID provided'}), 400

    available_users = db.session.query(User).join(UserAvailability).filter(
        UserAvailability.game_id == game_id,
        UserAvailability.available == True
    ).all()

    user_list = [{'id': user.id, 'username': user.username} for user in available_users]

    return jsonify(user_list)



@app.route('/my_allocations')
@user_required
def my_allocations():
    user_id = session['user_id']

    # Query for all allocations where the current user is involved
    user_allocations = db.session.query(FixtureStaff).filter_by(user_id=user_id).all()

    # Get the game IDs the user is assigned to
    game_ids = [allocation.game_id for allocation in user_allocations]

    # Query for all allocations related to these games
    allocations = db.session.query(FixtureStaff).filter(FixtureStaff.game_id.in_(game_ids)).all()

    # Build dictionaries for related games, positions, and users
    games = {allocation.game_id: allocation.game for allocation in allocations}
    positions = {allocation.position_id: allocation.position for allocation in allocations}
    users = {allocation.user_id: allocation.user for allocation in allocations}

    return render_template('my_allocations.html', games=games, positions=positions, users=users, allocations=allocations)



@app.route('/admin/set_live/<int:game_id>', methods=['POST'])
@admin_required
def set_live(game_id):
    # Ensure no other game is live
    live_game = Game.query.filter_by(live=True).first()
    if live_game:
        flash('Another game is currently live. Please complete it before starting a new one.', 'danger')
        return redirect(url_for('fixtures'))

    # Set the selected game as live
    game = Game.query.get_or_404(game_id)
    game.live = True
    db.session.commit()

    flash(f'Game {game.GameID} is now live!', 'success')

    # Redirect to the live game page (admin view)
    return redirect(url_for('admin_live_game'))


@app.route('/admin/complete_live_game', methods=['GET'])
@admin_required
def complete_live_game():
    # Find the currently live game
    live_game = Game.query.filter_by(live=True).first()

    if not live_game:
        flash('No live game to complete.', 'danger')
        return redirect(url_for('fixtures'))

    # Mark the game as completed
    live_game.completed = True
    live_game.live = False
    db.session.commit()

    # Clear the corresponding LiveGame entry if it exists
    live_game_data = LiveGame.query.filter_by(game_id=live_game.GameID).first()
    if live_game_data:
        db.session.delete(live_game_data)
        db.session.commit()

    flash(f'Game {live_game.GameID} has been completed and live data cleared.', 'success')
    return redirect(url_for('fixtures'))


@app.route('/live', methods=['GET'])
def live_game():
    # Fetch the current live game record
    live_game = LiveGame.query.first()  # Assuming only one game can be live at a time

    if live_game:
        # Access the related Game object via the relationship
        game = live_game.game
        if game:
            # Get the names of the home and away teams
            home_team_name = game.home_team.TeamName
            away_team_name = game.away_team.TeamName
        else:
            # Handle the case where the related Game record is not found
            flash('The game associated with the live event does not exist.', 'danger')
            return redirect(url_for('home'))

        # Render the live game page with the relevant data
        return render_template('public/live_game.html',
                               live_game=live_game,
                               home_team_name=home_team_name,
                               away_team_name=away_team_name)
    else:
        # Render the intermediate page if no live game is active
        return render_template('public/live_game_intermediate.html')



@app.route('/admin/live', methods=['GET', 'POST'])
@admin_required
def admin_live_game():
    live_game = Game.query.filter_by(live=True).first()

    if not live_game:
        return render_template('admin/admin_live_placeholder.html')  # Placeholder if no game is live

    if request.method == 'POST':
        # Handle editable stats here
        game_stats = GameStats.query.filter_by(game_id=live_game.GameID).first()
        game_stats.home_sog = request.form.get('home_sog', game_stats.home_sog)
        game_stats.away_sog = request.form.get('away_sog', game_stats.away_sog)
        db.session.commit()
        flash('Stats updated!', 'success')

    return render_template('admin/admin_live_game.html', game=live_game)  # Admin view with editable stats


@app.route('/api/sog', methods=['GET'])
def sog():
    live_game = Game.query.filter_by(live=True).first()

    if live_game:
        game_stats = GameStats.query.filter_by(game_id=live_game.GameID).first()

        if game_stats:
            home_sog = game_stats.home_sog
            away_sog = game_stats.away_sog

            return jsonify({'home_sog': home_sog, 'away_sog': away_sog}), 200
        else:
            return jsonify({'error': 'Game stats not found for the live game.'}), 404
    else:
        return jsonify({'error': 'No live game found.'}), 404


@app.route('/api/sog/<int:end>', methods=['GET', 'POST'])
def sog_team(end):
    live_game = Game.query.filter_by(live=True).first()

    if not live_game:
        return jsonify({'error': 'No live game found.'}), 404

    live_game_data = LiveGame.query.filter_by(game_id=live_game.GameID).first()

    if not live_game_data:
        return jsonify({'error': 'Live game data not found for the live game.'}), 404

    def determine_team_shooting_at_end(period, end):
        if period in ["1st", "3rd"]:
            if end == 2:
                return live_game.HomeTeamID
            elif end == 10:
                return live_game.AwayTeamID
        elif period == "2nd":
            if end == 2:
                return live_game.AwayTeamID
            elif end == 10:
                return live_game.HomeTeamID
        return None

    team_shooting_at_end = determine_team_shooting_at_end(live_game_data.period, end)

    if not team_shooting_at_end:
        print(f"Invalid end or period: {end}, {live_game_data.period}")
        return jsonify({'error': 'Invalid end or period.'}), 400

    if request.method == 'GET':
        if team_shooting_at_end == live_game.HomeTeamID:
            return jsonify({'end': end, 'sog': live_game_data.home_team_sog}), 200
        elif team_shooting_at_end == live_game.AwayTeamID:
            return jsonify({'end': end, 'sog': live_game_data.away_team_sog}), 200
        else:
            return jsonify({'error': 'Error determining team shooting at this end.'}), 500

    elif request.method == 'POST':
        data = request.get_json()
        sog_value = data.get('sog')

        if sog_value is None:
            return jsonify({'error': 'SOG value is required.'}), 400

        if team_shooting_at_end == live_game.HomeTeamID:
            live_game_data.home_team_sog = sog_value
            updated_sog = live_game_data.home_team_sog
            socketio.emit('update_value', {'elementId': 'home-sog', 'value': updated_sog})
        elif team_shooting_at_end == live_game.AwayTeamID:
            live_game_data.away_team_sog = sog_value
            updated_sog = live_game_data.away_team_sog
            socketio.emit('update_value', {'elementId': 'away-sog', 'value': updated_sog})
        else:
            return jsonify({'error': 'Error determining team shooting at this end.'}), 500

        db.session.commit()
        return jsonify({'message': 'SOG updated successfully.', 'sog': updated_sog}), 200


# POST /goals/<teamid>: Increment the goal count for the given team
@app.route('/goals/<int:team_id>', methods=['POST'])
def add_goal(team_id):
    live_game = Game.query.filter_by(live=True).first()

    if not live_game:
        return jsonify({'error': 'No live game found'}), 404

    game_stats = GameStats.query.filter_by(game_id=live_game.GameID).first()

    if not game_stats:
        return jsonify({'error': 'Game stats not found for the live game.'}), 404

    if team_id == live_game.HomeTeamID:
        game_stats.home_sog += 1
        db.session.commit()
        return jsonify({'message': 'Goal added to home team', 'home_goals': game_stats.home_sog}), 200
    elif team_id == live_game.AwayTeamID:
        game_stats.away_sog += 1
        db.session.commit()
        return jsonify({'message': 'Goal added to away team', 'away_goals': game_stats.away_sog}), 200
    else:
        return jsonify({'error': 'Team ID not found in the current live game.'}), 404


@app.route('/goals/<int:team_id>', methods=['GET'])
def get_team_goals(team_id):
    live_game = Game.query.filter_by(live=True).first()

    if not live_game:
        return jsonify({'error': 'No live game found'}), 404

    game_stats = GameStats.query.filter_by(game_id=live_game.GameID).first()

    if not game_stats:
        return jsonify({'error': 'Game stats not found for the live game.'}), 404

    if team_id == live_game.HomeTeamID:
        return jsonify({'home_goals': game_stats.home_sog}), 200
    elif team_id == live_game.AwayTeamID:
        return jsonify({'away_goals': game_stats.away_sog}), 200
    else:
        return jsonify({'error': 'Team ID not found in the current live game.'}), 404


# GET /goals: Retrieve the goal count for both teams
@app.route('/goals', methods=['GET'])
def get_all_goals():
    live_game = Game.query.filter_by(live=True).first()

    if not live_game:
        return jsonify({'error': 'No live game found'}), 404

    game_stats = GameStats.query.filter_by(game_id=live_game.GameID).first()

    if not game_stats:
        return jsonify({'error': 'Game stats not found for the live game.'}), 404

    return jsonify({
        'home_goals': game_stats.home_sog,
        'away_goals': game_stats.away_sog
    }), 200


@app.route('/admin/availability_matrix')
@admin_required
def availability_matrix():
    # Fetch all users
    users = User.query.all()

    # Fetch all fixtures
    fixtures = Game.query.order_by(Game.Date.asc()).all()

    # Fetch availability
    availability = UserAvailability.query.all()

    # Create a dictionary to map availability
    availability_map = {}
    for avail in availability:
        if avail.game_id not in availability_map:
            availability_map[avail.game_id] = {}
        availability_map[avail.game_id][avail.user_id] = avail.available

    return render_template('admin/availability_matrix.html', users=users, fixtures=fixtures, availability_map=availability_map)


from datetime import datetime, timedelta


@app.route('/admin/add_games/<int:team_id>', methods=['POST', 'GET'])
@admin_required
def add_games(team_id):
    # Mapping of API team IDs to your database team IDs
    team_id_mapping = {
        5: 1,   # API ID 5 -> Your DB ID 1 (Milton Keynes Lightning)
        14: 2,  # API ID 14 -> Your DB ID 2 (Moskitos)
        1: 3,   # API ID 1 -> Your DB ID 3 (Berkshire BEES)
        4: 9,   # API ID 4 -> Your DB ID 5 (Leeds Knights)
        8: 5,   # API ID 8 -> Your DB ID 6 (Sheffield Steeldogs)
        9: 6,   # API ID 9 -> Your DB ID 7 (Solway Sharks)
        3: 7,   # API ID 3 -> Your DB ID 8 (Hull Seahawks)
        2: 8,   # API ID 2 -> Your DB ID 9 (Bristol Pitbulls)
        6: 10,  # API ID 6 -> Your DB ID 10 (Peterborough Phantoms)
        11: 11, # API ID 11 -> Your DB ID 11 (Telford Tigers)
        10: 12, # API ID 10 -> Your DB ID 12 (Swindon Wildcats)
        7: 4    # API ID 7 -> Your DB ID 4 (Romford Raiders)
    }

    leagues = [1, 3]
    season = 2024
    milton_keynes_arena = "Planet Ice, 1 S Row, Elder Gate, Milton Keynes, MK9 1DL"

    api_url_template = "https://s3-eu-west-1.amazonaws.com/nihl.hokejovyzapis.cz/league-team-matches/{season}/{league}/{team}.json"

    for league_id in leagues:
        api_url = api_url_template.format(season=season, league=league_id, team=team_id)

        response = requests.get(api_url)

        if response.status_code != 200:
            flash(f"Failed to fetch data for League {league_id}.", 'danger')
            continue

        try:
            data = response.json()
            print(f"API Response for League {league_id}: {data}")  # Debugging line
        except ValueError:
            flash(f"Invalid JSON response for League {league_id}.", 'danger')
            continue

        # The response is expected to be a dictionary with a 'matches' key containing a list of games
        if 'matches' not in data or not isinstance(data['matches'], list):
            flash(f"Unexpected data structure from API for League {league_id}.", 'danger')
            continue

        games = data['matches']  # Access the list of games

        for game in games:
            if not isinstance(game, dict):
                flash(f"Invalid game data format for League {league_id}.", 'danger')
                continue

            # Only save home games
            if game['arena'] != milton_keynes_arena:
                continue

            home_team_id = team_id_mapping.get(game['home']['id'])
            away_team_id = team_id_mapping.get(game['guest']['id'])

            if home_team_id is None:
                print(f"Unrecognized home team ID {game['home']['id']} for game: {game}")
                flash(f"Unrecognized home team ID {game['home']['id']} in League {league_id}.", 'danger')
                continue

            if away_team_id is None:
                print(f"Unrecognized away team ID {game['guest']['id']} for game: {game}")
                flash(f"Unrecognized away team ID {game['guest']['id']} in League {league_id}.", 'danger')
                continue

            # Calculate end time as 3 hours after faceoff
            faceoff_time = datetime.strptime(game['start_date'], '%Y-%m-%d %H:%M:%S')
            end_time = faceoff_time + timedelta(hours=3)

            existing_game = Game.query.filter_by(GameID=game['id']).first()
            if existing_game:
                flash(f"Game {game['id']} already exists in the database.", 'info')
                continue

            new_game = Game(
                GameID=game['id'],
                Date=game['start_date'],
                EndTime=end_time.strftime('%Y-%m-%d %H:%M:%S'),
                Location="Home",  # Set location to "Home"
                HomeTeamID=home_team_id,
                AwayTeamID=away_team_id,
                live=False,
                completed=game['status'] == 'AFTER_MATCH'
            )

            db.session.add(new_game)

        db.session.commit()
        flash(f"Home games for League {league_id} have been added.", 'success')

    return jsonify({"message": "Home games added successfully"}), 201

from flask_socketio import emit

@app.route('/api/scoreboard_live_data', methods=['POST'])
def ingest_scoreboard_data():
    data = request.get_json()

    # Extract data from the POST request
    home_score = int(data.get('Home score', 0))
    away_score = int(data.get('Away Score', 0))
    clock = data.get('Clock', '20:00')
    period = data.get('Period', '1st')

    live_game = LiveGame.query.first()

    if not live_game:
        live_game_record = Game.query.filter_by(live=True).first()
        if not live_game_record:
            return jsonify({'error': 'No live game found in the Game table.'}), 404

        live_game = LiveGame(
            game_id=live_game_record.GameID,
            home_team_score=0,
            away_team_score=0,
            period="1st",
            clock="20:00"
        )
        db.session.add(live_game)
        db.session.commit()

    updates_made = False

    if live_game.home_team_score != home_score:
        live_game.home_team_score = home_score
        socketio.emit('update_value', {'elementId': 'home-goals', 'value': home_score})
        print('Emitting update for home-goals:', home_score)
        updates_made = True

    if live_game.away_team_score != away_score:
        live_game.away_team_score = away_score
        socketio.emit('update_value', {'elementId': 'away-goals', 'value': away_score})
        print('Emitting update for away-goals:', away_score)
        updates_made = True

    # Similar checks for period and clock

    if live_game.period != period:
        live_game.period = period
        socketio.emit('update_value', {'elementId': 'period-display', 'value': period})
        print('Emitting update for period-display:', period)
        updates_made = True

    if live_game.clock != clock:
        live_game.clock = clock
        socketio.emit('update_value', {'elementId': 'time-display', 'value': clock})
        print('Emitting update for time-display:', clock)
        updates_made = True

    if updates_made:
        db.session.add(live_game)
        db.session.commit()

    return jsonify({'message': 'Scoreboard data ingested successfully, LiveGame updated/created'}), 200


@app.route('/api/scoreboard_live_data', methods=['GET'])
def get_scoreboard_data():
    # Find the live game
    live_game = LiveGame.query.first()  # Adjust according to your game_id logic

    if not live_game or not live_game.scoreboard:
        return jsonify({'error': 'No scoreboard data available'}), 404

    scoreboard = live_game.scoreboard
    data = {
        'Home score': live_game.home_team_score,
        'Away Score': live_game.away_team_score,
        'Clock': live_game.clock,
        'Period': live_game.period,
        'homepenplayer1': scoreboard.home_penalty_player1,
        'homepenplayer2': scoreboard.home_penalty_player2,
        'homepentime1': scoreboard.home_penalty_time1,
        'homepentime2': scoreboard.home_penalty_time2,
        'awaypenplayer1': scoreboard.away_penalty_player1,
        'awaypenplayer2': scoreboard.away_penalty_player2,
        'awaypentime1': scoreboard.away_penalty_time1,
        'awaypentime2': scoreboard.away_penalty_time2,
        'last_updated': scoreboard.last_updated.strftime('%Y-%m-%d %H:%M:%S')
    }

    return jsonify(data), 200


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
