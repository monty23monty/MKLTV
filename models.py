from config import db
from flask_login import UserMixin


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.role}')"


class Team(db.Model):
    __tablename__ = 'teams'
    TeamID = db.Column(db.Integer, primary_key=True)
    TeamName = db.Column(db.String(100))
    Abbreviation = db.Column(db.String(10))
    City = db.Column(db.String(100))
    CoachName = db.Column(db.String(100))
    AssistantCoachName = db.Column(db.String(100))

    # Relationships
    players = db.relationship('Player', backref='team')
    home_games = db.relationship('Game', foreign_keys='Game.HomeTeamID', backref='home_team_details', overlaps="home_team,home_games")
    away_games = db.relationship('Game', foreign_keys='Game.AwayTeamID', backref='away_team_details', overlaps="away_team,away_games")


class Game(db.Model):
    __tablename__ = 'games'
    GameID = db.Column(db.Integer, primary_key=True)
    Date = db.Column(db.String(50))
    EndTime = db.Column(db.String(50))
    Location = db.Column(db.String(255))
    HomeTeamID = db.Column(db.Integer, db.ForeignKey('teams.TeamID'))
    AwayTeamID = db.Column(db.Integer, db.ForeignKey('teams.TeamID'))
    live = db.Column(db.Boolean)
    completed = db.Column(db.Boolean)

    # Relationships
    home_team = db.relationship('Team', foreign_keys=[HomeTeamID], backref='home_team', overlaps="home_games,home_team_details")
    away_team = db.relationship('Team', foreign_keys=[AwayTeamID], backref='away_team', overlaps="away_games,away_team_details")
    game_stats = db.relationship('GameStats', backref='game', cascade='all, delete-orphan')



class Player(db.Model):
    __tablename__ = 'players'
    PlayerID = db.Column(db.Integer, primary_key=True)
    FirstName = db.Column(db.String(100))
    LastName = db.Column(db.String(100))
    TeamID = db.Column(db.Integer, db.ForeignKey('teams.TeamID'))
    Position = db.Column(db.String(50))
    Shoots = db.Column(db.String(10))
    Height = db.Column(db.String(20))
    Weight = db.Column(db.Integer)
    BirthDate = db.Column(db.String(50))
    BirthCity = db.Column(db.String(100))
    BirthCountry = db.Column(db.String(100))


class StaffPosition(db.Model):
    __tablename__ = 'staff_positions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class FixtureStaff(db.Model):
    __tablename__ = 'fixture_staff'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.GameID'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('staff_positions.id'), nullable=False)

    game = db.relationship('Game', backref=db.backref('fixture_staff', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('fixture_staff', cascade='all, delete-orphan'))
    position = db.relationship('StaffPosition', backref=db.backref('fixture_staff', cascade='all, delete-orphan'))


class FixtureStaffDraft(db.Model):
    __tablename__ = 'fixture_staff_draft'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.GameID'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('staff_positions.id'), nullable=False)

    game = db.relationship('Game', backref=db.backref('fixture_staff_draft', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('fixture_staff_draft', cascade='all, delete-orphan'))
    position = db.relationship('StaffPosition', backref=db.backref('fixture_staff_draft', cascade='all, delete-orphan'))


class UserAvailability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.GameID'), nullable=False)
    available = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref=db.backref('availabilities', cascade='all, delete-orphan'))
    game = db.relationship('Game', backref=db.backref('availabilities', cascade='all, delete-orphan'))


class GameStats(db.Model):
    __tablename__ = 'game_stats'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.GameID'), nullable=False)
    home_sog = db.Column(db.Integer)
    away_sog = db.Column(db.Integer)
