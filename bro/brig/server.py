import os

import eve
from eve.io.mongo import Validator

class DisabledValidator(Validator):
    def validate(self, document, schema=None):
        return True

    def _validate(self, document, schema=None, update=False):
        return True

eve = eve.Eve(validator=DisabledValidator)

from werkzeug.wsgi import SharedDataMiddleware
eve.wsgi_app = SharedDataMiddleware(eve.wsgi_app, {
    '/ui': os.path.join(os.path.dirname(__file__), 'ui')
})

eve.run(host='127.0.0.1', debug=True, port=8100)
