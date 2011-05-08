#!/usr/bin/env python

##################################################################################################
# This GAE project provides sample code that demonstrates how to create a minimal web app
# that logins users with their Twitter account and displays only their most relevant tweets
# (as determined by a trivial algorithm that can easily be modified/extended) as part of a 
# UX that is optimized for a mobile client. First-time visitors get to login free for a number
# of times and experience the app before they are requested to purchase additional logins to
# continue using the app.
#
# Mike Knapp's https://github.com/mikeknapp/AppEngine-OAuth-Library project is used to 
# handle making OAuth requests to Twitter.
#
# Pat Coll's https://github.com/patcoll/paypal-python project is adapted to implement
# a (Mobile) Express Checkout flow using PayPal
#
# The application's primary UI is adapted from the final installment of SitePen's TweetView
# project at http://dojotoolkit.org/documentation/tutorials/1.6/mobile/tweetview/packaging/ 
# and is intended to be delivered to a mobile display like an iPhone, although development
# works fine on a desktop browser like WebKit. The UI for the payflows is minimal.
##################################################################################################

import os
import random
import operator
import logging

from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db
from django.utils import simplejson as json
from google.appengine.ext.webapp import template

import oauth

from paypal.interface import PayPalInterface

# Copy config.template.py to config.py and fill in these values in that file

from config import CONSUMER_KEY,\
                   CONSUMER_SECRET,\
                   PP_API_USERNAME,\
                   PP_API_PASSWORD,\
                   PP_API_SIGNATURE

# A simple (twitter_username, requests_remaining) tuple to track logins so that users can be
# charged for access. By default, users get 25 free logins. No additional user information is 
# stored in an attempt to keep this app as minimal and stateless as possible. (And memcache is
# used to implement a minimalist session management scheme to keep track of the user between
# requests.)

class User(db.Model):
  twitter_username = db.StringProperty(required=True)
  requests_remaining = db.IntegerProperty(required=True, default=25)

# Logic for interacting wtih PayPal's ExpressCheckout product

class PaymentHandler(webapp.RequestHandler):

  def _getPayPal(self):

    return PayPalInterface(API_USERNAME=PP_API_USERNAME, API_PASSWORD=PP_API_PASSWORD, API_SIGNATURE=PP_API_SIGNATURE)

  def _getProduct(self):

    # The app only features a single product: 100 login requests for a fixed price

    return {'price' : 10.00, 'quantity' : 100, 'units' : 'login requests'}

  def post(self, mode=""):

    if mode == "set_ec":

      sid = self.request.get("sid")
      user_info = memcache.get(sid)

      product = self._getProduct()

      pp = self._getPayPal()
      response = pp.set_express_checkout(amt=str(product['price']), returnurl=self.request.host_url+"/get_ec_details?sid="+sid, \
                 cancelurl=self.request.host_url+"/cancel_ec?sid="+sid, paymentaction='Order')

      if not response.success:
        logging.error("Failure for SetExpressCheckout")

        template_values = {
          'title' : 'Error',
          'operation' : 'SetExpressCheckout'
        }
        
        path = os.path.join(os.path.dirname(__file__), 'templates', 'unknown_error.html')
        return self.response.out.write(template.render(path, template_values))

      # Redirect to PayPal and allow user to confirm payment details.
      # Then PayPal redirects back to the /get_ec_details or /cancel_ec endpoints.
      # Assuming /get_ec_details, we complete the transaction with pp.get_express_checkout_details
      # and pp.do_express_checkout_payment

      redirect_url = pp.generate_express_checkout_redirect_url(response.TOKEN)
      return self.redirect(redirect_url)


    else:
      logging.error("Unknown mode for POST request!")

  def get(self, mode=""):
    if mode == "get_ec_details":
      pp = self._getPayPal()
      response = pp.get_express_checkout_details(self.request.get("token"))

      if not response.success:
        logging.error("Failure for GetExpressCheckoutDetails")

        template_values = {
          'title' : 'Error',
          'operation' : 'GetExpressCheckoutDetails'
        }
        
        path = os.path.join(os.path.dirname(__file__), 'templates', 'unknown_error.html')
        return self.response.out.write(template.render(path, template_values))

      product = self._getProduct()

      template_values = {
        'title' : 'Confirm Purchase',
        'quantity' : product['quantity'], 
        'units' : product['units'], 
        'email' : response.EMAIL, 
        'amount' : response.AMT,
        'query_string_params' : self.request.query_string
      }

      path = os.path.join(os.path.dirname(__file__), 'templates', 'confirm_purchase.html')
      self.response.out.write(template.render(path, template_values))

    elif mode == "do_ec_payment":

      if memcache.get(self.request.get("sid")) is not None: # Without an account reference, we can't credit the purchase
        pp = self._getPayPal()
        payerid = self.request.get("PayerID")

        product = self._getProduct()

        response = pp.do_express_checkout_payment(self.request.get("token"), payerid=payerid, amt=str(product['price']), paymentaction='Sale')

        if not response.success:
          logging.error("Failure for DoExpressCheckoutPayment")

          template_values = {
            'title' : 'Error',
            'operation' : 'DoExpressCheckoutPayment'
          }
        
          path = os.path.join(os.path.dirname(__file__), 'templates', 'unknown_error.html')
          return self.response.out.write(template.render(path, template_values))

        # Recharge the user's account with logins

        user_info = memcache.get(self.request.get("sid"))
        twitter_username = user_info['username']
        query = User.all().filter("twitter_username =", twitter_username)
        user = query.get()
        product = self._getProduct()
        user.requests_remaining = product['quantity']
        db.put(user)

        template_values = {
          'title' : 'Successful Payment',
          'quantity' : product['quantity'],
          'units' : product['units']
        }
        
        path = os.path.join(os.path.dirname(__file__), 'templates', 'successful_payment.html')
        self.response.out.write(template.render(path, template_values))

      else:
        logging.error("Invalid/expired session in /do_ec_payment")

        template_values = {
          'title' : 'Session Expired',
        }

        path = os.path.join(os.path.dirname(__file__), 'templates', 'session_expired.html')
        self.response.out.write(template.render(path, template_values))

    elif mode == "cancel_ec":
      template_values = {
        'title' : 'Cancel Purchase',
      }

      path = os.path.join(os.path.dirname(__file__), 'templates', 'cancel_purchase.html')
      self.response.out.write(template.render(path, template_values))

# Logic for interacting with Twitter's API and serving up data, etc.

class AppHandler(webapp.RequestHandler):

  def _cleanupTerm(self, term):

    # Strip some common punctuation from terms that are extracted from tweets

    return term.strip(")").strip("(").strip("?").strip(":").strip(".")

  def _getStopwords(self):

    # This stopword list is adapted from nltk.corpus - See http://nltk.org

    return ('i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'via', 'rt', '-', '&', '')


  # The get method takes care of all api endpoints in this app except for /set_ec

  def get(self, mode=""):
    
    client = oauth.TwitterClient(CONSUMER_KEY, CONSUMER_SECRET, "%s/app" % self.request.host_url)
   
    # The /app context ensures that the user has remaining requests that 
    # they've paid for, computes relevance for tweets from their home timeline, 
    # stashes the data and serves up the app. The app then requests the stashed 
    # data via /data.

    if mode == "app":

      # Pull out auth token/verifier in order to get an access token
      # and in order to get some basic information about the user.
      # Subsequent requests will be performed via client.make_request

      auth_token = self.request.get("oauth_token")
      auth_verifier = self.request.get("oauth_verifier")
      user_info = client.get_user_info(auth_token, auth_verifier=auth_verifier)

      twitter_username = user_info['username']

      # Has a user already used this webapp with twitter_username?

      query = User.all().filter("twitter_username =", twitter_username)
      user = query.get()

      # If not, create a user (and give them some free logins to this app)

      if user is None:
        user = User(twitter_username=twitter_username, )
        user.put()

      # Avoid a full-blown Session implementation for purposes of simplicity in this demo code. (See 
      # http://stackoverflow.com/questions/2560022/simple-app-engine-sessions-implementation
      # for some very pragmatic tips on how you might approach that in a very lightweight fashion.)
      # Sessions will be needed in both the if and the else clause below, so go ahead and compute it

      sid = str(random.random())[5:] + str(random.random())[5:] + str(random.random())[5:]

      # If yes and if they have some logins remaining, service their request

      if user.requests_remaining > 0:

        # A trivial relevance algorithm for ranking tweets:
        # For this trivial algorithm, we'll compute the most frequent terms for the 
        # logged in user's favorite tweets and rank tweets in the home timeline as
        # being more relevant if they contain those terms. Obviously, you could be much
        # more creative, but this basic idea should get you on your way.

        # Fetch some data to be displayed and used in the relevance ranking. See
        # http://dev.twitter.com/doc for a full API listing

        data_urls = {
          "home_timeline" : "http://api.twitter.com/1/statuses/home_timeline.json",
          "favorites_timeline" : "http://api.twitter.com/1/favorites.json",
        }

        # Fetch the first 5 pages of results for the data urls. (More pages could be requested.)
        # By default, there are 20 tweets per page for favorites and the home timeline

        num_pages = 5
        data = {}
        for name, url in data_urls.items():
          data[name] = []
          for page in range(1,num_pages+1):
            result = client.make_request(url=url, token=user_info['token'], secret=user_info['secret'], additional_params={'page' : page})
            if result.status_code == 200:
              data[name] += json.loads(result.content)
            else:
              # Could do any number of useful things to actually handle this error
              logging.error(("Expected 200 response but received %d for request " + url) % (result.status_code, page,))

        # Split out the text of the tweets, remove some leading/trailing punctuation, and filter
        # common stopwords 

        terms = [
            self._cleanupTerm(term.lower())
            for tweet in data['favorites_timeline']
                for term in tweet['text'].split() 
                    if self._cleanupTerm(term.lower()) not in self._getStopwords()
        ]

        # Build a frequency map and sort by value

        freqs = {}
        for term in terms:
          freqs[term] = freqs.get(term, 0) + 1           

        sorted_terms = sorted(freqs.iteritems(), key=operator.itemgetter(1), reverse=True)

        # Iterate through each tweet in the home_timeline and assign a relevance score based upon 
        # the ratio of how many of the top N frequent terms from the favorities appeared in the tweet

        n = 200
        top_n_terms = set([term for (term, freq) in sorted_terms[:n]])

        # Useful for gaining intuition into how the trivial algorithm works

        logging.info("\n\nTOP N TERMS FROM FAVORITES:")
        logging.info(top_n_terms)
        logging.info("\n\n")

        for tweet in data['home_timeline']:
          tweet_terms = set([ self._cleanupTerm(term.lower())
                              for term in tweet['text'].split() 
                                if self._cleanupTerm(term.lower()) not in self._getStopwords()
                        ])

          num_frequent_terms = len(tweet_terms.intersection(top_n_terms))

          tweet['relevance'] = 1.0*num_frequent_terms/len(tweet_terms)

          # You could optionally do any number of other things like normalize tweet scores at this point,
          # boost relevance scores based upon additional criteria, throw in a random amount of serendipity 
          # into scores, etc. We'll just be boring  and filter out any tweet with a relevance greater than 0.0
          # so that only tweets with a relevance of 0.0 or higher are returned in the final response
          # The sky is the limit

        user_info['relevant_tweets'] = [tweet for tweet in data['home_timeline'] if tweet['relevance'] > 0]

        # For purposes of not frustrating users of this sample code who don't have any favorites (and would
        # hence not have any "relevant tweets", check to make sure at least one relevant tweet exists and
        # if it doesn't, just go ahead and assign all tweets as relevant since we have no information to 
        # otherwise make a decision
        if len(user_info['relevant_tweets']) == 0:
          user_info['relevant_tweets'] = data['home_timeline']

        # Store the ranked tweets as to user_info as "relevant_tweets" and 
        # stash the latest results from relevance algorithm so the client app can grab them
        # from a subsequent request to /data 
        memcache.set(sid, user_info, time=60*10) # seconds

        user.requests_remaining -= 1 # Meter the request
        db.put(user)

        # Redirect to a mobile client application that will use sid to make a request for the 
        # tweets we just filtered and stashed away

        return self.redirect('/tweetview/index.html?sid='+sid)
      
      # If an account exists but no logins are remaining, then direct the user to ante up
      # via a PayPal Express Checkout pay flow

      else: 

        # Store the user_info so we can retrieve it in the next request

        memcache.set(sid, user_info, time=60*10) # seconds

        template_values = {
          'title' : 'Recharge Account',
          'sid' : sid
        }

        path = os.path.join(os.path.dirname(__file__), 'templates', 'recharge_account.html')
        self.response.out.write(template.render(path, template_values))

    # Serves up stashed data (which takes place in a prior request to /app). A ?refresh=true parameter could
    # be built in to the /data request to charge the user for another request handle associated details if so
    # desired. This /data implementation simply returns the most previously calculated data

    elif mode == "data":

      user_info = memcache.get(self.request.get("sid"))
      self.response.headers.add_header('content-type', 'application/json', charset='utf-8')
      self.response.out.write(json.dumps(user_info['relevant_tweets'], indent=2))

    elif mode == "login":

      return self.redirect(client.get_authorization_url())

    else: # root URL context 

      template_values = {
        'title' : 'Tweet Relevance',
      }

      path = os.path.join(os.path.dirname(__file__), 'templates', 'root.html')
      self.response.out.write(template.render(path, template_values))

def main():

  application = webapp.WSGIApplication([('/(set_ec)', PaymentHandler),
                                        ('/(get_ec_details)', PaymentHandler),                                      
                                        ('/(do_ec_payment)', PaymentHandler),                                      
                                        ('/(cancel_ec)', PaymentHandler),                                      

                                        ('/(app)', AppHandler),
                                        ('/(data)', AppHandler),
                                        ('/(login)', AppHandler),
                                        ('/', AppHandler)],
                                       debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
