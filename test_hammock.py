import unittest
import time
import json

from multiprocessing import Process
from wsgiref.simple_server import make_server

from hammock import Hammock

HOST = 'localhost'
PORT = 8000
BASE_URL = "http://%s:%s" % (HOST, PORT)
PATH = '/sample/path/to/resource'
URL = BASE_URL + PATH


def fixture_app(environ, start_response):
    content_length = int(environ.get('CONTENT_LENGTH', None) or '0')
    headers = dict([(k, v) for k, v in environ.items()
                   if k.find("HTTP_") == 0])
    body = None
    if content_length:
        body = environ.get('wsgi.input').read(content_length)
    response_obj = {
        'method': environ.get('REQUEST_METHOD'),
        'path': environ.get('PATH_INFO'),
        'body': body,
        'headers': headers,
        'querystring': environ.get('QUERY_STRING')
    }
    start_response('200 OK', [('Content-type', 'application/json')])
    return json.dumps(response_obj)


class TestCaseWrest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = make_server(HOST, PORT, fixture_app)
        cls.server_proc = Process(target=cls.server.serve_forever)
        cls.server_proc.start()
        time.sleep(1)  # Let server start in parallel execution

    @classmethod
    def tearDownClass(cls):
        cls.server_proc.terminate()

    def test_methods(self):
        client = Hammock(BASE_URL)
        for method in ['get', 'post', 'put', 'delete']:
            request = getattr(client, method.upper())
            resp = request('sample', 'path', 'to', 'resource')
            self.assertIsNotNone(resp.json)
            self.assertIsNotNone(resp.json.get('method', None))
            self.assertEqual(resp.json.get('method').lower(), method)

    def test_urls(self):
        client = Hammock(BASE_URL)
        combs = [
            client.sample.path.to.resource,
            client('sample').path('to').resource,
            client('sample', 'path', 'to', 'resource'),
            client('sample')('path')('to')('resource'),
            client.sample('path')('to', 'resource'),
            client('sample', 'path',).to.resource
        ]

        for comb in combs:
            self.assertEqual(str(comb), URL)
            resp = comb.GET()
            self.assertIsNotNone(resp.json)
            self.assertIsNotNone(resp.json.get('path', None))
            self.assertEqual(resp.json.get('path'), PATH)

    def test_urls_ignore(self):
        client = Hammock(BASE_URL, ignore=(False, None))
        combs = [
            client.sample(False).path.to(None).resource,
            client('sample', False).path('to', None).resource,
            client('sample', False, 'path', 'to', None, 'resource'),
            client('sample')(False)('path')('to')(None)('resource'),
            client.sample(False, 'path')('to', None, 'resource'),
            client('sample', False, 'path',).to(None).resource
        ]

        for comb in combs:
            self.assertEqual(str(comb), URL)
            resp = comb.GET()
            self.assertIsNotNone(resp.json)
            self.assertIsNotNone(resp.json.get('path', None))
            self.assertEqual(resp.json.get('path'), PATH)

    def test_append_slash_option(self):
        client = Hammock(BASE_URL, append_slash=True)
        resp = client.sample.path.to.resource.GET()
        self.assertIsNotNone(resp.json)
        self.assertIsNotNone(resp.json.get('path', None))
        self.assertEqual(resp.json.get('path'), PATH + "/")

    def test_body(self):
        client = Hammock(BASE_URL)
        body = "body fixture"
        resp = client.POST('sample', 'path', 'to', 'resource', data=body,
                           headers={'Content-Length': str(len(body))})
        self.assertIsNotNone(resp.json)
        self.assertIsNotNone(resp.json.get('body', None))
        self.assertEqual(resp.json.get('body'), body)

    def test_query(self):
        client = Hammock(BASE_URL)
        resp = client.POST('sample', 'path', 'to', 'resource',
                           params={'foo': 'bar'})
        self.assertIsNotNone(resp.json)
        self.assertIsNotNone(resp.json.get('querystring', None))
        self.assertEqual(resp.json.get('querystring'), 'foo=bar')

    def test_headers(self):
        client = Hammock(BASE_URL)
        resp = client.POST('sample', 'path', 'to', 'resource',
                           headers={'foo': 'bar'})
        self.assertIsNotNone(resp.json)
        headers = resp.json.get('headers', None)
        self.assertIsNotNone(headers)
        self.assertIsNotNone(headers.get('HTTP_FOO', None))
        self.assertEqual(headers.get('HTTP_FOO'), 'bar')

    def test_inheritance(self):
        """https://github.com/kadirpekel/hammock/pull/5/files#L1R99"""
        class CustomHammock(Hammock):
            def __init__(self, name=None, parent=None, **kwargs):
                if 'testing' in kwargs:
                    self.testing = kwargs.pop('testing')
                super(CustomHammock, self).__init__(name, parent, **kwargs)

            def _url(self, *args):
                assert isinstance(self.testing, bool)
                global called
                called = True
                return super(CustomHammock, self)._url(*args)

        global called
        called = False
        client = CustomHammock(BASE_URL, testing=True)
        resp = client.sample.path.to.GET()
        self.assertEqual(resp.json['path'], '/sample/path/to')
        self.assertTrue(called)

if __name__ == '__main__':
    unittest.main()
