from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse

import os
import requests
import base64
import html


app = FastAPI()


# ============================================================
# PANTALLA INICIAL
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home():

    return """
    <html>
    <head>

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Playlist Creator</title>

        <style>

            body {
                font-family: Arial, Helvetica, sans-serif;
                max-width: 700px;
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
                padding: 14px;
                font-size: 18px;
                cursor: pointer;
                margin-top: 10px;
            }

        </style>

    </head>

    <body>

        <h1>Playlist Creator</h1>

        <form action="/buscar_canciones/" method="post">

            <label>
                <strong>Nombre de la playlist</strong>
            </label>

            <br><br>

            <input
                type="text"
                name="nombre_playlist"
                required
            >

            <br><br>

            <label>
                <strong>Canciones (una por línea)</strong>
            </label>

            <br><br>

            <textarea
                name="canciones"
                required
                placeholder="Ejemplo:

Nada que perder
Chica de ayer
Billie Jean
Heroes - David Bowie"
            ></textarea>

            <br>

            <button type="submit">
                Buscar canciones
            </button>

        </form>

    </body>
    </html>
    """


# ============================================================
# OBTENER ACCESS TOKEN
# ============================================================

def obtener_access_token():

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")

    if not client_id or not client_secret or not refresh_token:
        return None, "Faltan las variables de entorno de Spotify."

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
        return None, r.text

    data = r.json()

    access_token = data.get("access_token")

    if not access_token:
        return None, "Spotify no devolvió un access token."

    return access_token, None


# ============================================================
# BUSCAR CANCIONES
# ============================================================

@app.post("/buscar_canciones/", response_class=HTMLResponse)
async def buscar_canciones(
    nombre_playlist: str = Form(...),
    canciones: str = Form(...)
):

    access_token, error = obtener_access_token()

    if error:
        return HTMLResponse(f"""
        <h2>Error obteniendo acceso a Spotify</h2>
        <pre>{html.escape(error)}</pre>
        <p><a href="/">Volver</a></p>
        """)

    lista_canciones = [
        linea.strip()
        for linea in canciones.splitlines()
        if linea.strip()
    ]

    if not lista_canciones:
        return HTMLResponse("""
        <h2>No se han introducido canciones</h2>
        <p><a href="/">Volver</a></p>
        """)

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    resultados = []

    for indice, cancion in enumerate(lista_canciones):

        search = requests.get(
            "https://api.spotify.com/v1/search",
            headers=headers,
            params={
                "q": cancion,
                "type": "track",
                "limit": 10
            }
        )

        if search.status_code != 200:

            resultados.append({
                "indice": indice,
                "entrada": cancion,
                "opciones": []
            })

            continue

        data = search.json()

        tracks = data.get(
            "tracks", {}
        ).get(
            "items", []
        )

        opciones = []

        for track in tracks:

            artistas = ", ".join(
                artist.get("name", "")
                for artist in track.get("artists", [])
            )

            opciones.append({
                "uri": track.get("uri", ""),
                "titulo": track.get("name", ""),
                "artista": artistas,
                "spotify_url": track.get(
                    "external_urls", {}
                ).get(
                    "spotify", "#"
                )
            })

        resultados.append({
            "indice": indice,
            "entrada": cancion,
            "opciones": opciones
        })

    # --------------------------------------------------------
    # Construir pantalla de selección
    # --------------------------------------------------------

    bloques = ""

    for resultado in resultados:

        indice = resultado["indice"]
        entrada = resultado["entrada"]
        opciones = resultado["opciones"]

        bloques += f"""
        <div class="cancion">

            <h3>
                {html.escape(entrada)}
            </h3>
        """

        if not opciones:

            bloques += """
                <p class="error">
                    No se encontraron resultados.
                </p>
            """

        else:

            for numero, opcion in enumerate(opciones):

                uri = html.escape(
                    opcion["uri"],
                    quote=True
                )

                titulo = html.escape(
                    opcion["titulo"]
                )

                artista = html.escape(
                    opcion["artista"]
                )

                spotify_url = html.escape(
                    opcion["spotify_url"],
                    quote=True
                )

                checked = ""

                # Si solo hay un resultado,
                # lo seleccionamos automáticamente.

                if len(opciones) == 1 and numero == 0:
                    checked = "checked"

                bloques += f"""

                <label class="opcion">

                    <input
                        type="radio"
                        name="cancion_{indice}"
                        value="{uri}"
                        {checked}
                    >

                    <span class="resultado">

                        <strong>
                            {titulo}
                        </strong>

                        — {artista}

                        <a
                            href="{spotify_url}"
                            target="_blank"
                            class="spotify"
                        >
                            Spotify
                        </a>

                    </span>

                </label>

                """

        bloques += """
        </div>
        """

    return HTMLResponse(f"""

    <html>

    <head>

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Seleccionar canciones</title>

        <style>

            body {{
                font-family: Arial, Helvetica, sans-serif;
                max-width: 700px;
                margin: auto;
                padding: 20px;
            }}

            h1 {{
                text-align: center;
            }}

            .cancion {{
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 25px;
            }}

            .opcion {{
                display: block;
                padding: 12px;
                margin: 8px 0;
                border: 1px solid #ddd;
                border-radius: 6px;
                cursor: pointer;
            }}

            .opcion:hover {{
                background: #f5f5f5;
            }}

            .opcion input {{
                width: auto;
                margin-right: 8px;
            }}

            .resultado {{
                line-height: 1.5;
            }}

            .spotify {{
                margin-left: 8px;
                font-size: 14px;
            }}

            button {{
                width: 100%;
                padding: 14px;
                font-size: 18px;
                cursor: pointer;
            }}

            .error {{
                color: #b00020;
            }}

        </style>

    </head>

    <body>

        <h1>Seleccionar canciones</h1>

        <p>
            Revisa las canciones antes de crear la playlist.
            Cuando haya varias versiones, selecciona la correcta.
        </p>

        <form
            action="/crear_playlist/"
            method="post"
        >

            <input
                type="hidden"
                name="nombre_playlist"
                value="{html.escape(nombre_playlist, quote=True)}"
            >

            {bloques}

            <button type="submit">
                Crear playlist con las canciones seleccionadas
            </button>

        </form>

        <br>

        <p>
            <a href="/">
                Empezar de nuevo
            </a>
        </p>

    </body>

    </html>

    """)


# ============================================================
# CREAR PLAYLIST Y AÑADIR CANCIONES
# ============================================================

@app.post("/crear_playlist/", response_class=HTMLResponse)
async def crear_playlist(
    request: Request,
    nombre_playlist: str = Form(...)
):

    access_token, error = obtener_access_token()

    if error:

        return HTMLResponse(f"""
        <h2>Error obteniendo acceso a Spotify</h2>
        <pre>{html.escape(error)}</pre>
        <p><a href="/">Volver</a></p>
        """)

    # --------------------------------------------------------
    # Recoger dinámicamente todas las canciones seleccionadas
    # --------------------------------------------------------

    form = await request.form()

    uris = []

    for clave, valor in form.multi_items():

        if clave.startswith("cancion_") and valor:

            uris.append(str(valor))

    # --------------------------------------------------------
    # Crear playlist
    # --------------------------------------------------------

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
        <h2>Error creando la playlist</h2>

        <p>
            <strong>Status Spotify:</strong>
            {playlist.status_code}
        </p>

        <pre>{html.escape(playlist.text)}</pre>

        <p>
            <a href="/">
                Volver
            </a>
        </p>
        """)

    playlist_data = playlist.json()

    playlist_id = playlist_data.get("id")

    spotify_url = (
        playlist_data
        .get("external_urls", {})
        .get("spotify", "#")
    )

    # --------------------------------------------------------
    # Añadir canciones
    # --------------------------------------------------------

    resultados_anadidos = []

    if uris:

        # Spotify permite un máximo de 100 elementos
        # por petición. Por eso dividimos automáticamente
        # playlists grandes en bloques de 100.

        for inicio in range(0, len(uris), 100):

            bloque = uris[inicio:inicio + 100]

            add_result = requests.post(
                f"https://api.spotify.com/v1/playlists/{playlist_id}/items",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "uris": bloque
                }
            )

            resultados_anadidos.append(add_result)

            if add_result.status_code != 201:

                return HTMLResponse(f"""
                <html>

                <body>

                    <h2>Playlist creada, pero hubo un error</h2>

                    <p>
                        La playlist se ha creado correctamente,
                        pero Spotify no pudo añadir todas las canciones.
                    </p>

                    <p>
                        <strong>Status Spotify:</strong>
                        {add_result.status_code}
                    </p>

                    <pre>
{html.escape(add_result.text)}
                    </pre>

                    <p>
                        <a
                            href="{html.escape(spotify_url)}"
                            target="_blank"
                        >
                            Abrir playlist en Spotify
                        </a>
                    </p>

                    <p>
                        <a href="/">
                            Crear otra playlist
                        </a>
                    </p>

                </body>

                </html>
                """)

    # --------------------------------------------------------
    # Resultado
    # --------------------------------------------------------

    if uris:

        mensaje = f"""
        <p>
            <strong>
                {len(uris)} canciones añadidas correctamente.
            </strong>
        </p>
        """

    else:

        mensaje = """
        <p>
            No se seleccionó ninguna canción.
        </p>
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
                max-width: 700px;
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

        <h3>Resultado</h3>

        {mensaje}

        <p>
            <a href="/">
                Crear otra playlist
            </a>
        </p>

    </body>

    </html>

    """)
