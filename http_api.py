import http_client


class HttpApi:
    def __init__(self):
        self.http_c = http_client.HttpClient()
        self.serverUri = 'http://172.16.10.55/api/v1/'

    def backDesign(self, id, info, path):
        self.http_c.post(self.serverUri + 'panel/back-design', {'id': id, 'info': info, 'path': path})
