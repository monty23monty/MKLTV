from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField, DateField, DateTimeField
from wtforms.fields.datetime import DateTimeLocalField
from wtforms.validators import DataRequired


class TeamForm(FlaskForm):
    TeamName = StringField('Team Name', validators=[DataRequired()])
    Abbreviation = StringField('Abbreviation')
    City = StringField('City')
    CoachName = StringField('Coach Name')
    AssistantCoachName = StringField('Assistant Coach Name')
    Submit = SubmitField('Create Team')


class PlayerForm(FlaskForm):
    FirstName = StringField('First Name', validators=[DataRequired()])
    LastName = StringField('Last Name', validators=[DataRequired()])
    TeamID = SelectField('Team', coerce=int, validators=[DataRequired()])
    Position = StringField('Position', validators=[DataRequired()])
    Shoots = StringField('Shoots')
    Height = StringField('Height')
    Weight = IntegerField('Weight')
    BirthDate = DateField('Birth Date')
    BirthCountry = StringField('Birth Country')
    Submit = SubmitField('Save Changes')


class FixtureForm(FlaskForm):
    DateTime = DateTimeLocalField('Date and Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    Location = SelectField('Location', choices=[('Home', 'Home'), ('Away', 'Away')], validators=[DataRequired()])
    HomeTeamID = SelectField('Home Team', coerce=int, validators=[DataRequired()])
    AwayTeamID = SelectField('Away Team', coerce=int, validators=[DataRequired()])
    Submit = SubmitField('Create Fixture')


class StaffPositionForm(FlaskForm):
    name = StringField('Position Name', validators=[DataRequired()])
    submit = SubmitField('Create Position')


class FixtureStaffForm(FlaskForm):
    fixture_id = SelectField('Fixture', coerce=int, validators=[DataRequired()])
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    position_id = SelectField('Position', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Assign Staff')