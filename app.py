from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from passlib.hash import sha256_crypt
from flask_mysqldb import MySQL
from dotenv import load_dotenv
from functools import wraps
from os import getenv
import MySQLdb

from forms import RegisterForm, ArticleForm
from middleware import redirect_if_logged_in#, is_logged_in

''' SETUP '''
# Load environent variables
load_dotenv()

# Initialize application
app = Flask(__name__)

# Set debug mode (or not)
app.debug = bool(getenv('DEBUG'))

# Set secret for sessions
app.secret_key = getenv('SECRET_KEY')

# Configure MySQL
app.config['MYSQL_HOST'] = getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = getenv('MYSQL_DB')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize MySQL
mysql = MySQL(app)


''' MIDDLEWARE '''
def is_logged_in(f):
    ''' Middleware that checks login state before proceding '''
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, please login', 'danger')
            return redirect(url_for('login'))
    return wrap



''' ERROR HANDLERS '''
@app.errorhandler(404)
def page_not_found(*args):
    error = {}
    error['title'] = 'Error!'
    error['lead'] = 'Error 404: Page Not Found'
    error['description'] = 'Sorry, but the page you were trying to access does not exist.'
    return render_template('error.html', error = error), 404

@app.errorhandler(500)
def server_error(*args):
    error = {}
    error['title'] = 'Oops!'
    error['lead'] = 'Error 500: Internal Server Error'
    error['description'] = 'Sorry, something went wrong on our side. Please try again later.'
    return render_template('error.html', error = error), 500



''' ROUTES '''
# Index
@app.route('/')
def index():
    return render_template('index.html')



# About
@app.route('/about')
def about():
    return render_template('about.html')



# Articles
@app.route('/articles')
def articles():

    # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    # Close connection
    cur.close()

    # Return corresponding page
    return render_template('articles.html', articles = articles)



# Article (singular)
@app.route('/article/<string:id>')
def article(id):
    
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()

    # Close connection
    cur.close()

    # Return corresponding page
    if result == 0:
        return redirect(url_for('articles'))
    else:
        return render_template('article.html', article = article)



# Register
@app.route('/register', methods=['GET', 'POST'])
def register():

    # Redirect to dashboard if already logged in
    redirect_if_logged_in(session)

    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():

        # Fetch form data
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.hash(str(form.password.data))

        # Create error variable (0 for none, 1 for duplicate email, 2 for duplicate username)
        error = 0

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query & commit to DB (check integrity errors)
        try:
            cur.execute("INSERT INTO users(name, email, username, password) VALUES (%s, %s, %s, %s)", (name, email, username, password))
            mysql.connection.commit()
        except MySQLdb._exceptions.IntegrityError as e:

            # Get error message
            message = e.args[1]

            if 'Duplicate' in message and 'email' in message:
                error = 1
            elif 'Duplicate' in message and 'username' in message:
                error = 2
            else:
                raise(e)


        # Close connection
        cur.close()

        # Flash message
        if error == 0:
            flash('You are now registered and can log in', 'success')
            return redirect(url_for('login')) # redirect user to login page
        elif error == 1:
            flash('Email already registered', 'danger')
        elif error == 2:
            flash('Username already registered', 'danger')
        

    return render_template('register.html', form = form)



# Login
@app.route('/login', methods=['GET', 'POST'])
def login():

    # Redirect to dashboard if already logged in
    redirect_if_logged_in(session)
    
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            data = cur.fetchone()
            password = data['password']

            if sha256_crypt.verify(password_candidate, password):
                # msg = '%s logged in'.format(username)
                session['logged_in'] = True
                session['username'] = username
                session['user_id'] = str(data['id'])
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Username and password did not match'
                return render_template('login.html', error = error)
        else:
            error = 'Username not found'
            return render_template('login.html', error = error)

        # Close connection
        cur.close()


    return render_template('login.html')



# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))



# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():

    # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    cur.execute("SELECT * FROM articles WHERE author = %s", [session['username']])
    articles = cur.fetchall()

    # Close connection
    cur.close()

    # Return corresponding page
    return render_template('dashboard.html', articles = articles)



# Add Article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)

    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create cursor
        cur = mysql.connection.cursor()

        # Insert article
        cur.execute("INSERT INTO articles(title, body, author, user_id) VALUES (%s, %s, %s, %s)", (title, body, session['username'], session['user_id']))
        mysql.connection.commit()

        # Close connection
        cur.close()

        # Let user know of success
        flash('Article created', 'success')

        # Return corresponding page
        return redirect(url_for('dashboard'))
        
    return render_template('add_article.html', form = form)



# Edit Article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):

    # Create cursor
    cur = mysql.connection.cursor()

    # Get article
    cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()

    # Close connection
    cur.close()

    # Get form
    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # Create cursor
        cur = mysql.connection.cursor()

        # Update article
        result = cur.execute("UPDATE articles SET title = %s, body = %s WHERE id = %s AND author = %s AND user_id = %s", (title, body, id, session['username'], session['user_id']))
        mysql.connection.commit()

        # Close connection
        cur.close()

        # Let user know of success/failure
        if result == 0:
            flash('Article left as is', 'info')
        else:
            flash('Article updated', 'success')

        # Return corresponding page
        return redirect(url_for('dashboard'))
        
    return render_template('edit_article.html', form = form)



# Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):

    # Create cursor
    cur = mysql.connection.cursor()

    # Delete article
    result = cur.execute("DELETE FROM articles WHERE id = %s AND author = %s AND user_id = %s", (id, session['username'], session['user_id']))
    mysql.connection.commit()

    print("DELETE FROM articles WHERE id = %s AND author = %s AND user_id = %s" % (id, session['username'], session['user_id']))

    # Close connection
    cur.close()

    # Let user know of success/failure
    if result == 0:
        flash('Article deletion denied, as article does not belong to user', 'danger')
    else:
        flash('Article deleted', 'success')

    # Return corresponding page
    return redirect(url_for('dashboard'))



'''' MAIN '''
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(getenv('PORT', 5000)))