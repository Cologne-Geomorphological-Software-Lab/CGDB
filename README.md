The Cologne Geomorphological Database System (CGDB)  is a comprehensive information system for managing complex geoscientific research data. It is specifically designed to support small research projects that must adhere to strict data management requirements set by funding bodies but often lack the financial and human resources to do so. The framework supports the transformation of raw research data into scientific knowledge. It addresses critical challenges, such as the rapid increase in the volume, variety, and complexity of geoscientific datasets, data heterogeneity, spatial complexity, and the need to comply with the FAIR (Findable, Accessible, Interoperable, and Reusable) principles. The approach optimises the research management process by enhancing scalability and enabling interdisciplinary integration. It is adaptable to evolving research requirements and supports various data types and methodological approaches, such as machine learning and deep learning, that place high demands on the data and their formats. 

![admin_samples](admin_samples.png)

## Installation for local development
To set up the framework for local development, navigate to the desired folder and clone the repository.

```
git clone git@github.com:Cologne-Geomorphological-Software-Lab/CGDB.git
```

```
cd CGDB
```

Set up a virtual environment, activate it and install the project's dependencies:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a copy of prototype *local_settings_TEMPLATE.py* as *local_settings.py*:

```
cp prototype/local_settings_TEMPLATE.py prototype/local_settings.py
```

For local development, edit local_settings.py with a text editor or an IDE according to the official Django documentation, especially the section on Geodjango: https://docs.djangoproject.com/en/5.2/ref/contrib/gis/install/ It is advisable to use SpatialLite initially for development. Also set the locations for STATIC_URL and MEDIA_URL. Set DEBUG = True:

```
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": "db.sqlite3",
    }
}
```

Install the geospatial libraries and SpatialLite:

```
sudo apt-get install binutils libproj-dev gdal-bin libsqlite3-mod-spatialite
```

Implement get_secret_key(). Only for local development you can allocate a static key to SECRET_KEY:

```
def get_secret_key():
    return "YOUR SECRET KEY"

```

Migrate the database and create a super user:
```
python manage.py migrate
python manage.py createsuperuser
```

Start the local development server:
```
python manage.py runserver
```


![admin_luminescence](admin_luminescence.png)
