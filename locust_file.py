"""
Como rodar:

1. Ative o ambiente virtual
2. `locust --headless --users 15 --spawn-rate 3 -H http://localhost`
"""
from locust import HttpUser, between, task


tokens: dict = {
    'user1': 'eyJ1c2VyIjogImFsbGFuIiwgImNvbXBhbnkiOiAidGVzdGUiLCAidXNlcl9pZCI6IDF9',
    'user2': 'eyJ1c2VyIjogImZ1bGFubyIsICJjb21wYW55IjogImNvY2EgY29sYSIsICJ1c2VyX2lkIjogMn0=',
    'user3': 'eyJ1c2VyIjogImNpY2xhbm8iLCAiY29tcGFueSI6ICJncm93dGgiLCAidXNlcl9pZCI6IDN9',
}

class LoadTest(HttpUser):
    wait_time = between(1, 5)

    @task
    def get_root(self):
        self.client.get('/user')

    @task
    def post_tiao(self):
        self.client.post(
            '/user',
            json={
                'username': 'Tião do gás',
                'email': 'dasdas@email.com',
                'senha': 'xeggaaaa',
            },
        )

    @task
    def get_spam(self):
        self.client.get('/user/1')

    @task
    def error(self):
        self.client.get('/error')
