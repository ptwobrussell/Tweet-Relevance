# coding=utf-8
"""
The end developer will do most of their work with the PayPalInterface class found
in this module. Configuration, querying, and manipulation can all be done
with it.
"""

import types
import socket
import urllib
import urllib2
from urlparse import urlsplit, urlunsplit

from settings import PayPalConfig
from response import PayPalResponse
from exceptions import PayPalError, PayPalAPIResponseError
   
class PayPalInterface(object):
    """
    The end developers will do 95% of their work through this class. API
    queries, configuration, etc, all go through here. See the __init__ method
    for config related details.
    """
    def __init__(self , config=None, **kwargs):
        """
        Constructor, which passes all config directives to the config class
        via kwargs. For example:
        
            paypal = PayPalInterface(API_USERNAME='somevalue')
            
        Optionally, you may pass a 'config' kwarg to provide your own
        PayPalConfig object.
        """
        if config:
            # User provided their own PayPalConfig object.
            self.config = config
        else:
            # Take the kwargs and stuff them in a new PayPalConfig object.
            self.config = PayPalConfig(**kwargs)
        
    def _encode_utf8(self, **kwargs):
        """
        UTF8 encodes all of the NVP values.
        """
        unencoded_pairs = kwargs
        for i in unencoded_pairs.keys():
            if isinstance(unencoded_pairs[i], types.UnicodeType):
                unencoded_pairs[i] = unencoded_pairs[i].encode('utf-8')
        return unencoded_pairs
    
    def _check_required(self, requires, **kwargs):
        """
        Checks kwargs for the values specified in 'requires', which is a tuple
        of strings. These strings are the NVP names of the required values.
        """
        for req in requires:
            # PayPal api is never mixed-case.
            if req.lower() not in kwargs and req.upper() not in kwargs:
                raise PayPalError('missing required : %s' % req)
        
    def _call(self, method, **kwargs):
        """
        Wrapper method for executing all API commands over HTTP. This method is
        further used to implement wrapper methods listed here:
    
        https://www.x.com/docs/DOC-1374
    
        ``method`` must be a supported NVP method listed at the above address.
    
        ``kwargs`` will be a hash of
        """
        socket.setdefaulttimeout(self.config.HTTP_TIMEOUT)
    
        url_values = {
            'METHOD': method,
            'VERSION': self.config.API_VERSION
        }
    
        headers = {}
        if(self.config.API_AUTHENTICATION_MODE == "3TOKEN"):
            # headers['X-PAYPAL-SECURITY-USERID'] = API_USERNAME
            # headers['X-PAYPAL-SECURITY-PASSWORD'] = API_PASSWORD
            # headers['X-PAYPAL-SECURITY-SIGNATURE'] = API_SIGNATURE
            url_values['USER'] = self.config.API_USERNAME
            url_values['PWD'] = self.config.API_PASSWORD
            url_values['SIGNATURE'] = self.config.API_SIGNATURE
        elif(self.config.API_AUTHENTICATION_MODE == "UNIPAY"):
            # headers['X-PAYPAL-SECURITY-SUBJECT'] = SUBJECT
            url_values['SUBJECT'] = self.config.SUBJECT
        # headers['X-PAYPAL-REQUEST-DATA-FORMAT'] = 'NV'
        # headers['X-PAYPAL-RESPONSE-DATA-FORMAT'] = 'NV'
        # print(headers)

        for k,v in kwargs.iteritems():
            url_values[k.upper()] = v
        
        # When in DEBUG level 2 or greater, print out the NVP pairs.
        if self.config.DEBUG_LEVEL >= 2:
            k = url_values.keys()
            k.sort()
            for i in k:
               print " %-20s : %s" % (i , url_values[i])

        u2 = self._encode_utf8(**url_values)

        data = urllib.urlencode(u2)
        req = urllib2.Request(self.config.API_ENDPOINT, data, headers)
        response = PayPalResponse(urllib2.urlopen(req).read(), self.config)

        if self.config.DEBUG_LEVEL >= 1:
            print " %-20s : %s" % ("ENDPOINT", self.config.API_ENDPOINT)
    
        if not response.success:
            if self.config.DEBUG_LEVEL >= 1:
                print response
            raise PayPalAPIResponseError(response)

        return response

    def address_verify(self, email, street, zip):
        """Shortcut for the AddressVerify method.
    
        ``email``::
            Email address of a PayPal member to verify.
            Maximum string length: 255 single-byte characters
            Input mask: ?@?.??
        ``street``::
            First line of the billing or shipping postal address to verify.
    
            To pass verification, the value of Street must match the first three
            single-byte characters of a postal address on file for the PayPal member.
    
            Maximum string length: 35 single-byte characters.
            Alphanumeric plus - , . ‘ # \
            Whitespace and case of input value are ignored.
        ``zip``::
            Postal code to verify.
    
            To pass verification, the value of Zip mustmatch the first five
            single-byte characters of the postal code of the verified postal
            address for the verified PayPal member.
    
            Maximumstring length: 16 single-byte characters.
            Whitespace and case of input value are ignored.
        """
        args = locals()
        del args['self']
        return self._call('AddressVerify', **args)

    def get_express_checkout_details(self, token):
        """Shortcut for the GetExpressCheckoutDetails method.
        """
        return self._call('GetExpressCheckoutDetails', token=token)
        
    def set_express_checkout(self, token='', **kwargs):
        """Shortcut for the SetExpressCheckout method.
            JV did not like the original method. found it limiting.
        """
        kwargs.update(locals())
        del kwargs['self']
        self._check_required(('amt',), **kwargs)
        return self._call('SetExpressCheckout', **kwargs)

    def do_express_checkout_payment(self, token, **kwargs):
        """Shortcut for the DoExpressCheckoutPayment method.
        
            Required
                *METHOD
                *TOKEN
                PAYMENTACTION
                PAYERID
                AMT
                
            Optional
                RETURNFMFDETAILS
                GIFTMESSAGE
                GIFTRECEIPTENABLE
                GIFTWRAPNAME
                GIFTWRAPAMOUNT
                BUYERMARKETINGEMAIL
                SURVEYQUESTION
                SURVEYCHOICESELECTED
                CURRENCYCODE
                ITEMAMT
                SHIPPINGAMT
                INSURANCEAMT
                HANDLINGAMT
                TAXAMT

            Optional + USEFUL
                INVNUM - invoice number
                
        """
        kwargs.update(locals())
        del kwargs['self']
        self._check_required(('paymentaction', 'payerid'), **kwargs)
        return self._call('DoExpressCheckoutPayment', **kwargs)
        
    def generate_express_checkout_redirect_url(self, token):
        """Submit token, get redirect url for client."""
        url_vars = (self.config.PAYPAL_URL_BASE, token)
        return "%s?cmd=_express-checkout&token=%s" % url_vars
