#import external libreries
import jinja2
import os
import webapp2
from google.appengine.ext import db
import json
import urllib
import urllib2
import logging
import datetime

#template jinja config
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)
#main render jinja function
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

CACHE = {}

def getPosts():
    global CACHE
    logging.error('FIRE! DB QUERY')
    time = datetime.datetime.now()
    posts = greetings = Post.all().order('-created')
    CACHE = {'posts':posts,'time':time}
    return CACHE


#main class with request handler
class BaseHandler(webapp2.RequestHandler):

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render(self, template, **kw):
        self.write(render_str(template, **kw))

    def render_json(self, d):
        json_txt = json.dumps(d)
        self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
        self.write(json_txt)

        # check is request is html or json and set format
    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        try:
            if self.request.url.endswith('.json'):
                self.format = 'json'
            else:
                self.format = 'html'
        except:
            pass


class MainPage(BaseHandler):

    def get(self):
        global CACHE

        if self.format == 'html':

            if self.request.url.endswith('/flush'):
                CACHE.clear()
                return self.redirect('/blog')

            if not 'time' in CACHE:
                CACHE = getPosts()

            number = datetime.datetime.now() - CACHE['time']

            self.render('front.html', posts = CACHE['posts'], number = int(number.total_seconds()))

        else:
            return self.render_json([p.as_dict() for p in posts])


class Post(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    # to render posts
    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        base = BaseHandler()
        return render_str("post.html", p = self)

    #add to model function to serialize to json
    def as_dict(self):
        time_fmt = '%c'
        d = {'subject': self.subject,
             'content': self.content,
             'created': self.created.strftime(time_fmt),
             'last_modified': self.last_modified.strftime(time_fmt)}
        return d

def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)


class BlogFront:
    pass

class PostPage(BaseHandler):

    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if self.format == 'html':
            self.render("permalink.html", post = post)
        else:
            self.render_json(post.as_dict())


class NewPostPage(BaseHandler):
    def get(self):
        self.render('login-form.html')

class NewPostPage(BaseHandler):

    def get(self):
        self.render('newpost.html')

    def post(self):
        subject = self.request.get('subject')
        content = self.request.get('content')

        p = Post(parent = blog_key(), subject = subject, content = content)
        p.put()
        self.redirect('/blog/%s' % str(p.key().id()))

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/blog/?(?:.json)?', MainPage),
                               ('/blog/([0-9]+)(?:.json)?', PostPage),
                               ('/blog/addpost', NewPostPage),
                               ('/blog/flush', MainPage),
                               ('/blog/login', LoginPage)
                               ],
                              debug=True)
