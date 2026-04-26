#!/usr/bin/env python
from contextlib import redirect_stdout
from datetime import datetime, timezone, timedelta
from io import BytesIO, StringIO
import os
import unittest
from unittest import mock

import sqlalchemy as sa
from PIL import Image

from app import create_app, db
from app.models import Comment, ConversationReadState, Message, Notification, Post, User
from config import ProductionConfig, TestConfig, get_config_class


class MicroblogTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.avatar_dir = os.path.join(self.app.root_path, 'static', 'avatars')
        self._initial_avatar_files = set(os.listdir(self.avatar_dir)) \
            if os.path.isdir(self.avatar_dir) else set()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self._remove_uploaded_avatars()
        self.app_context.pop()

    def _remove_uploaded_avatars(self):
        if not os.path.isdir(self.avatar_dir):
            return
        for filename in os.listdir(self.avatar_dir):
            if filename not in self._initial_avatar_files:
                os.remove(os.path.join(self.avatar_dir, filename))

    def create_user(self, username='john', email='john@example.com',
                    password='cat'):
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    def login(self, username='john', password='cat', follow_redirects=True):
        return self.client.post('/auth/login', data={
            'username': username,
            'password': password,
        }, follow_redirects=follow_redirects)

    def logout(self):
        return self.client.get('/auth/logout', follow_redirects=True)

    def make_png_file(self):
        image = Image.new('RGB', (16, 16), color='red')
        file_obj = BytesIO()
        image.save(file_obj, format='PNG')
        file_obj.seek(0)
        return file_obj

    def test_config_selection_and_test_isolation(self):
        self.assertIs(get_config_class('testing'), TestConfig)
        self.assertIs(get_config_class('unknown'), get_config_class('default'))
        self.assertTrue(self.app.testing)
        self.assertEqual(self.app.config['SQLALCHEMY_DATABASE_URI'], 'sqlite://')
        self.assertIsNone(self.app.config['ELASTICSEARCH_URL'])
        self.assertIsNone(self.app.elasticsearch)
        self.assertTrue(self.app.config['MAIL_SUPPRESS_SEND'])
        self.assertIsNone(self.app.config['BAIDU_TRANSLATOR_APP_ID'])
        self.assertIsNone(self.app.config['BAIDU_TRANSLATOR_KEY'])

    def test_production_config_requires_secret_key(self):
        class MissingSecretProductionConfig(ProductionConfig):
            SECRET_KEY = None

        with mock.patch.dict(os.environ, {'SECRET_KEY': ''}):
            with self.assertRaisesRegex(RuntimeError, 'SECRET_KEY'):
                create_app(MissingSecretProductionConfig)

    def test_password_hashing(self):
        user = User(username='susan', email='susan@example.com')
        user.set_password('cat')
        self.assertFalse(user.check_password('dog'))
        self.assertTrue(user.check_password('cat'))

    def test_avatar(self):
        user = User(username='john', email='john@example.com')
        self.assertEqual(user.avatar(128), ('https://www.gravatar.com/avatar/'
                                            'd4c74594d841139328695756648b6bd6'
                                            '?d=identicon&s=128'))

    def test_follow(self):
        john = self.create_user('john', 'john@example.com')
        susan = self.create_user('susan', 'susan@example.com')

        self.assertEqual(db.session.scalars(john.following.select()).all(), [])
        self.assertEqual(db.session.scalars(susan.followers.select()).all(), [])

        john.follow(susan)
        db.session.commit()
        self.assertTrue(john.is_following(susan))
        self.assertEqual(john.following_count(), 1)
        self.assertEqual(susan.followers_count(), 1)
        self.assertEqual(
            db.session.scalars(john.following.select()).first().username,
            'susan')
        self.assertEqual(
            db.session.scalars(susan.followers.select()).first().username,
            'john')

        john.unfollow(susan)
        db.session.commit()
        self.assertFalse(john.is_following(susan))
        self.assertEqual(john.following_count(), 0)
        self.assertEqual(susan.followers_count(), 0)

    def test_follow_posts(self):
        john = self.create_user('john', 'john@example.com')
        susan = self.create_user('susan', 'susan@example.com')
        mary = self.create_user('mary', 'mary@example.com')
        david = self.create_user('david', 'david@example.com')

        now = datetime.now(timezone.utc)
        p1 = Post(body='post from john', author=john,
                  timestamp=now + timedelta(seconds=1))
        p2 = Post(body='post from susan', author=susan,
                  timestamp=now + timedelta(seconds=4))
        p3 = Post(body='post from mary', author=mary,
                  timestamp=now + timedelta(seconds=3))
        p4 = Post(body='post from david', author=david,
                  timestamp=now + timedelta(seconds=2))
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        john.follow(susan)
        john.follow(david)
        susan.follow(mary)
        mary.follow(david)
        db.session.commit()

        self.assertEqual(db.session.scalars(john.following_posts()).all(),
                         [p2, p4, p1])
        self.assertEqual(db.session.scalars(susan.following_posts()).all(),
                         [p2, p3])
        self.assertEqual(db.session.scalars(mary.following_posts()).all(),
                         [p3, p4])
        self.assertEqual(db.session.scalars(david.following_posts()).all(),
                         [p4])

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login', response.headers['Location'])

    def test_register_login_and_logout_flow(self):
        response = self.client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'secret123',
            'password2': 'secret123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        user = db.session.scalar(sa.select(User).where(
            User.username == 'newuser'))
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('secret123'))
        self.assertTrue(user.is_active)
        self.assertIsNone(user.activation_token)

        response = self.login('newuser', 'wrong-password')
        self.assertIn(b'Invalid username or password', response.data)

        response = self.login('newuser', 'secret123', follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        response = self.logout()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign In', response.data)

    def test_create_post_and_database_search_fallback(self):
        self.create_user()
        self.login()

        response = self.client.post('/', data={
            'title': 'Needle title',
            'post': 'This body contains a unique needle phrase.',
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        post = db.session.scalar(sa.select(Post).where(
            Post.title == 'Needle title'))
        self.assertIsNotNone(post)
        self.assertEqual(post.author.username, 'john')

        response = self.client.get('/search?q=needle')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Needle title', response.data)

    def test_delete_post_requires_author(self):
        john = self.create_user('john', 'john@example.com')
        self.create_user('susan', 'susan@example.com')
        post = Post(title='Owned post', body='Delete me', author=john)
        db.session.add(post)
        db.session.commit()
        post_id = post.id

        self.login('susan')
        response = self.client.post(f'/delete_post/{post_id}')
        self.assertEqual(response.status_code, 403)
        self.assertIsNotNone(db.session.get(Post, post_id))

        self.logout()
        self.login('john')
        response = self.client.post(f'/delete_post/{post_id}',
                                    follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(db.session.get(Post, post_id))

    def test_comment_creation(self):
        john = self.create_user('john', 'john@example.com')
        self.create_user('susan', 'susan@example.com')
        post = Post(title='Comment target', body='A post body', author=john)
        db.session.add(post)
        db.session.commit()

        self.login('susan')
        response = self.client.post(f'/post/{post.id}', data={
            'body': 'Nice post',
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        comment = db.session.scalar(sa.select(Comment).where(
            Comment.body == 'Nice post'))
        self.assertIsNotNone(comment)
        self.assertEqual(comment.author.username, 'susan')
        self.assertEqual(comment.post.id, post.id)

    def test_user_popup_contains_profile_card_and_moment_timestamp(self):
        john = self.create_user('john', 'john@example.com')
        self.create_user('susan', 'susan@example.com')
        john.follow(db.session.scalar(sa.select(User).where(
            User.username == 'susan')))
        db.session.commit()

        self.login('john')
        response = self.client.get('/user/susan/popup')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'user-popover-card', response.data)
        self.assertIn(b'user-popover-card__meta-value', response.data)
        self.assertIn(b'flask-moment', response.data)
    def test_private_message_and_notifications(self):
        self.create_user('john', 'john@example.com')
        susan = self.create_user('susan', 'susan@example.com')

        self.login('john')
        response = self.client.post('/conversation/susan', data={
            'message': 'hello susan',
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        message = db.session.scalar(sa.select(Message).where(
            Message.body == 'hello susan'))
        self.assertIsNotNone(message)
        self.assertEqual(message.author.username, 'john')
        self.assertEqual(message.recipient.username, 'susan')
        self.assertEqual(susan.unread_message_count(), 1)

        self.logout()
        self.login('susan')
        response = self.client.get('/notifications')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload[0]['name'], 'unread_message_count')
        self.assertEqual(payload[0]['data'], 1)

        notification = db.session.scalar(sa.select(Notification).where(
            Notification.name == 'unread_message_count'))
        self.assertIsNotNone(notification)

    def test_conversation_read_state_is_per_sender(self):
        john = self.create_user('john', 'john@example.com')
        susan = self.create_user('susan', 'susan@example.com')
        mary = self.create_user('mary', 'mary@example.com')
        now = datetime.now(timezone.utc)
        db.session.add(Message(author=john, recipient=susan,
                               body='from john', timestamp=now))
        db.session.add(Message(author=mary, recipient=susan,
                               body='from mary',
                               timestamp=now + timedelta(seconds=1)))
        db.session.commit()

        self.assertEqual(susan.unread_message_count(), 2)
        self.assertEqual(susan.new_messages_from(john), 1)
        self.assertEqual(susan.new_messages_from(mary), 1)

        self.login('susan')
        response = self.client.get('/conversation/john')
        self.assertEqual(response.status_code, 200)

        state = db.session.scalar(sa.select(ConversationReadState).where(
            ConversationReadState.user_id == susan.id,
            ConversationReadState.peer_id == john.id))
        self.assertIsNotNone(state)
        self.assertEqual(susan.new_messages_from(john), 0)
        self.assertEqual(susan.new_messages_from(mary), 1)
        self.assertEqual(susan.unread_message_count(), 1)

        notification = db.session.scalar(sa.select(Notification).where(
            Notification.user_id == susan.id,
            Notification.name == 'unread_message_count'))
        self.assertIsNotNone(notification)
        self.assertEqual(notification.get_data(), 1)

    def test_conversation_pagination_uses_conversation_urls(self):
        john = self.create_user('john', 'john@example.com')
        susan = self.create_user('susan', 'susan@example.com')
        for index in range(11):
            db.session.add(Message(author=susan, recipient=john,
                                   body=f'message {index}'))
        db.session.commit()

        self.login('john')
        response = self.client.get('/conversation/susan')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'/conversation/susan?page=2', response.data)
        self.assertNotIn(b'/messages?page=2', response.data)

    def test_translate_unconfigured_service_returns_error(self):
        self.create_user()
        self.login()

        with redirect_stdout(StringIO()):
            response = self.client.post('/translate', json={
                'text': 'hello',
                'source_language': 'en',
                'dest_language': 'zh',
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['text'].startswith('Error:'))

    def test_avatar_upload_updates_user_avatar(self):
        self.create_user()
        self.login()

        response = self.client.post('/change_avatar', data={
            'avatar': (self.make_png_file(), 'avatar.png'),
        }, content_type='multipart/form-data', follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        user = db.session.scalar(sa.select(User).where(User.username == 'john'))
        self.assertIsNotNone(user.avatar_filename)
        self.assertTrue(user.avatar_filename.endswith('.png'))
        avatar_path = os.path.join(self.avatar_dir, user.avatar_filename)
        self.assertTrue(os.path.exists(avatar_path))
        with Image.open(avatar_path) as image:
            self.assertEqual(image.size, (512, 512))

    def test_registration_rejects_weak_password_and_invalid_username(self):
        response = self.client.post('/auth/register', data={
            'username': '1bad',
            'email': 'bad@example.com',
            'password': 'short',
            'password2': 'short',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(db.session.scalar(sa.select(User).where(
            User.email == 'bad@example.com')))
        self.assertIn(b'Field must be between 8 and 128 characters long.', response.data)

    def test_change_password_requires_current_password_and_updates_hash(self):
        self.create_user(password='oldpassword')
        self.login(password='oldpassword')

        response = self.client.post('/auth/change_password', data={
            'current_password': 'wrongpassword',
            'password': 'newpassword',
            'password2': 'newpassword',
        }, follow_redirects=True)
        self.assertIn(b'Current password is incorrect.', response.data)

        response = self.client.post('/auth/change_password', data={
            'current_password': 'oldpassword',
            'password': 'newpassword',
            'password2': 'newpassword',
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        self.logout()
        response = self.login(password='oldpassword')
        self.assertIn(b'Invalid username or password', response.data)
        response = self.login(password='newpassword')
        self.assertEqual(response.status_code, 200)

    def test_translate_rejects_malformed_json(self):
        self.create_user()
        self.login()

        response = self.client.post('/translate', json={'text': 'hello'})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.get_json()['text'].startswith('Error:'))

    def test_avatar_upload_rejects_non_image_payload(self):
        self.create_user()
        self.login()

        response = self.client.post('/change_avatar', data={
            'avatar': (BytesIO(b'not an image'), 'avatar.png'),
        }, content_type='multipart/form-data', follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        user = db.session.scalar(sa.select(User).where(User.username == 'john'))
        self.assertIsNone(user.avatar_filename)


if __name__ == '__main__':
    unittest.main(verbosity=2)