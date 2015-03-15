from werkzeug import secure_filename
from flask.ext.script import Manager
from flask.ext.migrate import Migrate
from flask.ext.migrate import MigrateCommand
from application import app
from application import db
from application import twitter_api
from application import imgur_client
from application.modules.posts.model import Post
from application.modules.posts.model import PostRating
from application.modules.posts.model import PostCustomFields
from application.modules.users.model import user_datastore
from application.helpers import encode_id
from application.helpers import slugify

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

@manager.command
def create_all_tables():
    db.create_all()

@manager.command
def runserver():
    import os
    os.environ['DEBUG'] = 'true'
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
    app.run()

@manager.command
def populate_for_testing():
    for x in range(50):
        post = Post(
            user_id=1,
            category_id=1,
            post_type_id=1,
            title='test '+str(x),
            slug='the-slug',
            content='<p>content</p>')
        db.session.add(post)
        db.session.commit()
        post.uuid = encode_id(post.id)
        db.session.commit()
        post_rating = PostRating(
            post_id=post.id,
            positive=0,
            negative=0
            )
        db.session.add(post_rating)
        post.update_hot()
        db.session.commit()
        print x

@manager.command
def twitter_fetch():
    # Fetch greatest id
    recent_tweets = twitter_api.search(q='#b3d -filter:retweets', rpp=100, page=2)
    print len(recent_tweets)
    for tweet in recent_tweets:
        #print dir(tweet)
        if tweet.favorite_count > 10:
            if not PostCustomFields.query\
                .filter_by(field_type='tweet_id', value=tweet.id_str)\
                .first():

                bot = user_datastore.get_user('bot@blender.today')
                # get category by parsing the tweet text
                title = (tweet.text[:60] + '..') if len(tweet.text) > 60 else tweet.text
                post = Post(
                    user_id=bot.id,
                    category_id=1,
                    post_type_id=1, #hardcoded to be a link
                    title=title,
                    slug=slugify(title),
                    content="https://twitter.com/{0}/status/{1}".format(
                        tweet.user.screen_name, tweet.id),
                    status='published'
                )
                db.session.add(post)
                db.session.commit()
                post.uuid = encode_id(post.id)
                twitter_id = PostCustomFields(
                    post_id=post.id,
                    field_type='tweet_id',
                    value=tweet.id_str)
                db.session.add(twitter_id)
                db.session.commit()

                post_rating = PostRating(
                    post_id=post.id,
                    positive=0,
                    negative=0
                    )
                db.session.add(post_rating)
                post.update_hot()
                # if form.picture.data:
                #     filename = secure_filename(form.picture.data.filename)
                #     filepath = '/tmp/' + filename
                #     form.picture.data.save(filepath)
                #     image = imgur_client.upload_from_path(filepath, config=None, anon=True)
                #     post.picture = image['id']
                #     post.picture_deletehash = image['deletehash']
                #     os.remove(filepath)
                db.session.commit()
                break

        print tweet.retweet_count
        print tweet.favorite_count
        print tweet.truncated
        print tweet.user.screen_name
        print "https://twitter.com/{0}/status/{1}".format(tweet.user.screen_name, tweet.id)
        print '----'
        #break
    # public_tweets = twitter_api.home_timeline()
    # for tweet in public_tweets:
    #     print tweet.url


manager.run()
