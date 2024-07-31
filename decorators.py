from functools import wraps
from flask import session, redirect, url_for, flash
from models import User


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('You need to be logged in to access this page.')
            return redirect(url_for('login'))

        user = User.query.filter_by(id=user_id).first()
        if not user or user.role != 'admin':
            flash('You do not have permission to access this page.')
            return redirect(url_for('index'))

        return f(*args, **kwargs)

    return decorated_function
