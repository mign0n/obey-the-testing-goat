Provisioning a new site
=======================

## Required packages:

* nginx
* Python 3.10
* virtualenv + pip
* Git

e.g., on Alpine Linux:

```
	doas apk upgrade
	doas apk add git nginx python3
  doas rc-update add nginx default
  doas rc-service nginx start
```

## Nginx Virtual Host config

* create file `/etc/nginx/http.d/DOMAIN.conf`
* it's file contents see in `nginx.conf.template`
* replace `DOMAIN` with, e.g., *staging.my-domain.com*
* replace `USER` with your server username 

## OpenRC service

* create openrc-script `/etc/init.d/DOMAIN`
* it's file contents see in `gunicorn-openrc.init.template`
* create config file `/etc/conf.d/DOMAIN` for openrc-script
* it's file contents see in `gunicorn-openrc.conf.template`
* replace `DOMAIN` with, e.g., *staging.my-domain.com*
* replace `USER` with your server username 
* replace `APP` with application name
* start service:

```
	doas chmod +x /etc/init.d/DOMAIN
	doas rc-update add DOMAIN default
	doas rc-service DOMAIN start
```

## Folder structure

    /home/USER
    └── sites
        └── DOMAIN1
            ├── README.md
            ├── database
            ├── env
            ├── poetry.lock
            ├── pyproject.toml
            ├── requirements.txt
            ├── static
            ├── APP
            └── tests
