import json
import requests

class HttpClient:
    def __init__(self, headers=None, timeout=None):
        self.uri = "http://172.16.10.55/api/v1/"
        self.headers = headers or {}
        self.timeout = timeout or 600

    def handle_exception(self, e):
        message = str(e)
        print(message)

    def get(self, url, params=None, headers=None, stream=False):
        headers = headers or self.headers
        if 'http' not in url:
            url = self.uri + url
        try:
            response = requests.get(url, params=params, headers=headers, stream=stream, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.handle_exception(e)

    def post(self, url, data=None, headers=None, files=None):
        headers = headers or self.headers
        if 'http' not in url:
            url = self.uri + url
        try:
            response = requests.post(url, data=data, headers=headers, files=files, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.handle_exception(e)

    def json(self, url, json_data=None, headers=None):
        headers = headers or self.headers
        if 'http' not in url:
            url = self.uri + url
        try:
            data = json.dumps(json_data) if json_data is not None else None
            response = requests.post(url, data=data, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.handle_exception(e)

    def upload(self, url, file_path, headers=None, filename='file'):
        headers = headers or self.headers
        if 'http' not in url:
            url = self.uri + url
        try:
            with open(file_path, 'rb') as f:
                files = {filename: f}
                response = self.post(url, headers=headers, files=files)
                response.raise_for_status()
                return response.json()
        except requests.exceptions.RequestException as e:
            self.handle_exception(e)