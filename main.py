from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

import os
import requests
import base64
import html


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

        <form action="/crear_playlist/" method="post">

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

    # ---------------------------------------------------------
    # 1. Obtener credenciales
    # ---------------------------------------------------------

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")

    if not client_id or not client_secret or not refresh_token:
        return HTMLResponse("""
        <html>
        <body>
            <h2>Error de configuración</h2>

            <p>
                Faltan una o más variables de entorno de Spotify:
            </p>

            <ul>
                <li>SPOTIFY_CLIENT_ID</li>
                <li>SPOTIFY_CLIENT_SECRET</li>
                <li>SPOTIFY_REFRESH_TOKEN</li>
            </ul>

            <p>
                <a href="/">Volver</a>
            </p>
        </body>
        </html>
        """)

    # ---------------------------------------------------------
    # 2. Obtener access token usando el refresh token
    # ---------------------------------------------------------

    auth = base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode()

    r = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
    )

    if r.status_code != 200:
        return HTMLResponse(f"""
        <html>
        <body>
            <h2>Error obteniendo el access token</h2>

            <p>
                <strong>Status:</strong> {r.status_code}
            </p>

            <pre>{html.escape(r.text)}</pre>

            <p>
                <a href="/">Volver</a>
            </p>
        </body>
        </html>
        """)

    token_data = r.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return HTMLResponse("""
        <html>
        <body>
            <h2>Error</h2>

            <p>
                Spotify no ha devuelto un access token.
            </p>

            <p>
                <a href="/">Volver</a>
            </p>
        </body>
        </html>
        """)

    # ---------------------------------------------------------
    # 3. Preparar las canciones
    # ---------------------------------------------------------

    lista_canciones = [
        linea.strip()
        for linea in canciones.splitlines()
        if linea.strip()
    ]

    if not lista_canciones:
        return HTMLResponse("""
        <html>
        <body>
            <h2>No se han introducido canciones</h2>

            <p>
                <a href="/">Volver</a>
            </p>
        </body>
        </html>
        """)

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # ---------------------------------------------------------
    # 4. Buscar cada canción en Spotify
    # ---------------------------------------------------------

    uris = []
    encontradas = []
    no_encontradas = []

    for cancion in lista_canciones:

        search = requests.get(
            "https://api.spotify.com/v1/search",
            headers=headers,
            params={
                "q": cancion,
                "type": "track",
                "limit": 1
            }
        )

        if search.status_code != 200:
            no_encontradas.append(
                f"{cancion} (error Spotify {search.status_code})"
            )
            continue

        search_data = search.json()

        tracks = search_data.get("tracks", {}).get("items", [])

        if not tracks:
            no_encontradas.append(cancion)
            continue

        track = tracks[0]

        uri = track.get("uri")

        if not uri:
            no_encontradas.append(cancion)
            continue

        uris.append(uri)

        artista = ", ".join(
            artist.get("name", "")
            for artist in track.get("artists", [])
        )

        titulo = track.get("name", "")

        encontradas.append(
            f"{titulo} — {artista}"
        )

    # ---------------------------------------------------------
    # 5. Crear la playlist
    # ---------------------------------------------------------

    playlist = requests.post(
        "https://api.spotify.com/v1/me/playlists",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={
            "name": nombre_playlist,
            "public": False
        }
    )

    if playlist.status_code != 201:

        return HTMLResponse(f"""
        <html>
        <body>

            <h2>Error creando la playlist</h2>

            <p>
                <strong>Status Spotify:</strong>
                {playlist.status_code}
            </p>

            <pre>{html.escape(playlist.text)}</pre>

            <p>
                <a href="/">Volver</a>
            </p>

        </body>
        </html>
        """)

    playlist_data = playlist.json()

    playlist_id = playlist_data.get("id")

    spotify_url = (
        playlist_data
        .get("external_urls", {})
        .get("spotify", "#")
    )

    # ---------------------------------------------------------
    # 6. Añadir las canciones encontradas
    # ---------------------------------------------------------

    add_result = None

    if uris:

        add_result = requests.post(
            f"https://api.spotify.com/v1/playlists/{playlist_id}/items",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "uris": uris
            }
        )

    # ---------------------------------------------------------
    # 7. Preparar resultado
    # ---------------------------------------------------------

    encontradas_html = ""

    if encontradas:
        encontradas_html = "<ul>"

        for cancion in encontradas:
            encontradas_html += (
                f"<li>{html.escape(cancion)}</li>"
            )

        encontradas_html += "</ul>"
    else:
        encontradas_html = "<p>Ninguna canción encontrada.</p>"

    no_encontradas_html = ""

    if no_encontradas:
        no_encontradas_html = "<ul>"

        for cancion in no_encontradas:
            no_encontradas_html += (
                f"<li>{html.escape(cancion)}</li>"
            )

        no_encontradas_html += "</ul>"
    else:
        no_encontradas_html = "<p>Ninguna.</p>"

    # ---------------------------------------------------------
    # 8. Mostrar resultado
    # ---------------------------------------------------------

    if add_result is None:

        estado_anadir = """
        <p>
            No había canciones encontradas para añadir.
        </p>
        """

    elif add_result.status_code == 201:

        estado_anadir = f"""
        <p>
            <strong>
                {len(uris)} canciones añadidas correctamente.
            </strong>
        </p>
        """

    else:

        estado_anadir = f"""
        <p>
            <strong>
                Error añadiendo las canciones.
            </strong>
        </p>

        <p>
            <strong>Status Spotify:</strong>
            {add_result.status_code}
        </p>

        <pre>{html.escape(add_result.text)}</pre>
        """

    return HTMLResponse(f"""
    <html>

    <head>
        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Playlist creada</title>

        <style>

            body {{
                font-family: Arial, Helvetica, sans-serif;
                max-width: 600px;
                margin: auto;
                padding: 20px;
            }}

            h1, h2 {{
                text-align: center;
            }}

            .boton {{
                display: block;
                text-align: center;
                background: #1DB954;
                color: white;
                padding: 14px;
                text-decoration: none;
                border-radius: 6px;
                margin: 25px 0;
                font-size: 18px;
            }}

            .resultado {{
                margin-top: 25px;
            }}

        </style>

    </head>

    <body>

        <h2>Playlist creada</h2>

        <p>
            <strong>Nombre:</strong>
            {html.escape(nombre_playlist)}
        </p>

        <a
            class="boton"
            href="{html.escape(spotify_url)}"
            target="_blank"
        >
            Abrir playlist en Spotify
        </a>

        <div class="resultado">

            <h3>Canciones encontradas</h3>

            <p>
                {len(encontradas)} de {len(lista_canciones)}
            </p>

            {encontradas_html}

            <h3>Canciones no encontradas</h3>

            {no_encontradas_html}

            <h3>Añadir a la playlist</h3>

            {estado_anadir}

        </div>

        <p>
            <a href="/">
                Crear otra playlist
            </a>
        </p>

    </body>

    </html>
    """)
