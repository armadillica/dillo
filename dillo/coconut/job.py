import requests
from requests.auth import HTTPBasicAuth

from dillo.coconut import config

USER_AGENT = 'Coconut/2.2.0 (Python)'


def submit(config_content, **kwargs):
    headers = {'User-Agent': USER_AGENT, 'Content-Type': 'text/plain', 'Accept': 'application/json'}
    response = requests.post(
        'https://api.coconut.co/v1/job',
        data=config_content,
        headers=headers,
        auth=HTTPBasicAuth(kwargs['api_key'], ''),
    )

    return response.json()


def create(**kwargs):
    return submit(config.new(**kwargs), **kwargs)
