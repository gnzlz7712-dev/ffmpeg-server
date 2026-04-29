from flask import Flask, request, jsonify
import subprocess
import base64
import os
import tempfile
import uuid

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/tts', methods=['POST'])
def text_to_speech():
    try:
        data = request.json
        text = data.get('text', '')
        voice = data.get('voice', 'ef_dora')  # Voz española por defecto

        if not text:
            return jsonify({"error": "Se requiere el campo 'text'"}), 400

        tmp_dir = tempfile.mkdtemp()
        uid = str(uuid.uuid4())[:8]
        audio_path = os.path.join(tmp_dir, f'audio_{uid}.wav')
        mp3_path = os.path.join(tmp_dir, f'audio_{uid}.mp3')

        # Generar audio con Kokoro
        cmd = [
            'python', '-c',
            f'''
import kokoro
import soundfile as sf
pipeline = kokoro.KPipeline(lang_code="e")
generator = pipeline("{text}", voice="{voice}", speed=1.0)
audio_chunks = []
for chunk in generator:
    audio_chunks.append(chunk.audio)
import numpy as np
audio = np.concatenate(audio_chunks)
sf.write("{audio_path}", audio, 24000)
'''
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # Convertir WAV a MP3 con FFmpeg
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', audio_path,
            '-codec:a', 'libmp3lame',
            '-qscale:a', '2',
            mp3_path
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

        with open(mp3_path, 'rb') as f:
            audio_b64 = base64.b64encode(f.read()).decode('utf-8')

        for path in [audio_path, mp3_path]:
            try:
                os.remove(path)
            except:
                pass
        try:
            os.rmdir(tmp_dir)
        except:
            pass

        return jsonify({
            "success": True,
            "audio_base64": audio_b64
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/merge', methods=['POST'])
def merge_videos():
    try:
        data = request.json

        video1_b64 = data.get('video1_base64', '')
        video2_b64 = data.get('video2_base64', '')
        audio_b64  = data.get('audio_base64', '')

        if not video1_b64 or not video2_b64:
            return jsonify({"error": "Se requieren video1_base64 y video2_base64"}), 400

        def clean_base64(b64_string):
            if ',' in b64_string:
                return b64_string.split(',')[1]
            return b64_string

        video1_b64 = clean_base64(video1_b64)
        video2_b64 = clean_base64(video2_b64)

        tmp_dir = tempfile.mkdtemp()
        uid = str(uuid.uuid4())[:8]

        video1_path  = os.path.join(tmp_dir, f'video1_{uid}.mp4')
        video2_path  = os.path.join(tmp_dir, f'video2_{uid}.mp4')
        audio_path   = os.path.join(tmp_dir, f'audio_{uid}.mp3')
        concat_path  = os.path.join(tmp_dir, f'concat_{uid}.txt')
        merged_path  = os.path.join(tmp_dir, f'merged_{uid}.mp4')
        output_path  = os.path.join(tmp_dir, f'output_{uid}.mp4')

        with open(video1_path, 'wb') as f:
            f.write(base64.b64decode(video1_b64))

        with open(video2_path, 'wb') as f:
            f.write(base64.b64decode(video2_b64))

        with open(concat_path, 'w') as f:
            f.write(f"file '{video1_path}'\n")
            f.write(f"file '{video2_path}'\n")

        concat_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_path,
            '-c', 'copy',
            merged_path
        ]
        subprocess.run(concat_cmd, check=True, capture_output=True)

        if audio_b64:
            audio_b64 = clean_base64(audio_b64)
            with open(audio_path, 'wb') as f:
                f.write(base64.b64decode(audio_b64))

            audio_cmd = [
                'ffmpeg', '-y',
                '-i', merged_path,
                '-i', audio_path,
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-shortest',
                output_path
            ]
            subprocess.run(audio_cmd, check=True, capture_output=True)
        else:
            output_path = merged_path

        with open(output_path, 'rb') as f:
            output_b64 = base64.b64encode(f.read()).decode('utf-8')

        for path in [video1_path, video2_path, audio_path, concat_path, merged_path, output_path]:
            try:
                os.remove(path)
            except:
                pass
        try:
            os.rmdir(tmp_dir)
        except:
            pass

        return jsonify({
            "success": True,
            "video_base64": f"data:video/mp4;base64,{output_b64}"
        })

    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": "FFmpeg falló",
            "details": e.stderr.decode('utf-8') if e.stderr else str(e)
        }), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
