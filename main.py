from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <title>Playlist Creator</title>

        <style>
            body {
                font-family: Arial, Helvetica, sans-serif;
                max-width: 600px;
                margin: auto;
                padding: 20px;
            }

            h1 {
                text-align: center;
            }

            input, textarea {
                width: 100%;
                box-sizing: border-box;
                padding: 10px;
                font-size: 16px;
            }

            textarea {
                height: 300px;
            }

            button {
                width: 100%;
                padding: 12px;
                font-size: 18px;
                cursor: pointer;
            }
        </style>
    </head>

    <body>

        <h1>Playlist Creator</h1>

        /crear_playlist/

            <label>Nombre de la playlist</label><br>
            <input
                type="text"
                name="nombre_playlist"
                required
            ><br><br>

            <label>Canciones (una por línea)</label><br>

            <textarea
                name="canciones"
                required
            ></textarea><br><br>

            <button type="submit">
                Crear playlist Spotify
            </button>

        </form>

    </body>
    </html>
    """


@app.post("/crear_playlist/")
async def crear_playlist(
    nombre_playlist: str = Form(...),
    canciones: str = Form(...)
):

    lista = [
        x.strip()
        for x in canciones.splitlines()
        if x.strip()
    ]

    return HTMLResponse(f"""
    <html>
    <body>

    <h2>Prueba OK</h2>

    <p><strong>Playlist:</strong> {nombre_playlist}</p>

    <p><strong>Canciones:</strong> {len(lista)}</p>

    <pre>
{chr(10).join(lista)}
    </pre>

    </body>
    </html>
    """)