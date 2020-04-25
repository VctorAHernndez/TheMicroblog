from wtforms import Form, StringField, TextAreaField, validators

class ArticleForm(Form):
    ''' WTForm used for article edition and creation '''
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])