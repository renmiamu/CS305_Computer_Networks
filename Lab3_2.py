# flask http server Demo2
from flask import Flask
from flask import request
from flask import render_template
from flask import make_response

app = Flask(__name__)


@app.route("/", methods=['GET', 'POST'])
def main():
    if request.method == 'GET':
        return render_template('main.html')

    if request.method == 'POST':
        user = request.form.get('user')
        password = request.form.get('password')

        resp = make_response(render_template('welcome.html'))
        resp.set_cookie('username', user)
        return resp


if __name__ == "__main__":
    app.run(host='0.0.0.0', port = 9000, debug = True)