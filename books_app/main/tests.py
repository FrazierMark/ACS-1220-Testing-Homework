import os
import unittest
import app

from datetime import date
from books_app.extensions import app, db, bcrypt
from books_app.models import Book, Author, User, Audience, Genre

"""
Run these tests with the command:
python -m unittest books_app.main.tests
"""

#################################################
# Setup
#################################################

def login(client, username, password):
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

def logout(client):
    return client.get('/logout', follow_redirects=True)

def create_books():
    a1 = Author(name='Harper Lee')
    b1 = Book(
        title='To Kill a Mockingbird',
        publish_date=date(1960, 7, 11),
        author=a1
    )
    db.session.add(b1)

    a2 = Author(name='Sylvia Plath')
    b2 = Book(title='The Bell Jar', author=a2)
    db.session.add(b2)
    db.session.commit()

def create_user():
    # Creates a user with username 'me1' and password of 'password'
    password_hash = bcrypt.generate_password_hash('password').decode('utf-8')
    user = User(username='me1', password=password_hash)
    db.session.add(user)
    db.session.commit()
    
def create_authors():
    a1 = Author(name='Harper Lee')
    a2 = Author(name='Sylvia Plath')
    db.session.add_all([a1, a2])
    db.session.commit()

#################################################
# Tests
#################################################

class MainTests(unittest.TestCase):
 
    def setUp(self):
        """Executed prior to each test."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        db.drop_all()
        db.create_all()
 
    def test_homepage_logged_out(self):
        """Test that the books show up on the homepage."""
        # Set up
        create_books()
        create_user()

        # Make a GET request
        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check that page contains all of the things we expect
        response_text = response.get_data(as_text=True)
        self.assertIn('To Kill a Mockingbird', response_text)
        self.assertIn('The Bell Jar', response_text)
        self.assertIn('me1', response_text)
        self.assertIn('Log In', response_text)
        self.assertIn('Sign Up', response_text)

        # Check that the page doesn't contain things we don't expect
        # (these should be shown only to logged in users)
        self.assertNotIn('Create Book', response_text)
        self.assertNotIn('Create Author', response_text)
        self.assertNotIn('Create Genre', response_text)
 
    def test_homepage_logged_in(self):
        """Test that the books show up on the homepage."""
        # Set up
        create_books()
        create_user()
        login(self.app, 'me1', 'password')

        # Make a GET request
        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check that page contains all of the things we expect
        response_text = response.get_data(as_text=True)
        self.assertIn('To Kill a Mockingbird', response_text)
        self.assertIn('The Bell Jar', response_text)
        self.assertIn('me1', response_text)
        self.assertIn('Create Book', response_text)
        self.assertIn('Create Author', response_text)
        self.assertIn('Create Genre', response_text)
        self.assertNotIn('Log In', response_text)
        self.assertNotIn('Sign Up', response_text)

    def test_book_detail_logged_out(self):
        """Test that the book appears on its detail page."""
        create_books()
        create_user()
        create_authors()

        response = self.app.get('/book/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        response_text = response.get_data(as_text=True)
        self.assertIn("<h1>To Kill a Mockingbird</h1>", response_text)
        self.assertIn("Harper Lee", response_text)

        self.assertNotIn("Favorite This Book", response_text)

    def test_book_detail_logged_in(self):
        """Test that the book appears on its detail page."""
        create_authors()
        create_books()
        create_user()
        login(self.app, 'me1', 'password')

        response = self.app.get('/book/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        response_text = response.get_data(as_text=True)
        self.assertIn("<h1>To Kill a Mockingbird</h1>", response_text)
        self.assertIn("Harper Lee", response_text)

        self.assertIn("Favorite This Book", response_text)


    def test_update_book(self):
        """Test updating a book."""
        create_books()
        create_user()
        login(self.app, 'me1', 'password')

        post_data = {
            'title': 'Tequila Mockingbird',
            'publish_date': '1960-07-12',
            'author': 1,
            'audience': 'CHILDREN',
            'genres': []
        }
        self.app.post('/book/1', data=post_data)
        
        book = Book.query.get(1)
        self.assertEqual(book.title, 'Tequila Mockingbird')
        self.assertEqual(book.publish_date, date(1960, 7, 12))
        self.assertEqual(book.audience, Audience.CHILDREN)

    def test_create_book(self):
        """Test creating a book."""
        create_books()
        create_user()
        login(self.app, 'me1', 'password')

        post_data = {
            'title': 'Go Set a Watchman',
            'publish_date': '2015-07-14',
            'author': 1,
            'audience': 'ADULT',
            'genres': []
        }
        self.app.post('/create_book', data=post_data)

        created_book = Book.query.filter_by(title='Go Set a Watchman').one()
        self.assertIsNotNone(created_book)
        self.assertEqual(created_book.author.name, 'Harper Lee')

    def test_create_book_logged_out(self):
        """
        Test that the user is redirected when trying to access the create book 
        route if not logged in.
        """
        create_books()
        create_user()

        response = self.app.get('/create_book')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login?next=%2Fcreate_book', response.location)

    def test_create_author(self):
        """Test creating an author."""
        create_books()
        create_user()
        login(self.app, 'me1', 'password')

        post_data = {
            'name': 'Johnny Martin',
            'biography': 'The Best Author Ever'
        }
        
        self.app.post('/create_author', data=post_data)

        created_author = Author.query.filter_by(name='Johnny Martin').one()
        self.assertIsNotNone(created_author)
        self.assertEqual(created_author.biography, 'The Best Author Ever')

    def test_create_genre(self):
        create_books()
        create_user()
        login(self.app, 'me1', 'password')

        post_data = {
            'name': 'Science Fiction Fantasy'
        }
        
        self.app.post('/create_genre', data=post_data)
        created_genre = Genre.query.filter_by(name='Science Fiction Fantasy').one()
        self.assertIsNotNone(created_genre)
        self.assertEqual(created_genre.name, 'Science Fiction Fantasy')


    def test_profile_page(self):
        create_books()
        create_user()
        login(self.app, 'me1', 'password')

        response = self.app.get('/profile/me1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        response_text = response.get_data(as_text=True)
        self.assertIn("<p>\nWelcome to me1\'s profile.\n</p>", response_text)


    def test_favorite_book(self):
        create_books()
        create_user()
        login(self.app, 'me1', 'password')

        response = self.app.get('/profile/me1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.app.post('/favorite/1', data=response.get_data(as_text=False))

        response_text = self.app.get('/profile/me1', follow_redirects=True)
        new_response_text = response_text.get_data(as_text=True)

        self.assertIsNotNone(new_response_text)
        self.assertIn('To Kill a Mockingbird', new_response_text)

    def test_unfavorite_book(self):
        create_books()
        create_user()
        login(self.app, 'me1', 'password')
        
        response = self.app.get('/profile/me1', follow_redirects=True)
        self.app.post('/favorite/1', data=response.get_data(as_text=False))

        self.app.post('/unfavorite/1', data='')
        
        get_reponse = self.app.get('/profile/me1', follow_redirects=True)
        get_response_text = get_reponse.get_data(as_text=True)
        self.assertNotIn('To Kill a Mockingbird', get_response_text)
        

