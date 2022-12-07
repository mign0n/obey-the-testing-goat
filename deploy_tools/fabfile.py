import getpass
import os
import secrets
import string
from fabric import Connection, Config
from fabric.tasks import task

REPO_TOKEN = os.environ['REPO_TOKEN']
REPO_URL = f'https://{REPO_TOKEN}@github.com/mign0n/obey-the-testing-goat.git'


@task
def deploy(context):
    connection = Connection(
        host=context.host,
        user=context.user,
        port=context.port,
    )
    current_commit = connection.local(
        'git log -n 1 --format=%H').stdout.strip()
    site_folder = f'/home/{connection.user}/sites/{connection.host}'
    connection.run(f'mkdir -p {site_folder}')
    with connection.cd(site_folder):
        _get_latest_source(connection, current_commit)
        _update_virtualenv(connection)
        _create_or_update_dotenv(connection)
        _update_static_files(connection)
        _update_database(connection, site_folder)
        _config_web_server(context, site_folder)


def _get_latest_source(connection, commit):
    if connection.run('test -d .git', warn=True).failed:
        connection.run(f'git clone {REPO_URL} .')
    else:
        connection.run(f'git remote set-url origin {REPO_URL}')
        connection.run('git fetch')
    connection.run(f'git reset --hard {commit}')


def _update_virtualenv(connection):
    if connection.run('test -d virtualenv/bin/pip', warn=True).failed:
        connection.run('python3 -m venv env')
        connection.run('./env/bin/python -m pip install -U pip')
    connection.run('./env/bin/pip install -r requirements.txt')


def _create_or_update_dotenv(connection):
    connection.run('echo "DJANGO_DEBUG_FALSE=y" >> .env')
    connection.run(f'echo "SITENAME={connection.host}" >> .env')
    current_contents = connection.run('cat .env').stdout.strip()
    if 'DJANGO_SECRET_KEY' not in current_contents:
        alphabet = string.ascii_letters + string.digits
        secret_key = ''.join(secrets.choice(alphabet) for i in range(60))
        connection.run(f'echo "DJANGO_SECRET_KEY={secret_key}" > .env')


def _update_static_files(connection):
    connection.run(
        './env/bin/python superlists/manage.py collectstatic --noinput')


def _update_database(connection, site_folder):
    connection.run(f'mkdir -p {site_folder}/database')
    connection.run('./env/bin/python superlists/manage.py migrate --noinput')


def _config_web_server(context, site_folder):
    sudo_pass = getpass.getpass('Enter sudo password on server: ')
    config = Config(overrides={'doas': {'password': sudo_pass}})
    with Connection(
            host=context.host,
            user=context.user,
            port=context.port,
            config=config
    ) as connection:
        deploy_dir = f'{site_folder}/deploy_tools'
        sudo_prefix = 'doas -u root sh -c'
        connection.run(
            (f'cat {deploy_dir}/nginx.conf.template | sed -e '
             f'"s/DOMAIN/{connection.host}/g" -e '
             f'"s/USER/{connection.user}/g" | tee '
             f'{deploy_dir}/nginx.conf')
        )
        connection.run(
            (f'cat {deploy_dir}/gunicorn-openrc.conf.template | '
             f'sed -e "s/DOMAIN/{connection.host}/g" -e '
             f'"s/USER/{connection.user}/g" -e "s/APP/superlists/g" '
             f'| tee {deploy_dir}/gunicorn-openrc.conf')
        )
        cmd_mv_nginx_conf = (
            (f'{sudo_prefix} "mv -f {deploy_dir}/nginx.conf '
             f'/etc/nginx/http.d/{connection.host}.conf"')
        )
        cmd_mv_gunicorn_conf = (
            (f'{sudo_prefix} "mv -f {deploy_dir}/gunicorn-openrc.conf'
             f' /etc/conf.d/{connection.host}"')
        )
        cmd_cp_init_script = (
            (f'{sudo_prefix} "cp -f {deploy_dir}/gunicorn-openrc.init.template'
             f' /etc/init.d/{connection.host}"')
        )
        cmd_chmod_script = (
            f'{sudo_prefix} "chmod +x /etc/init.d/{connection.host}"'
        )
        cmd_add_service = (
            f'{sudo_prefix} "rc-update add {connection.host} default"'
        )
        cmd_start_service = (
            f'{sudo_prefix} "rc-service {connection.host} start"'
        )
        connection.run(cmd_mv_nginx_conf, pty=True)
        connection.run(cmd_mv_gunicorn_conf, pty=True)
        connection.run(cmd_cp_init_script, pty=True)
        connection.run(cmd_chmod_script, pty=True)
        connection.run(cmd_add_service, pty=True)
        connection.run(cmd_start_service, pty=True)

