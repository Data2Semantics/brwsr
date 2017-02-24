echo "Updating from git"
git pull
echo "Killing existing gunicorn process"
pkill -F /tmp/gunicorn-brwsr.pid
echo "Activating the virtual environment"
source bin/activate
echo "Changing directory to src"
cd src
echo "Starting the gunicorn process"
gunicorn -c gunicorn_config.py app:app
