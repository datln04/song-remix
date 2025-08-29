import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from remix.pipeline import RemixPipeline, Config
from pathlib import Path
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB

UPLOAD_DIR = Path('uploads')
OUTPUT_DIR = Path('outputs')
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

@app.after_request
def add_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

@app.route('/')
def index():
    return '''
    <html><head><meta charset="utf-8"/><title>Covers Remix</title></head>
    <body style="font-family: sans-serif; padding: 1rem; max-width: 900px;">
      <h2>Auto Remix Covers</h2>
      <form id="f" method="post" action="/api/remix" enctype="multipart/form-data">
        <label>Song name</label><br/>
        <input type="text" name="song_name" placeholder="Never Enough" style="width: 100%;" required/><br/><br/>
        <label>Lyrics (paste or leave empty to fetch via Genius)</label><br/>
        <textarea name="lyrics" rows="10" style="width: 100%;"></textarea><br/>
        <label>Number of covers (used only if not uploading local videos)</label><br/>
        <input type="number" name="num_covers" value="3"/><br/><br/>
        <label>Upload local video files (optional, recommended in this environment)</label><br/>
        <input type="file" name="videos" multiple accept="video/*"/><br/><br/>
        <label>Model size</label> <input type="text" name="model_size" value="tiny"/><br/>
        <label>Resolution</label> <input type="text" name="resolution" value="1080p"/><br/>
        <label><input type="checkbox" name="subtitles" checked/> Add subtitles</label><br/><br/>
        <button type="submit">Remix</button>
      </form>
      <div id="result" style="margin-top: 1rem;"></div>
      <script>
      const form = document.getElementById('f');
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        const res = await fetch('/api/remix', { method: 'POST', body: fd });
        const data = await res.json();
        const d = document.getElementById('result');
        if (data.error) {
          d.innerHTML = '<pre style="color:red">'+data.error+'</pre>';
        } else {
          d.innerHTML = '<p>Done. <a href="/outputs/'+data.filename+'" target="_blank">Download '+data.filename+'</a></p>';
          const video = document.createElement('video');
          video.controls = true; video.width = 720;
          video.src = '/outputs/'+data.filename;
          d.appendChild(video);
        }
      });
      </script>
    </body></html>
    '''

@app.route('/outputs/<path:fn>')
def serve_output(fn):
    return send_from_directory(OUTPUT_DIR, fn, as_attachment=False)

@app.route('/api/remix', methods=['POST'])
def remix_api():
    try:
        song_name = request.form.get('song_name', '').strip()
        if not song_name:
            return jsonify({'error': 'song_name is required'}), 400
        lyrics = request.form.get('lyrics', None)
        try:
            num_covers = int(request.form.get('num_covers', '3'))
        except Exception:
            num_covers = 3
        model_size = request.form.get('model_size', 'tiny')
        resolution = request.form.get('resolution', '1080p')
        add_subtitles = request.form.get('subtitles', 'on') == 'on'

        local_paths = []
        if 'videos' in request.files:
            files = request.files.getlist('videos')
            for f in files:
                if f and f.filename:
                    fn = secure_filename(f.filename)
                    savep = UPLOAD_DIR / fn
                    f.save(savep)
                    local_paths.append(str(savep))

        out_name = f"remix_{secure_filename(song_name)}.mp4"
        out_path = str(OUTPUT_DIR / out_name)

        cfg = Config(song_name=song_name, lyrics=lyrics, num_covers=num_covers,
                     model_size=model_size, out_path=out_path, add_subtitles=add_subtitles,
                     local_videos=local_paths if local_paths else None)
        pipe = RemixPipeline(cfg)
        result = pipe.run()
        return jsonify({'ok': True, 'filename': os.path.basename(result)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '12000'))
    app.run(host='0.0.0.0', port=port, debug=False)
