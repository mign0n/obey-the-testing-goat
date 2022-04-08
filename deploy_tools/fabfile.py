import os
import secrets
import string
from fabric import Connection
from fabric.tasks import task

REPO_TOKEN = os.environ['REPO_TOKEN']
REPO_URL = f'https://{REPO_TOKEN}@github.com/mign0n/obey-the-testing-goat.git'
HOST = 'obey@superlists-staging.local.vm:2233'

@task
def deploy(context):
    connection = Connection(HOST) 
    current_commit = connection.local('git log -n 1 --format=%H').stdout.strip()
    site_folder = f'/home/{connection.user}/sites/{connection.host}'
    connection.run(f'mkdir -p {site_folder}')
    with connection.cd(site_folder):
        _get_latest_source(connection, current_commit)
        _update_virtualenv(connection)
        _create_or_update_dotenv(connection)
        _update_static_files(connection)
        _update_database(connection)


def _get_latest_source(connection, commit):
    if connection.run('test -d .git', warn=True).failed:
        connection.run(f'git clone {REPO_URL} .')
    else:
        connection.run(f'git remote set-url origin {REPO_URL}')
        connection.run('git fetch')
    connection.run(f'git reset --hard {commit}')


def _update_virtualenv(connection):
    if connection.run('test -d virtualenv/bin/pip', warn=True).failed:
        connection.run(f'python3 -m venv env')
    connection.run('./env/bin/pip install -r requirements.txt')


def _create_or_update_dotenv(connection):
    current_contents = connection.run('cat .env').stdout.strip()
    if 'DJANGO_SECRET_KEY' not in current_contents:
        alphabet = string.ascii_letters + string.digits
        secret_key = ''.join(secrets.choice(alphabet) for i in range(60))
        connection.run(f'echo "DJANGO_SECRET_KEY={secret_key}" > .env')
    connection.run('echo "DJANGO_DEBUG_FALSE=y" >> .env')
    connection.run(f'echo "SITENAME={connection.host}" >> .env')


def _update_static_files(connection):
    connection.run('./env/bin/python superlists/manage.py collectstatic --noinput')


def _update_database(connection):
    connection.run('./env/bin/python superlists/manage.py migrate --noinput')

