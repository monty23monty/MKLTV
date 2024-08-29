from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
import os
import boto3
from botocore.exceptions import ClientError
from itsdangerous import URLSafeTimedSerializer
from flask import render_template, redirect, url_for


AWS_REGION = "eu-west-2"  # e.g., "us-west-2"
SENDER_EMAIL = "no-reply@lightningtv.co.uk"
app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
app.config['SECURITY_PASSWORD_SALT'] = 'my_precious_two'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL',
                                                  'postgresql://postgres:postgres@localhost:5432/MKLv0.2')


ses_client = boto3.client('ses', region_name=AWS_REGION)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)
socketio = SocketIO(app)


def send_allocation_email(user_email, subject, body_text):
    # Email subject and body
    SUBJECT = subject
    BODY_TEXT = body_text

    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [user_email],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': "UTF-8",
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': SUBJECT,
                },
            },
            Source=SENDER_EMAIL,
        )
    except ClientError as e:
        print(f"Error sending email: {e}")
    else:
        print(f"Email sent! Message ID: {response['MessageId']}")


def generate_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except:
        return False
    return email
