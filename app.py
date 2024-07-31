from hashlib import sha256

from flask import request, render_template, flash, redirect, url_for, session

from decorators import admin_required
from models import User, Team, Player, Fixture
from config import bcrypt, login_manager, app
from models import db
from forms import TeamForm, PlayerForm, FixtureForm
from datetime import timedelta


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


@app.route('/admin/fixtures/new', methods=['POST'])
@admin_required
def new_fixture():
    home_team_id = request.form.get('home_team')
    away_team_id = request.form.get('away_team')
    date = request.form.get('date')
    location = request.form.get('location')

    fixture = Fixture(
        HomeTeamID=home_team_id,
        AwayTeamID=away_team_id,
        Date=date,
        Location=location,
        live=False,
        completed=False
    )
    db.session.add(fixture)
    db.session.commit()
    flash('Fixture has been created!', 'success')
    return redirect(url_for('fixtures'))


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



@app.route('/')
def home():  # put application's code here
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('admin' if user.role == 'admin' else 'index'))
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


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=True)
