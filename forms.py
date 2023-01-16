from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, SelectField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from flask_wtf.file import FileField, FileRequired


class SignupForm(FlaskForm):
    email = StringField("Email", [Email(message="Not a valid email address"), DataRequired()])
    name = StringField("Username", [Length(max=20), DataRequired()])
    password = PasswordField("Password", [DataRequired()])
    confirmPassword = PasswordField("Repeat Password", [EqualTo('password', message="Passwords must match")])
    question = SelectField(
        "Security Question",
        [DataRequired()],
        choices=[
            ("In what city were you born?", "In what city were you born?"),
            ("What is your mother's maiden name?", "What is your mother's maiden name?"),
            ("What high school did you attend?", "What high school did you attend?"),
            ("What was your favorite food as a child?", "What was your favorite food as a child?"),
            ("What year was your father born?", "What year was your father born?"),
        ],
    )
    answer = StringField("Answer", [DataRequired()])
    submit = SubmitField("Signup")


class LoginForm(FlaskForm):
    name = StringField("Username", [Length(max=20), DataRequired()])
    password = PasswordField("Password", [DataRequired()])
    status = BooleanField("Remember me")
    submit = SubmitField("Login")


class ChangePasswordForm(FlaskForm):
    name = StringField('Username', [Length(max=20), DataRequired()])
    old_password = PasswordField("Current Password", [DataRequired()])
    new_password = PasswordField("New Password", [DataRequired()])
    confirmPassword = PasswordField("Confirm Password", [EqualTo('new_password', message="Passwords must match")])
    submit = SubmitField("Change")


class ForgotForm(FlaskForm):
    name = StringField("Username", [Length(max=20), DataRequired()])
    question = SelectField(
        "Security Question",
        [DataRequired()],
        choices=[
            ("In what city were you born?", "In what city were you born?"),
            ("What is your mother's maiden name?", "What is your mother's maiden name?"),
            ("What high school did you attend?", "What high school did you attend?"),
            ("What was your favorite food as a child?", "What was your favorite food as a child?"),
            ("What year was your father born?", "What year was your father born?"),
        ],
    )
    answer = StringField("Answer", [DataRequired()])
    submit = SubmitField("Submit")


class ChangeUsernameForm(FlaskForm):
    name = StringField('Current Username', [Length(max=20), DataRequired()])
    new_name = StringField("New Username", [Length(max=20), DataRequired()])
    confirmname = StringField("Confirm Username", [Length(max=20), DataRequired(), EqualTo('new_name', message="Username must match")])
    submit = SubmitField("Change")


class ChangeEmailForm(FlaskForm):
    email = StringField('Current Email', [Email(message="Not a valid email address"), DataRequired()])
    new_email = StringField("New Email", [Email(message="Not a valid email address"), DataRequired()])
    confirmemail = StringField("Confirm Email", [EqualTo('new_email', message="Email must match")])
    submit = SubmitField("Change")


class ChangeQuestionForm(FlaskForm):
    question = SelectField(
        "New Security Question",
        [DataRequired()],
        choices=[
            ("In what city were you born?", "In what city were you born?"),
            ("What is your mother's maiden name?", "What is your mother's maiden name?"),
            ("What high school did you attend?", "What high school did you attend?"),
            ("What was your favorite food as a child?", "What was your favorite food as a child?"),
            ("What year was your father born?", "What year was your father born?"),
        ]
    )
    answer = StringField("Answer", [DataRequired()])
    submit = SubmitField("Change")


class CreateForm(FlaskForm):
    title = StringField("Title of post", [Length(max=30), DataRequired()])
    description = TextAreaField("Description of post")
    photo = FileField('Upload picture', [FileRequired()])
    archived = BooleanField("Private")
    active = BooleanField("Turn off comments")
    submit = SubmitField("Create")


class EditPostForm(FlaskForm):
    title = StringField("New title", [Length(max=30)])
    description = TextAreaField("New description")
    photo = FileField('Upload picture')
    submit = SubmitField("Edit")


class CommentForm(FlaskForm):
    content = TextAreaField([DataRequired()])
    submit = SubmitField('Comment')


class EditCommentForm(FlaskForm):
    content = TextAreaField("New contents", [DataRequired()])
    submit = SubmitField("Edit")


class ColorForm(FlaskForm):
    color = SelectField('Background color', [DataRequired()], choices=[('lightblue', 'Blue'), ('lightgreen', 'Green'), ('yellow', 'Yellow'), ('white', 'White'), ('crimson', 'Red')])
    submit = SubmitField("Save")


class SortForm(FlaskForm):
    sort = SelectField('Posts in feed sorted by', [DataRequired()], choices=[(0, 'Latest first'), (1, 'Most popular first')])
    submit = SubmitField("Save")
