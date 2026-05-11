import os
from flask import Flask, render_template

app = Flask(__name__)

STREAM_URL = os.environ.get('STREAM_URL', '')

@app.route('/')
def index():
    return render_template('index.html', stream_url=STREAM_URL)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
