from flask import Flask, render_template, redirect, request, url_for, make_response
from flask_restful import Resource, Api, fields, marshal_with, reqparse
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, UserMixin, current_user, login_required
from forms import *
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from datetime import datetime
import aspose.words as aw
import requests
import json
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.from_object('config.Config')
db = SQLAlchemy()
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
api = Api(app)
app.app_context().push()

API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
headers = {"Authorization": "Bearer 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"}


def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()


follow = db.Table('follow',
                  db.Column('user_id', db.Integer, db.ForeignKey('user.user_id'), primary_key=True),
                  db.Column('follow_id', db.Integer, db.ForeignKey('user.user_id'), primary_key=True))
block = db.Table('block',
                 db.Column('user_id', db.Integer, db.ForeignKey('user.user_id'), primary_key=True),
                 db.Column('block_id', db.Integer, db.ForeignKey('user.user_id'), primary_key=True))


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.String, nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.now())
    age = db.Column(db.Integer)
    received = db.Column(db.Integer, nullable=False)
    posts = db.relationship('Post', backref='user')
    follows = db.relationship('User', secondary=follow, primaryjoin=user_id == follow.c.follow_id,
                              secondaryjoin=user_id == follow.c.user_id, backref=db.backref('followed'))
    blocked = db.relationship('User', secondary=block, primaryjoin=user_id == block.c.block_id,
                              secondaryjoin=user_id == block.c.user_id, backref=db.backref('blocks'))
    followers = db.Column(db.Integer, nullable=False)
    liked_post = db.relationship('Post', secondary='likedpost')
    liked_comment = db.relationship('Comment', secondary='likedcomment')
    comments = db.relationship('Comment', backref='user')
    level = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String)
    sort = db.Column(db.Integer, nullable=False)

    def get_id(self):
        return str(self.user_id)


class Post(db.Model):
    __tablename__ = 'post'
    post_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    image = db.Column(db.String, nullable=False)
    title = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text)
    time = db.Column(db.DateTime, nullable=False, default=datetime.now())
    age = db.Column(db.Integer)
    likes = db.Column(db.Integer, nullable=False)
    poster_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    poster_name = db.Column(db.String(20), nullable=False)
    reviews = db.relationship('Comment', backref='post')
    archived = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Integer, nullable=False)


class Comment(db.Model):
    __tablename__ = 'comment'
    comment_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    contents = db.Column(db.Text, nullable=False)
    likes = db.Column(db.Integer, nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.now())
    age = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    username = db.Column(db.String, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.post_id'), nullable=False)


class Likedpost(db.Model):
    __tablename__ = 'likedpost'
    liked_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.post_id'), nullable=False)


class Likedcomment(db.Model):
    __tablename__ = 'likedcomment'
    liked_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.comment_id'), nullable=False)


db.create_all()
default = 'lightblue'


@login_manager.user_loader
def load_user(user_id):
    if user_id is not None:
        return User.query.get(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.name.data).first():
            return render_template('signup.html', form=form, message='That username is taken', color=default)
        if User.query.filter_by(email=form.email.data).first():
            return render_template('signup.html', form=form, message='That email id is already registered',
                                   color=default)
        user = User(email=form.email.data, username=form.name.data, password=form.password.data, level=1, sort=0,
                    question=form.question.data, answer=form.answer.data, received=0, followers=0, color='lightblue')
        db.session.add(user)
        db.session.commit()
        return redirect('/')
    return render_template('signup.html', form=form, message='', color=default)


@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/feed')
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user:
            if user.password == form.password.data:
                if user.level == 0:
                    return render_template('login.html', form=form, message='You have been banned', color=default)
                if form.status.data:
                    login_user(user, remember=True)
                else:
                    login_user(user, remember=False)
                next_page = request.args.get('next')
                return redirect(next_page or '/feed')
            return render_template('login.html', form=form, message='Incorrect Password', color=default)
        return render_template('login.html', form=form, message='Account not found, Sign Up!', color=default)
    return render_template('login.html', form=form, message='', color=default)


@app.route('/change', methods=['GET', 'POST'])
def change():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user:
            if form.old_password.data == user.password:
                user.password = form.new_password.data
                db.session.commit()
                return redirect('/')
            return render_template('change.html', form=form, message='Incorrect Password', color=default)
        return render_template('change.html', form=form, message='Account not found, Sign Up!', color=default)
    return render_template('change.html', form=form, message='', color=default)


@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    form = ForgotForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            return render_template('forgot.html', form=form, message='That username does not exist', color=default)
        if user.question == form.question.data and user.answer == form.answer.data:
            return render_template('forgot.html', form=form, message=f'Your password is {user.password}', color=default)
        return render_template('forgot.html', form=form, message='Incorrect Answer', color=default)
    return render_template('forgot.html', form=form, message='Select your security question and enter the answer',
                           color=default)


@app.route('/feed', methods=['GET', 'POST'])
@login_required
def feed():
    user = current_user
    if not user:
        return redirect('/')
    user_id = user.user_id
    posts = []
    for follow in user.follows:
        posts += Post.query.filter_by(poster_id=follow.user_id).all()
    if user.sort == 0:
        posts.sort(key=lambda x: x.post_id, reverse=True)
    elif user.sort == 1:
        posts.sort(key=lambda x: x.likes, reverse=True)
    notfollow = []
    for unfollow in User.query.all():
        if unfollow not in user.follows and unfollow not in user.blocked and unfollow.level > 0:
            notfollow += Post.query.filter_by(poster_id=unfollow.user_id).all()
    if user.sort == 0:
        notfollow.sort(key=lambda x: x.post_id, reverse=True)
    if user.sort == 1:
        notfollow.sort(key=lambda x: x.likes, reverse=True)
    posts += notfollow
    for post in posts:
        if post.archived:
            posts.remove(post)
    valid = [(elem, elem.received) for elem in User.query.all() if elem not in user.follows
             and elem not in user.blocked and elem.level > 0 and elem != user]
    if valid:
        recommended = sorted(valid, key=lambda x: x[1], reverse=True)
        recommended = [elem[0] for elem in recommended]
    else:
        recommended = None
    if request.method == 'POST':
        return redirect('/create')
    return render_template('feed.html', user_id=user_id, posts=posts, recommended=recommended, color=user.color)


@app.route('/logout')
@login_required
def logout():
    user = current_user
    if not user:
        return redirect('/')
    logout_user()
    return redirect('/')


@app.post('/search_user')
@login_required
def search_user():
    user = current_user
    if not user:
        return redirect('/')
    user_id = user.user_id
    users = User.query.filter(User.username.like(f"{request.form['search']}%")).all()
    users.sort(key=lambda x: len(x.username))
    for elem in users:
        if elem.username == user.username:
            users.remove(elem)
            users.append(elem)
            break
    return render_template('search_user.html', users=users, user_id=user_id, color=user.color)


@app.post('/search_post')
@login_required
def search_post():
    user = current_user
    if not user:
        return redirect('/')
    user_id = user.user_id
    sentences = [(post.post_id, post.title) for post in Post.query.all() if post.archived == 0]
    output = query({
        "inputs": {
            "source_sentence": request.form['search'],
            "sentences": [sentence[1] for sentence in sentences]
        },
    })
    result = [[sentences[i][0], sentences[i][1], output[i]] for i in range(len(sentences))]
    result.sort(key=lambda x: x[2], reverse=True)
    return render_template('search_post.html', results=result, user_id=user_id, color=user.color)


@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = CreateForm()
    user = current_user
    if not user:
        return redirect('/')
    user_id = user.user_id
    if form.validate_on_submit():
        title, description, f = form.title.data, form.description.data, form.photo.data
        filename = secure_filename(f.filename)
        f.save(os.path.join('static', filename))
        posts = Post(title=title, description=description, likes=0, poster_id=user_id, image=filename,
                     poster_name=user.username, archived=0, active=0)
        if form.archived.data:
            posts.archived = 1
        if form.active.data:
            posts.active = 1
        db.session.add(posts)
        db.session.commit()
        return redirect('/feed')
    return render_template('create.html', form=form, user_id=user_id, color=user.color)


@app.route('/post/<post_id>', methods=['GET', 'POST'])
@login_required
def post(post_id):
    user = current_user
    if not user:
        return redirect('/')
    user_id = user.user_id
    post = Post.query.filter_by(post_id=post_id).first()
    if not post:
        return redirect('/feed')
    post.age = (datetime.now() - post.time).days
    for review in post.reviews:
        review.age = (datetime.now() - review.time).days
    db.session.commit()
    poster = User.query.filter_by(user_id=post.poster_id).first()
    if poster is None:
        return redirect('/feed')
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(contents=form.content.data, user_id=user_id, username=user.username, post_id=post_id, likes=0)
        db.session.add(comment)
        db.session.commit()
        return redirect(f'/post/{post_id}')
    if os.path.exists(f'static/post.{post_id}.docx'):
        os.remove(f'static/post.{post_id}.docx')
    doc = aw.Document()
    builder = aw.DocumentBuilder(doc)
    builder.writeln(f'Posted by {post.poster_name} {post.age} days ago')
    if os.path.exists(f'static/{post.image}'):
        builder.insert_image(f'static/{post.image}')
    builder.write(f'Likes: {post.likes}    Comments: {len(post.reviews)}')
    doc.save(f'static/post.{post_id}.docx')
    return render_template('post.html', form=form, post=post, user=user, color=user.color, poster=poster)


@app.post('/<post_id>/archive')
@login_required
def archive(post_id):
    if not current_user:
        return redirect('/')
    post = Post.query.filter_by(post_id=post_id).first()
    if not post:
        return redirect('/feed')
    if post.archived == 1:
        post.archived = 0
    else:
        post.archived = 1
    db.session.commit()
    return redirect(f'/post/{post_id}')


@app.post('/<post_id>/enable')
@login_required
def enable(post_id):
    if not current_user:
        return redirect('/')
    post = Post.query.filter_by(post_id=post_id).first()
    if not post:
        return redirect('/feed')
    post.active = 0
    db.session.commit()
    return redirect(f'/post/{post_id}')


@app.post('/delete_post/<post_id>')
@login_required
def delete_post(post_id):
    user = current_user
    if not user:
        return redirect('/')
    post = Post.query.filter_by(post_id=post_id).first()
    if not post:
        return redirect('/feed')
    for comment in Comment.query.filter_by(post_id=post_id).all():
        for elem in User.query.all():
            if comment in elem.liked_comment:
                elem.liked_comment.remove(comment)
        db.session.delete(comment)
    user.received -= post.likes
    for elem in User.query.all():
        if post in elem.liked_post:
            elem.liked_post.remove(post)
    db.session.delete(post)
    db.session.commit()
    os.remove(f'static/post.{post_id}.docx')
    for posts in Post.query.all():
        if posts.image == post.image:
            return redirect('/feed')
    if os.path.exists(f'static/{post.image}'):
        os.remove(f'static/{post.image}')
    return redirect('/feed')


@app.route('/edit_post/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    user = current_user
    if not user:
        return redirect('/')
    user_id = user.user_id
    post = Post.query.filter_by(post_id=post_id).first()
    if not post:
        return redirect('/feed')
    form = EditPostForm()
    if form.validate_on_submit():
        post.description = form.description.data
        if form.title.data:
            post.title = form.title.data
        if form.photo.data:
            f = form.photo.data
            filename = secure_filename(f.filename)
            if filename != post.image:
                flag = False
                for posts in Post.query.all():
                    if posts.image == post.image and posts != post:
                        flag = True
                        break
                if not flag and os.path.exists(f'static/{post.image}'):
                    os.remove(f'static/{post.image}')
            f.save(os.path.join('static', filename))
            post.image = filename
        db.session.commit()
        return redirect(f'/post/{post_id}')
    return render_template('edit_post.html', form=form, user_id=user_id, post_id=post_id, color=user.color)


@app.post('/delete_comment/<post_id>/<comment_id>')
@login_required
def delete_comment(post_id, comment_id):
    user = current_user
    if not user:
        return redirect('/')
    if not Post.query.filter_by(post_id=post_id).first():
        return redirect('feed')
    comment = Comment.query.filter_by(comment_id=comment_id).first()
    if not comment:
        return redirect(f'post/{post_id}')
    user.received -= comment.likes
    for elem in User.query.all():
        if comment in elem.liked_comment:
            elem.liked_comment.remove(comment)
    db.session.delete(comment)
    db.session.commit()
    return redirect(f'/post/{post_id}')


@app.route('/edit_comment/<post_id>/<comment_id>', methods=['GET', 'POST'])
@login_required
def edit_comment(post_id, comment_id):
    if not current_user:
        return redirect('/')
    if not Post.query.filter_by(post_id=post_id).first():
        return redirect('/feed')
    comment = Comment.query.filter_by(comment_id=comment_id).first()
    if not comment:
        return redirect(f'/post/{post_id}')
    form = EditCommentForm()
    if form.validate_on_submit():
        comment.contents = form.content.data
        db.session.commit()
        return redirect(f'/post/{comment.post_id}')
    return render_template('edit_comment.html', form=form, comment=comment, color=current_user.color)


@app.post('/like_post/<post_id>')
@login_required
def like_post(post_id):
    user = current_user
    if not user:
        return redirect('/')
    post = Post.query.filter_by(post_id=post_id).first()
    if not post:
        return redirect('/feed')
    poster = User.query.filter_by(user_id=post.poster_id).first()
    if not poster:
        return redirect('/feed')
    if post not in user.liked_post:
        user.liked_post.append(post)
        poster.received += 1
        post.likes += 1
        db.session.commit()
    else:
        user.liked_post.remove(post)
        poster.received -= 1
        post.likes -= 1
        db.session.commit()
    return redirect(f'/post/{post_id}')


@app.post('/like_post2/<post_id>')
@login_required
def like_post2(post_id):
    user = current_user
    if not user:
        return redirect('/')
    post = Post.query.filter_by(post_id=post_id).first()
    if not post:
        return redirect('/feed')
    poster = User.query.filter_by(user_id=post.poster_id).first()
    if not poster:
        return redirect('/feed')
    if post not in user.liked_post:
        user.liked_post.append(post)
        poster.received += 1
        post.likes += 1
        db.session.commit()
    else:
        user.liked_post.remove(post)
        poster.received -= 1
        post.likes -= 1
        db.session.commit()
    return redirect('/liked_post')


@app.post('/like_comment/<post_id>/<comment_id>')
@login_required
def like_comment(post_id, comment_id):
    user = current_user
    if not user:
        return redirect('/')
    if not Post.query.filter_by(post_id=post_id).first():
        return redirect('/feed')
    comment = Comment.query.filter_by(comment_id=comment_id).first()
    if not comment:
        return redirect(f'/post/{post_id}')
    poster = User.query.filter_by(user_id=comment.user_id).first()
    if not poster:
        return redirect(f'/post/{comment.post_id}')
    if comment not in user.liked_comment:
        user.liked_comment.append(comment)
        poster.received += 1
        comment.likes += 1
        db.session.commit()
    else:
        user.liked_comment.remove(comment)
        poster.received -= 1
        comment.likes -= 1
        db.session.commit()
    return redirect(f'/post/{comment.post_id}')


@app.post('/like_comment2/<post_id>/<comment_id>')
@login_required
def like_comment2(post_id, comment_id):
    user = current_user
    if not user:
        return redirect('/')
    if not Post.query.filter_by(post_id=post_id).first():
        return redirect('/feed')
    comment = Comment.query.filter_by(comment_id=comment_id).first()
    if not comment:
        return redirect(f'/post/{post_id}')
    poster = User.query.filter_by(user_id=comment.user_id).first()
    if not poster:
        return redirect(f'/post/{comment.post_id}')
    if comment not in user.liked_comment:
        user.liked_comment.append(comment)
        poster.received += 1
        comment.likes += 1
        db.session.commit()
    else:
        user.liked_comment.remove(comment)
        poster.received -= 1
        comment.likes -= 1
        db.session.commit()
    return redirect('/liked_comment')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = current_user
    if not user:
        return redirect('/')
    user_id = user.user_id
    user.age = (datetime.now() - user.time).days
    db.session.commit()
    temp_post = sorted([(post.post_id, post.likes) for post in user.posts], key=lambda x: x[1], reverse=True)
    temp_comment = sorted([(comment.comment_id, comment.likes) for comment in user.comments], key=lambda x: x[1],
                          reverse=True)
    post, comment = None, None
    if temp_post:
        post = Post.query.filter_by(post_id=temp_post[0][0]).first()
    if temp_comment:
        comment = Comment.query.filter_by(comment_id=temp_comment[0][0]).first()
    if os.path.exists(f'static/user.{user_id}.docx'):
        os.remove(f'static/user.{user_id}.docx')
    doc = aw.Document()
    builder = aw.DocumentBuilder(doc)
    builder.writeln(f'Username: {user.username}')
    builder.writeln(f'Email: {user.email}')
    builder.writeln(f'Age of account: {user.age}')
    builder.writeln(f'Number of followers: {user.followers}')
    builder.writeln(f'Number of accounts followed by user: {len(user.follows)}')
    builder.writeln(f'Number of posts made by user: {len(user.posts)}')
    builder.writeln(f'Number of comments made by user: {len(user.comments)}')
    builder.writeln(f'Number of posts user liked: {len(user.liked_post)}')
    builder.writeln(f'Number of comments user liked: {len(user.liked_comment)}')
    builder.writeln(f'Number of likes user received: {user.received}')
    doc.save(f'static/user.{user_id}.docx')
    return render_template('profile.html', user=user, post=post, comment=comment, color=user.color)


@app.route('/my_posts', methods=['GET', 'POST'])
@login_required
def my_posts():
    user = current_user
    if not user:
        return redirect('/')
    if request.method == 'POST':
        return redirect('/create')
    return render_template('my_posts.html', user=user, color=user.color)


@app.route('/comments', methods=['GET', 'POST'])
@login_required
def comments():
    user = current_user
    if not user:
        return redirect('/')
    if request.method == 'POST':
        return redirect('/create')
    return render_template('comments.html', user=user, color=user.color)


@app.route('/followed', methods=['GET', 'POST'])
@login_required
def followed():
    user = current_user
    if not user:
        return redirect('/')
    if request.method == 'POST':
        return redirect('/create')
    return render_template('followed.html', user=user, color=user.color)


@app.route('/followers', methods=['GET', 'POST'])
@login_required
def followers():
    user = current_user
    if not user:
        return redirect('/')
    followers = []
    for elem in User.query.all():
        if user in elem.follows:
            followers.append(elem)
    if request.method == 'POST':
        return redirect('/create')
    return render_template('followers.html', user=user, followers=followers, color=user.color)


@app.route('/liked_post', methods=['GET', 'POST'])
@login_required
def liked_post():
    user = current_user
    if not user:
        return redirect('/')
    if request.method == 'POST':
        return redirect('/create')
    return render_template('liked_post.html', user=user, color=user.color)


@app.route('/liked_comment', methods=['GET', 'POST'])
@login_required
def liked_comment():
    user = current_user
    if not user:
        return redirect('/')
    if request.method == 'POST':
        return redirect('/create')
    temp = []
    for comment in user.liked_comment:
        post = Post.query.filter_by(post_id=comment.post_id).first()
        commenter = User.query.filter_by(user_id=comment.user_id).first()
        if commenter:
            temp.append((comment.username, comment.contents, comment.likes, comment.user_id, comment.post_id, post, comment.comment_id))
    return render_template('liked_comment.html', user=user, color=user.color, temp=temp)


@app.route('/user/<public_id>', methods=['GET', 'POST'])
@login_required
def public_profile(public_id):
    user = current_user
    if not user:
        return redirect('/')
    public = User.query.filter_by(user_id=public_id).first()
    if not public:
        return redirect('/feed')
    public.age = (datetime.now() - public.time).days
    db.session.commit()
    if os.path.exists(f'static/user.{public_id}.docx'):
        os.remove(f'static/user.{public_id}.docx')
    doc = aw.Document()
    builder = aw.DocumentBuilder(doc)
    builder.writeln(f'Username: {public.username}')
    builder.writeln(f'Age of account: {public.age}')
    builder.writeln(f'Number of followers: {public.followers}')
    builder.writeln(f'Number of accounts followed by user: {len(public.follows)}')
    builder.writeln(f'Number of posts made by user: {len(public.posts)}')
    builder.writeln(f'Number of comments made by user: {len(public.comments)}')
    builder.writeln(f'Number of posts user liked: {len(public.liked_post)}')
    builder.writeln(f'Number of comments user liked: {len(public.liked_comment)}')
    builder.writeln(f'Number of likes user received: {public.received}')
    doc.save(f'static/user.{public_id}.docx')
    return render_template('public.html', user=user, public=public, color=user.color)


@app.route('/follow/<public_id>', methods=['GET', 'POST'])
@login_required
def follow(public_id):
    user = current_user
    if not user:
        return redirect('/')
    public = User.query.filter_by(user_id=public_id).first()
    if not public:
        return redirect('/feed')
    if public in user.follows:
        user.follows.remove(public)
        public.followers -= 1
    else:
        user.follows.append(public)
        public.followers += 1
    db.session.commit()
    return redirect(f'/user/{public_id}')


@app.route('/block/<public_id>', methods=['GET', 'POST'])
@login_required
def blocker(public_id):
    user = current_user
    if not user:
        return redirect('/')
    public = User.query.filter_by(user_id=public_id).first()
    if not public:
        return redirect('/feed')
    if public in user.blocked:
        user.blocked.remove(public)
    else:
        user.blocked.append(public)
    db.session.commit()
    return redirect(f'/user/{public_id}')


@app.route('/follow2/<public_id>', methods=['GET', 'POST'])
@login_required
def follow2(public_id):
    user = current_user
    if not user:
        return redirect('/')
    public = User.query.filter_by(user_id=public_id).first()
    if not public:
        return redirect('/followers')
    if public in user.follows:
        user.follows.remove(public)
        public.followers -= 1
    else:
        user.follows.append(public)
        public.followers += 1
    db.session.commit()
    return redirect('/followers')


@app.route('/block2/<public_id>', methods=['GET', 'POST'])
@login_required
def blocker2(public_id):
    user = current_user
    if not user:
        return redirect('/')
    public = User.query.filter_by(user_id=public_id).first()
    if not public:
        return redirect('/followers')
    if public in user.blocked:
        user.blocked.remove(public)
    else:
        user.blocked.append(public)
    db.session.commit()
    return redirect('/followers')


@app.route('/follow3/<public_id>', methods=['GET', 'POST'])
@login_required
def follow3(public_id):
    user = current_user
    if not user:
        return redirect('/')
    public = User.query.filter_by(user_id=public_id).first()
    if not public:
        return redirect('/followed')
    if public in user.follows:
        user.follows.remove(public)
        public.followers -= 1
    else:
        user.follows.append(public)
        public.followers += 1
    db.session.commit()
    return redirect('/followed')


@app.route('/promote/<public_id>', methods=['GET', 'POST'])
@login_required
def promote(public_id):
    user = current_user
    if user is None:
        return redirect('/')
    public = User.query.filter_by(user_id=public_id).first()
    if public is None:
        return redirect('/feed')
    if public.level == 1:
        public.level = 2
    else:
        public.level = 1
    db.session.commit()
    return redirect(f'/user/{public_id}')


@app.route('/ban/<public_id>', methods=['GET', 'POST'])
@login_required
def ban(public_id):
    user = current_user
    if user is None:
        return redirect('/')
    public = User.query.filter_by(user_id=public_id).first()
    if public is None:
        return redirect('/feed')
    if public.level == 1:
        public.level = 0
        for followed in public.follows:
            followed.followers -= 1
            public.follows.remove(followed)
        for follow in User.query.all():
            if public in follow.follows:
                follow.follows.remove(public)
        public.followers = 0
    else:
        public.level = 1
    db.session.commit()
    return redirect(f'/user/{public_id}')


@app.route('/about')
@login_required
def about():
    user = current_user
    if not user:
        return redirect('/')
    return render_template('about.html', user_id=user.user_id, count=len(User.query.all()), color=user.color)


@app.route('/help')
@login_required
def help():
    user = current_user
    if not user:
        return redirect('/')
    return render_template('help.html', user_id=user.user_id, color=user.color)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = current_user
    if not user:
        return redirect('/')
    form = ColorForm(color=user.color)
    form2 = SortForm(sort=user.sort)
    if form.validate_on_submit():
        user.color = form.color.data
        db.session.commit()
        return redirect('/settings')
    return render_template('settings.html', user=user, form=form, form2=form2, color=user.color)


@app.post('/sort')
@login_required
def sort():
    user = current_user
    if not user:
        return redirect('/')
    form2 = SortForm(sort=user.sort)
    if form2.validate_on_submit():
        user.sort = form2.sort.data
        db.session.commit()
    return redirect('/settings')


@app.route('/name', methods=['GET', 'POST'])
@login_required
def name():
    user = current_user
    if not user:
        return redirect('/')
    user_id = user.user_id
    form = ChangeUsernameForm()
    if form.validate_on_submit():
        if form.name.data == user.username:
            if User.query.filter_by(username=form.new_name.data).first():
                return render_template('name.html', form=form, user_id=user_id, message='That username is taken',
                                       color=user.color)
            user.username = form.new_name.data
            db.session.commit()
            return redirect('/settings')
        return render_template('name.html', form=form, user_id=user_id, message="That's not your Username",
                               color=user.color)
    return render_template('name.html', form=form, user_id=user_id, message='', color=user.color)


@app.route('/email', methods=['GET', 'POST'])
@login_required
def email():
    form = ChangeEmailForm()
    user = current_user
    if not user:
        return redirect('/')
    user_id = user.user_id
    if form.validate_on_submit():
        if form.email.data == user.email:
            if User.query.filter_by(email=form.new_email.data).first():
                return render_template('email.html', form=form, user_id=user_id,
                                       message='That email is already registered', color=user.color)
            user.email = form.new_email.data
            db.session.commit()
            return redirect('/settings')
        return render_template('email.html', form=form, user_id=user_id, message="That's not your Email",
                               color=user.color)
    return render_template('email.html', form=form, user_id=user_id, message='', color=user.color)


@app.route('/question', methods=['GET', 'POST'])
@login_required
def question():
    user = current_user
    if not user:
        return redirect('/')
    user_id = user.user_id
    form = ChangeQuestionForm(question=user.question)
    if form.validate_on_submit():
        user.question, user.answer = form.question.data, form.answer.data
        db.session.commit()
        return redirect('/settings')
    return render_template('question.html', form=form, user_id=user_id, message='', color=user.color)


@app.post('/delete_account')
@login_required
def delete_account():
    user = current_user
    if not user:
        return redirect('/')
    user_id = user.user_id
    for comment in Comment.query.filter_by(user_id=user_id).all():
        db.session.delete(comment)
    for post in Post.query.filter_by(poster_id=user_id).all():
        for comments in Comment.query.filter_by(post_id=post.post_id).all():
            for elem in User.query.all():
                if comments in elem.liked_comment:
                    elem.liked_comment.remove(comments)
            db.session.delete(comments)
        for likers in User.query.all():
            if post in likers.liked_post:
                likers.liked_post.remove(post)
        db.session.delete(post)
        if os.path.exists(f'static/post.{post.post_id}.docx'):
            os.remove(f'static/post.{post.post_id}.docx')
        flag = False
        for posts in Post.query.all():
            if posts.image == post.image:
                flag = True
                break
        if not flag:
            os.remove(f'static/{post.image}')
    for followed in user.follows:
        followed.followers -= 1
    db.session.delete(user)
    db.session.commit()
    if os.path.exists(f'static/user.{user_id}.docx'):
        os.remove(f'static/user.{user_id}.docx')
    return redirect('/')


user_fields = {'user_id': fields.Integer, 'email': fields.String, 'username': fields.String, 'question': fields.String,
               'age': fields.Integer, 'received': fields.Integer, 'followers': fields.Integer}
post_fields = {'post_id': fields.Integer, 'image': fields.String, 'title': fields.String, 'description': fields.String,
               'age': fields.Integer, 'likes': fields.Integer, 'poster_name': fields.String}
comment_fields = {'comment_id': fields.Integer, 'contents': fields.String, 'likes': fields.Integer,
                  'age': fields.Integer, 'username': fields.String}
feed_fields = {'user_id': fields.Integer, 'posts': fields.List(fields.String),
               'recommended': fields.List(fields.String)}
follow_fields = {'followed_people': fields.List(fields.String)}
block_fields = {'blocked_people': fields.List(fields.String)}

user_parser, post_parser, comment_parser = reqparse.RequestParser(), reqparse.RequestParser(), reqparse.RequestParser()
follow_parser, block_parser = reqparse.RequestParser(), reqparse.RequestParser()
like_post_parser, like_comment_parser = reqparse.RequestParser(), reqparse.RequestParser()
user_parser.add_argument('email')
user_parser.add_argument('username')
user_parser.add_argument('password')
user_parser.add_argument('question')
user_parser.add_argument('answer')
post_parser.add_argument('title')
post_parser.add_argument('description')
post_parser.add_argument('image')
post_parser.add_argument('user_id')
post_parser.add_argument('password')
comment_parser.add_argument('contents')
comment_parser.add_argument('password')
follow_parser.add_argument('follow_id')
follow_parser.add_argument('password')
block_parser.add_argument('block_id')
block_parser.add_argument('password')
like_post_parser.add_argument('post_id')
like_post_parser.add_argument('password')
like_comment_parser.add_argument('comment_id')
like_comment_parser.add_argument('password')


class NotFoundError(HTTPException):
    def __init__(self, message):
        self.response = make_response(json.dumps({'error_message': message}), 404)


class BadRequest(HTTPException):
    def __init__(self, error_code, message):
        self.response = make_response(json.dumps({'error_code': error_code, 'error_message': message}), 400)


class InternalServerError(HTTPException):
    def __init__(self):
        self.response = make_response(json.dumps({'error_message': 'Internal Server Error'}), 500)


class Conflict(HTTPException):
    def __init__(self, message):
        self.response = make_response(json.dumps({'error_message': message}), 409)


class UserAPI(Resource):
    @marshal_with(user_fields)
    def get(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if user:
            user.age = (datetime.now() - user.time).days
            db.session.commit()
            return user
        raise NotFoundError(message='User not found')

    @marshal_with(user_fields)
    def post(self):
        try:
            args = user_parser.parse_args()
            email = args.get('email', None)
            username = args.get('username', None)
            password = args.get('password', None)
            question = args.get('question', None)
            answer = args.get('answer', None)
        except:
            raise InternalServerError()
        else:
            if email is None:
                raise BadRequest(error_code='USER001', message='email required')
            if username is None:
                raise BadRequest(error_code='USER002', message='username required')
            if password is None:
                raise BadRequest(error_code='USER003', message='password required')
            if question is None:
                raise BadRequest(error_code='USER004', message='question required')
            if answer is None:
                raise BadRequest(error_code='USER005', message='answer to security question required')
            if '@' not in email or '.' not in email or email.index('@') > email.index('.') - 2 or email.count(
                    '@') + email.count('.') != 2 or email.index('@') == 0 or email.index('.') == len(email) - 1:
                raise BadRequest(error_code='USER006', message='Invalid email')
            if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
                raise Conflict('User already exists')
            user = User(email=email, username=username, password=password, question=question, answer=answer,
                        received=0, followers=0, level=1, color='lightblue', sort=0)
            db.session.add(user)
            db.session.commit()
            user.age = (datetime.now() - user.time).days
            db.session.commit()
            return user, 201

    @marshal_with(user_fields)
    def put(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if user is None:
            raise NotFoundError(message='User not found')
        try:
            args = user_parser.parse_args()
            email = args.get('email', None)
            username = args.get('username', None)
            password = args.get('password', None)
            question = args.get('question', None)
            answer = args.get('answer', None)
        except:
            raise InternalServerError()
        else:
            if email is None:
                raise BadRequest(error_code='USER001', message='email required')
            if username is None:
                raise BadRequest(error_code='USER002', message='username required')
            if password is None:
                raise BadRequest(error_code='USER003', message='password required')
            if question is None:
                raise BadRequest(error_code='USER004', message='question required')
            if answer is None:
                raise BadRequest(error_code='USER005', message='answer to security question required')
            if password != user.password:
                raise BadRequest(error_code='USER006', message='Incorrect password')
            if '@' not in email or '.' not in email or email.index('@') > email.index('.') - 2 or email.count(
                    '@') + email.count('.') != 2 or email.index('@') == 0 or email.index('.') == len(email) - 1:
                raise BadRequest(error_code='USER007', message='Invalid email')
            if email != user.email and User.query.filter_by(email=email).first():
                raise Conflict('Email already exists')
            if username != user.username and User.query.filter_by(username=username).first():
                raise Conflict('Username is taken')
            user.email, user.username, user.question, user.answer = email, username, question, answer
            user.age = (datetime.now() - user.time).days
            db.session.commit()
            return user

    def delete(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if user is None:
            raise NotFoundError(message='User not found')
        try:
            args = user_parser.parse_args()
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if password is None:
                raise BadRequest(error_code='USER003', message='password required')
            if password != user.password:
                raise BadRequest(error_code='USER006', message='Incorrect password')
            for comment in Comment.query.filter_by(user_id=user_id).all():
                db.session.delete(comment)
            for post in Post.query.filter_by(poster_id=user_id).all():
                for comments in Comment.query.filter_by(post_id=post.post_id).all():
                    for elem in User.query.all():
                        if comments in elem.liked_comment:
                            elem.liked_comment.remove(comments)
                    db.session.delete(comments)
                for likers in User.query.all():
                    if post in likers.liked_post:
                        likers.liked_post.remove(post)
                db.session.delete(post)
                if os.path.exists(f'static/post.{post.post_id}.docx'):
                    os.remove(f'static/post.{post.post_id}.docx')
                flag = False
                for posts in Post.query.all():
                    if posts.image == post.image:
                        flag = True
                        break
                if not flag and os.path.exists(f'static/{post.image}'):
                    os.remove(f'static/{post.image}')
            for followed in user.follows:
                followed.followers -= 1
            db.session.delete(user)
            db.session.commit()
            if os.path.exists(f'static/user.{user_id}.docx'):
                os.remove(f'static/user.{user_id}.docx')
            return 'Successfully deleted'


class PostAPI(Resource):
    @marshal_with(post_fields)
    def get(self, post_id):
        post = Post.query.filter_by(post_id=post_id).first()
        if post:
            post.age = (datetime.now() - post.time).days
            db.session.commit()
            return post
        raise NotFoundError(message='Post not found')

    @marshal_with(post_fields)
    def post(self):
        try:
            args = post_parser.parse_args()
            title = args.get('title', None)
            description = args.get('description', None)
            image = args.get('image', None)
            user_id = args.get('user_id', None)
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if title is None:
                raise BadRequest(error_code='POST001', message='title required')
            if image is None:
                raise BadRequest(error_code='POST002', message='image required')
            if user_id is None:
                raise BadRequest(error_code='POST003', message='user id required')
            if password is None:
                raise BadRequest(error_code='POST004', message='password required')
            user = User.query.filter_by(user_id=user_id).first()
            if user is None:
                raise NotFoundError(message='User not found')
            if password != user.password:
                raise BadRequest(error_code='POST005', message='Incorrect password')
            post = Post(title=title, description=description, image=image, likes=0, poster_id=user_id,
                        poster_name=user.username, archived=0, active=0)
            db.session.add(post)
            db.session.commit()
            post.age = (datetime.now() - post.time).days
            db.session.commit()
            return post, 201

    @marshal_with(post_fields)
    def put(self, post_id):
        post = Post.query.filter_by(post_id=post_id).first()
        if post is None:
            raise NotFoundError(message='Post not found')
        try:
            args = post_parser.parse_args()
            title = args.get('title', None)
            description = args.get('description', None)
            image = args.get('image', None)
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if password is None:
                raise BadRequest(error_code='POST004', message='password required')
            user = User.query.filter_by(user_id=post.poster_id).first()
            if password != user.password:
                raise BadRequest(error_code='POST005', message='Incorrect password')
            if post.archived:
                raise Conflict(message="You aren't allowed to edit an archived post")
            post.age = (datetime.now() - post.time).days
            db.session.commit()
            if post.age >= 1 or post.likes > 0:
                raise Conflict(
                    message="You aren't allowed to edit a post that is more than a day old or has received likes")
            if title:
                post.title = title
            if image:
                flag = False
                for posts in Post.query.all():
                    if posts.image == post.image and posts != post:
                        flag = True
                        break
                if not flag and os.path.exists(f'static/{post.image}'):
                    os.remove(f'static/{post.image}')
                post.image = image
            post.description = description
            db.session.commit()
            return post

    def delete(self, post_id):
        post = Post.query.filter_by(post_id=post_id).first()
        if post is None:
            raise NotFoundError(message='Post not found')
        try:
            args = post_parser.parse_args()
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            user = User.query.filter_by(user_id=post.poster_id).first()
            if password is None:
                raise BadRequest(error_code='POST004', message='password required')
            if password != user.password:
                raise BadRequest(error_code='POST005', message='Incorrect password')
            for comment in Comment.query.filter_by(post_id=post_id).all():
                for elem in User.query.all():
                    if comment in elem.liked_comment:
                        elem.liked_comment.remove(comment)
                db.session.delete(comment)
            user.received -= post.likes
            for elem in User.query.all():
                if post in elem.liked_post:
                    elem.liked_post.remove(post)
            db.session.delete(post)
            db.session.commit()
            if os.path.exists(f'static/post.{post_id}.docx'):
                os.remove(f'static/post.{post_id}.docx')
            flag = False
            for posts in Post.query.all():
                if posts.image == post.image:
                    flag = True
                    break
            if not flag and os.path.exists(f'static/{post.image}'):
                os.remove(f'static/{post.image}')
            return 'Successfully deleted'


class CommentAPI(Resource):
    @marshal_with(comment_fields)
    def get(self, comment_id):
        comment = Comment.query.filter_by(comment_id=comment_id).first()
        if comment:
            comment.age = (datetime.now() - comment.time).days
            db.session.commit()
            return comment
        raise NotFoundError(message='Comment not found')

    @marshal_with(comment_fields)
    def post(self, user_id, post_id):
        try:
            args = comment_parser.parse_args()
            contents = args.get('contents', None)
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            user = User.query.filter_by(user_id=user_id).first()
            post = Post.query.filter_by(post_id=post_id).first()
            if user is None:
                raise NotFoundError(message='User not found')
            if post is None:
                raise NotFoundError(message='Post not found')
            if contents is None:
                raise BadRequest(error_code='COMMENT001', message='Comment must not be empty')
            if password is None:
                raise BadRequest(error_code='COMMENT002', message='password required')
            if password != user.password:
                raise BadRequest(error_code='COMMENT003', message='Incorrect password')
            if post.archived or post.active:
                raise Conflict(
                    message="You aren't allowed to comment on an archived post or whose comments have been turned off")
            comment = Comment(contents=contents, user_id=user_id, post_id=post_id, username=user.username, likes=0)
            db.session.add(comment)
            db.session.commit()
            comment.age = (datetime.now() - comment.time).days
            db.session.commit()
            return comment, 201

    @marshal_with(comment_fields)
    def put(self, comment_id):
        comment = Comment.query.filter_by(comment_id=comment_id).first()
        if comment is None:
            raise NotFoundError(message='Comment not found')
        try:
            args = comment_parser.parse_args()
            contents = args.get('contents', None)
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if contents is None:
                raise BadRequest(error_code='COMMENT001', message='Comment must not be empty')
            if password is None:
                raise BadRequest(error_code='COMMENT002', message='password required')
            post = Post.query.filter_by(post_id=comment.post_id).first()
            user = Post.query.filter_by(user_id=comment.user_id).first()
            if password != user.password:
                raise BadRequest(error_code='COMMENT003', message='Incorrect password')
            if post.archived:
                raise Conflict(message="You aren't allowed to edit comments on an archived post")
            comment.age = (datetime.now() - comment.time).days
            db.session.commit()
            if comment.age >= 1 or comment.likes > 0:
                raise Conflict(
                    message="You aren't allowed to edit a comment that is more than a day old or has received likes")
            comment.contents = contents
            db.session.commit()
            return comment

    def delete(self, comment_id):
        comment = Comment.query.filter_by(comment_id=comment_id).first()
        if comment is None:
            raise NotFoundError(message='Comment not found')
        try:
            args = comment_parser.parse_args()
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if password is None:
                raise BadRequest(error_code='COMMENT002', message='password required')
            user = Post.query.filter_by(user_id=comment.user_id).first()
            if password != user.password:
                raise BadRequest(error_code='COMMENT003', message='Incorrect password')
            post = Post.query.filter_by(post_id=comment.post_id).first()
            if post.archived:
                raise Conflict(message="You aren't allowed to delete comments on an archived post")
            for user in User.query.all():
                if comment in user.liked_comment:
                    user.liked_comment.remove(comment)
            user = User.query.filter_by(user_id=comment.user_id).first()
            user.received -= comment.likes
            db.session.delete(comment)
            db.session.commit()
            return 'Successfully deleted'


class FeedAPI(Resource):
    @marshal_with(feed_fields)
    def get(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if user is None:
            raise NotFoundError(message='User not found')
        posts = []
        for follow in user.follows:
            posts += Post.query.filter_by(poster_id=follow.user_id).all()
        if user.sort == 0:
            posts.sort(key=lambda x: x.post_id, reverse=True)
        if user.sort == 1:
            posts.sort(key=lambda x: x.likes, reverse=True)
        notfollow = []
        for unfollow in User.query.all():
            if unfollow not in user.follows and unfollow not in user.blocked and unfollow.level > 0:
                notfollow += Post.query.filter_by(poster_id=unfollow.user_id).all()
        if user.sort == 0:
            notfollow.sort(key=lambda x: x.post_id, reverse=True)
        if user.sort == 1:
            notfollow.sort(key=lambda x: x.likes, reverse=True)
        posts += notfollow
        for post in posts:
            if post.archived:
                posts.remove(post)
        posts = [elem.title for elem in posts]
        valid = [(elem, elem.received) for elem in User.query.all() if elem not in user.follows
                 and elem not in user.blocked and elem.level > 0 and elem != user]
        if valid:
            recommended = sorted(valid, key=lambda x: x[1], reverse=True)
            recommended = [elem[0].username for elem in recommended]
        else:
            recommended = None
        feed.user_id, feed.posts, feed.recommended = user_id, posts, recommended
        db.session.commit()
        return feed


class FollowAPI(Resource):
    @marshal_with(follow_fields)
    def get(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if user is None:
            raise NotFoundError(message='User not found')
        follow.followed_people = [elem.username for elem in user.follows]
        return follow

    @marshal_with(follow_fields)
    def post(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if user is None:
            raise NotFoundError(message='User not found')
        try:
            args = follow_parser.parse_args()
            follow_id = args.get('follow_id', None)
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if follow_id is None:
                raise BadRequest(error_code='FOLLOW001', message='follow_id required')
            if password is None:
                raise BadRequest(error_code='FOLLOW002', message='password required')
            if password != user.password:
                raise BadRequest(error_code='FOLLOW003', message='Incorrect password')
            account = User.query.filter_by(user_id=follow_id).first()
            if account is None:
                raise NotFoundError(message='Account to be followed not found')
            if follow_id == user_id:
                raise Conflict(message='Account cannot follow itself')
            if account in user.follows:
                raise Conflict(message='User already follows account')
            if account in user.blocked:
                raise Conflict(message='User has blocked account')
            if account.level == 0:
                raise Conflict(message='Cannot follow banned account')
            user.follows.append(account)
            account.followers += 1
            db.session.commit()
            follow.followed_people = [elem.username for elem in user.follows]
            return follow, 201

    def delete(self, user_id, follow_id):
        user = User.query.filter_by(user_id=user_id).first()
        account = User.query.filter_by(user_id=follow_id).first()
        if user is None:
            raise NotFoundError(message='User not found')
        if account is None:
            raise NotFoundError(message='Followed account not found')
        try:
            args = follow_parser.parse_args()
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if password is None:
                raise BadRequest(error_code='FOLLOW002', message='password required')
            if password != user.password:
                raise BadRequest(error_code='FOLLOW003', message='Incorrect password')
            if user_id == follow_id:
                raise Conflict(message='Account cannot follow itself')
            if account not in user.follows:
                raise Conflict(message='User does not follow account')
            user.follows.remove(account)
            account.followers -= 1
            db.session.commit()
            return 'Successfully unfollowed'


class BlockAPI(Resource):
    @marshal_with(block_fields)
    def get(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if user is None:
            raise NotFoundError(message='User not found')
        block.blocked_people = [elem.username for elem in user.blocked]
        return block

    @marshal_with(block_fields)
    def post(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if user is None:
            raise NotFoundError(message='User not found')
        try:
            args = block_parser.parse_args()
            block_id = args.get('block_id', None)
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if block_id is None:
                raise BadRequest(error_code='BLOCK001', message='block_id required')
            if password is None:
                raise BadRequest(error_code='BLOCK002', message='password required')
            if password != user.password:
                raise BadRequest(error_code='BLOCK003', message='Incorrect password')
            account = User.query.filter_by(user_id=block_id).first()
            if account is None:
                raise NotFoundError(message='Account to be followed not found')
            if block_id == user_id:
                raise Conflict(message='Account cannot block itself')
            if account in user.follows:
                raise Conflict(message='User follows account')
            if account in user.blocked:
                raise Conflict(message='User has already blocked account')
            user.blocked.append(account)
            db.session.commit()
            block.blocked_people = [elem.username for elem in user.blocked]
            return block, 201

    def delete(self, user_id, block_id):
        user = User.query.filter_by(user_id=user_id).first()
        account = User.query.filter_by(user_id=block_id).first()
        if user is None:
            raise NotFoundError(message='User not found')
        if account is None:
            raise NotFoundError(message='Blocked account not found')
        try:
            args = block_parser.parse_args()
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if password is None:
                raise BadRequest(error_code='BLOCK002', message='password required')
            if password != user.password:
                raise BadRequest(error_code='BLOCK003', message='Incorrect password')
            if user_id == block_id:
                raise Conflict(message='Account cannot block itself')
            if account not in user.blocked:
                raise Conflict(message='User does not block account')
            user.blocked.remove(account)
            db.session.commit()
            return 'Successfully unblocked'


class LikePostAPI(Resource):
    @marshal_with(post_fields)
    def post(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            raise NotFoundError(message='User not found')
        try:
            args = like_post_parser.parse_args()
            post_id = args.get('post_id', None)
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if post_id is None:
                raise BadRequest(error_code='LIKEPOST001', message='post_id required')
            if password is None:
                raise BadRequest(error_code='LIKEPOST002', message='password required')
            post = Post.query.filter_by(post_id=post_id).first()
            if post is None:
                raise NotFoundError(message='Post not found')
            poster = User.query.filter_by(user_id=post.poster_id).first()
            if poster is None:
                raise Conflict(message='Poster account has been deleted')
            if password != user.password:
                raise BadRequest(error_code='LIKEPOST003', message='Incorrect password')
            if post.archived:
                raise Conflict(message='Cannot like an archived post')
            if post.poster_id == user_id:
                raise Conflict(message='Cannot like your own post')
            if post in user.liked_post:
                raise Conflict(message='Already liked post')
            user.liked_post.append(post)
            post.likes += 1
            poster.received += 1
            post.age = (datetime.now() - post.time).days
            db.session.commit()
            return post, 201

    @marshal_with(post_fields)
    def delete(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            raise NotFoundError(message='User not found')
        try:
            args = like_post_parser.parse_args()
            post_id = args.get('post_id', None)
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if post_id is None:
                raise BadRequest(error_code='LIKEPOST001', message='post_id required')
            if password is None:
                raise BadRequest(error_code='LIKEPOST002', message='password required')
            post = Post.query.filter_by(post_id=post_id).first()
            if post is None:
                raise NotFoundError(message='Post not found')
            poster = User.query.filter_by(user_id=post.poster_id).first()
            if poster is None:
                raise Conflict(message='Poster account has been deleted')
            if password != user.password:
                raise BadRequest(error_code='LIKEPOST003', message='Incorrect password')
            if post.archived:
                raise Conflict(message='Cannot like an archived post')
            if post.poster_id == user_id:
                raise Conflict(message='Cannot like your own post')
            if post not in user.liked_post:
                raise Conflict(message='User does not like post')
            user.liked_post.remove(post)
            post.likes -= 1
            poster.received -= 1
            post.age = (datetime.now() - post.time).days
            db.session.commit()
            return post


class LikeCommentAPI(Resource):
    @marshal_with(comment_fields)
    def post(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            raise NotFoundError(message='User not found')
        try:
            args = like_comment_parser.parse_args()
            comment_id = args.get('comment_id', None)
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if comment_id is None:
                raise BadRequest(error_code='LIKECOMMENT001', message='comment_id required')
            if password is None:
                raise BadRequest(error_code='LIKECOMMENT002', message='password required')
            comment = Comment.query.filter_by(comment_id=comment_id).first()
            if comment is None:
                raise NotFoundError(message='Comment not found')
            post = Post.query.filter_by(post_id=comment.post_id).first()
            if post is None:
                raise Conflict(message='Post has been deleted')
            commenter = User.query.filter_by(user_id=comment.user_id).first()
            if commenter is None:
                raise Conflict(message='Commenter account has been deleted')
            poster = User.query.filter_by(user_id=post.poster_id).first()
            if poster is None:
                raise Conflict(message='Poster account has been deleted')
            if password != user.password:
                raise BadRequest(error_code='LIKECOMMENT003', message='Incorrect password')
            if post.archived:
                raise Conflict(message='Cannot like comment of an archived post')
            if comment.user_id == user_id:
                raise Conflict(message='Cannot like your own comment')
            if comment in user.liked_comment:
                raise Conflict(message='Already liked comment')
            user.liked_comment.append(comment)
            comment.likes += 1
            commenter.received += 1
            comment.age = (datetime.now() - comment.time).days
            db.session.commit()
            return comment, 201

    @marshal_with(comment_fields)
    def delete(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            raise NotFoundError(message='User not found')
        try:
            args = like_post_parser.parse_args()
            comment_id = args.get('comment_id', None)
            password = args.get('password', None)
        except:
            raise InternalServerError()
        else:
            if comment_id is None:
                raise BadRequest(error_code='LIKECOMMENT001', message='comment_id required')
            if password is None:
                raise BadRequest(error_code='LIKECOMMENT002', message='password required')
            comment = Comment.query.filter_by(comment_id=comment_id).first()
            if comment is None:
                raise NotFoundError(message='Comment not found')
            post = Post.query.filter_by(post_id=comment.post_id).first()
            if post is None:
                raise NotFoundError(message='Post has been deleted')
            commenter = User.query.filter_by(user_id=comment.user_id).first()
            if commenter is None:
                raise Conflict(message='Commenter account has been deleted')
            poster = User.query.filter_by(user_id=post.poster_id).first()
            if poster is None:
                raise Conflict(message='Poster account has been deleted')
            if password != user.password:
                raise BadRequest(error_code='LIKECOMMENT003', message='Incorrect password')
            if post.archived:
                raise Conflict(message='Cannot like comment of an archived post')
            if comment.user_id == user_id:
                raise Conflict(message='Cannot like your own comment')
            if comment not in user.liked_comment:
                raise Conflict(message='User does not like comment')
            user.liked_comment.remove(comment)
            comment.likes -= 1
            comment.received -= 1
            comment.age = (datetime.now() - comment.time).days
            db.session.commit()
            return comment


api.add_resource(UserAPI, '/api/user', '/api/user/<user_id>')
api.add_resource(PostAPI, '/api/post', '/api/post/<post_id>')
api.add_resource(CommentAPI, '/api/comment/<comment_id>', '/api/comment/<user_id>/<post_id>')
api.add_resource(FeedAPI, '/api/feed/<user_id>')
api.add_resource(FollowAPI, '/api/follow/<user_id>', '/api/follow/<user_id>/<follow_id>')
api.add_resource(BlockAPI, '/api/block/<user_id>', '/api/block/<user_id>/<block_id>')
api.add_resource(LikePostAPI, '/api/like_post/<user_id>')
api.add_resource(LikeCommentAPI, '/api/like_comment/<user_id>')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
