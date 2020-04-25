from flask import redirect, url_for

def redirect_if_logged_in(session):
    ''' Redirects to dashboard if logged in '''
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))