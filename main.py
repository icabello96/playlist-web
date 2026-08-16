from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

import os
import requests
import base64
import html
import json


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

            album = track.get(
                "album", {}
            ).get(
                "name", ""
            )

            fecha = track.get(
                "album", {}
            ).get(
                "release_date", ""
            )

            imagenes = track.get(
                "album", {}
            ).get(
                "images", []
            )

            imagen = ""

            if imagenes:
                imagen = imagenes[-1].get(
                    "url", ""
                )

            opciones.append({
                "uri": track.get("uri", ""),
                "titulo": track.get("name", ""),
                "artista": artistas,
                "album": album,
                "fecha": fecha,
                "imagen": imagen,
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

    resultados_json = json.dumps(
        resultados,
        ensure_ascii=False
    )

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

                album = html.escape(
                    opcion["album"]
                )

                fecha = html.escape(
                    opcion["fecha"]
                )

                imagen = opcion["imagen"]

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

                    <div class="info">

                """

                if imagen:

                    bloques += f"""
                        <img
                            src="{html.escape(imagen, quote=True)}"
                            class="portada"
                        >
                    """

                bloques += f"""

                        <div>

                            <strong>
                                {titulo}
                            </strong>

                            <br>

                            <span>
                                {artista}
                            </span>

                            <br>

                            <small>
                                {album}
                                """

                if fecha:
                    bloques += f" · {fecha}"

                bloques += f"""
                            </small>

                            <br>

                            <a
                                href="{spotify_url}"
                                target="_blank"
                            >
                                Abrir en Spotify
                            </a>

                        </div>

                    </div>

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
                padding: 10px;
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
                margin-right: 10px;
            }}

            .info {{
                display: flex;
                align-items: center;
                gap: 12px;
                margin-top: 8px;
            }}

            .portada {{
                width: 60px;
                height: 60px;
                object-fit: cover;
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

            .aviso {{
                background: #fff4cc;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 20px;
            }}

        </style>

    </head>

    <body>

        <h1>Seleccionar canciones</h1>

        <div class="aviso">

            <strong>
                Revisa las canciones antes de crear la playlist.
            </strong>

            <br><br>

            Cuando haya varias versiones de una canción,
            selecciona la correcta.

        </div>

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
    nombre_playlist: str = Form(...),
    cancion_0: str | None = Form(None),
    cancion_1: str | None = Form(None),
    cancion_2: str | None = Form(None),
    cancion_3: str | None = Form(None),
    cancion_4: str | None = Form(None),
    cancion_5: str | None = Form(None),
    cancion_6: str | None = Form(None),
    cancion_7: str | None = Form(None),
    cancion_8: str | None = Form(None),
    cancion_9: str | None = Form(None),
    cancion_10: str | None = Form(None),
    cancion_11: str | None = Form(None),
    cancion_12: str | None = Form(None),
    cancion_13: str | None = Form(None),
    cancion_14: str | None = Form(None),
    cancion_15: str | None = Form(None),
    cancion_16: str | None = Form(None),
    cancion_17: str | None = Form(None),
    cancion_18: str | None = Form(None),
    cancion_19: str | None = Form(None)
):

    access_token, error = obtener_access_token()

    if error:

        return HTMLResponse(f"""
        <h2>Error obteniendo acceso a Spotify</h2>
        <pre>{html.escape(error)}</pre>
        <p><a href="/">Volver</a></p>
        """)

    # --------------------------------------------------------
    # Recoger canciones seleccionadas
    # --------------------------------------------------------

    uris = []

    posibles_canciones = [
        cancion_0,
        cancion_1,
        cancion_2,
        cancion_3,
        cancion_4,
        cancion_5,
        cancion_6,
        cancion_7,
        cancion_8,
        cancion_9,
        cancion_10,
        cancion_11,
        cancion_12,
        cancion_13,
        cancion_14,
        cancion_15,
        cancion_16,
        cancion_17,
        cancion_18,
        cancion_19
    ]

    for uri in posibles_canciones:

        if uri:
            uris.append(uri)

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

    # --------------------------------------------------------
    # Resultado
    # --------------------------------------------------------

    if add_result is not None and add_result.status_code == 201:

        mensaje = f"""
        <p>
            <strong>
                {len(uris)} canciones añadidas correctamente.
            </strong>
        </p>
        """

    elif not uris:

        mensaje = """
        <p>
            No se seleccionó ninguna canción.
        </p>
        """

    else:

        mensaje = f"""
        <p>
            <strong>
                Error añadiendo las canciones.
            </strong>
        </p>

        <p>
            <strong>
                Status Spotify:
            </strong>

            {add_result.status_code}
        </p>

        <pre>
{html.escape(add_result.text)}
        </pre>
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
