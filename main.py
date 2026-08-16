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
                "artista": artistas
            })

        resultados.append({
            "indice": indice,
            "entrada": cancion,
            "opciones": opciones
        })


    # ========================================================
    # CONSTRUIR CARRUSELES
    # ========================================================

    bloques = ""

    # Solo se mostrará "Desliza →" una vez
    primer_desliza = True

    for resultado in resultados:

        indice = resultado["indice"]
        opciones = resultado["opciones"]

        bloques += """
        <section class="cancion">
        """

        if not opciones:

            bloques += """
                <p class="error">
                    No se encontraron resultados.
                </p>
            """

        else:

            bloques += """
                <div class="carrusel">
            """

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

                # Primera opción seleccionada por defecto
                checked = ""

                if numero == 0:
                    checked = "checked"

                bloques += f"""

                    <label class="opcion">

                        <input
                            type="radio"
                            name="cancion_{indice}"
                            value="{uri}"
                            {checked}
                        >

                        <span class="texto-opcion">

                            <strong>
                                {titulo}
                            </strong>

                            <span class="artista">
                                {artista}
                            </span>

                        </span>

                    </label>

                """

            bloques += """
                </div>
            """

            # ------------------------------------------------
            # "Desliza →" solo aparece una vez
            # ------------------------------------------------

            if len(opciones) > 3 and primer_desliza:

                bloques += """
                    <div class="desliza">
                        Desliza →
                    </div>
                """

                primer_desliza = False

        bloques += """
        </section>
        """


    # ========================================================
    # PANTALLA DE SELECCIÓN
    # ========================================================

    return HTMLResponse(f"""

    <html>

    <head>

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Seleccionar canciones</title>

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: Arial, Helvetica, sans-serif;
                max-width: 700px;
                margin: auto;
                padding: 20px;
                color: #222;
            }}

            h1 {{
                text-align: center;
                margin-bottom: 8px;
            }}

            .intro {{
                text-align: center;
                color: #666;
                margin-bottom: 20px;
            }}

            /* =================================================
               CADA CARRUSEL
               ================================================= */

            .cancion {{
                margin-bottom: 12px;
            }}

            .carrusel {{
                display: flex;
                gap: 8px;

                overflow-x: auto;

                scroll-snap-type: x mandatory;

                padding: 2px 2px 8px 2px;

                scrollbar-width: thin;
            }}

            /* =================================================
               TARJETAS
               ================================================= */

            .opcion {{
                flex: 0 0 calc((100% - 16px) / 3);

                min-height: 72px;

                border: 1px solid #ddd;
                border-radius: 7px;

                padding: 9px;

                cursor: pointer;

                scroll-snap-align: start;

                background: white;

                display: flex;
                align-items: flex-start;

                gap: 7px;

                transition:
                    background 0.15s ease,
                    border 0.15s ease;
            }}

            .opcion:hover {{
                background: #f7f7f7;
            }}

            /* =================================================
               OPCIÓN SELECCIONADA
               ================================================= */

            .opcion:has(input:checked) {{
                border: 2px solid #999;
                background: #f2f2f2;
            }}

            .opcion input {{
                margin-top: 2px;
                flex-shrink: 0;
            }}

            /* =================================================
               TEXTO
               ================================================= */

            .texto-opcion {{
                display: flex;
                flex-direction: column;
                gap: 3px;

                overflow: hidden;
            }}

            .texto-opcion strong {{
                line-height: 1.2;
                font-size: 14px;
            }}

            .artista {{
                color: #666;
                font-size: 13px;
                line-height: 1.2;
            }}

            /* =================================================
               INDICADOR DEL CARRUSEL
               ================================================= */

            .desliza {{
                text-align: right;

                color: #999;

                font-size: 12px;

                margin-top: 1px;

                padding-right: 4px;
            }}

            /* =================================================
               ERRORES
               ================================================= */

            .error {{
                color: #b00020;

                padding: 10px;

                border: 1px solid #f0c0c0;

                border-radius: 6px;
            }}

            /* =================================================
               BOTÓN
               ================================================= */

            button {{
                width: 100%;

                padding: 15px;

                font-size: 18px;

                cursor: pointer;

                border: none;

                border-radius: 7px;

                background: #222;

                color: white;

                margin-top: 10px;
            }}

            button:hover {{
                opacity: 0.9;
            }}

            /* =================================================
               MÓVIL
               ================================================= */

            @media (max-width: 500px) {{

                body {{
                    padding: 15px;
                }}

                .opcion {{
                    flex: 0 0 calc((100% - 8px) / 2);

                    min-height: 68px;

                    padding: 8px;
                }}

                .texto-opcion strong {{
                    font-size: 13px;
                }}

                .artista {{
                    font-size: 12px;
                }}

            }}

        </style>

    </head>

    <body>

        <h1>Seleccionar canciones</h1>

        <p class="intro">
            Revisa las coincidencias y selecciona la versión correcta.
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
                Crear playlist
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

    # ========================================================
    # RECOGER TODAS LAS CANCIONES SELECCIONADAS
    # ========================================================

    form = await request.form()

    uris = []

    for clave, valor in form.multi_items():

        if clave.startswith("cancion_") and valor:

            uris.append(str(valor))


    # ========================================================
    # CREAR PLAYLIST
    # ========================================================

    playlist = requests.post(
        "https://api.spotify.com/v1/me/playlists",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={
            "name": nombre_playlist,
            "description": (
                "Los Perrostratos, grupo de música para bodas "
                "y eventos en Madrid. Música en directo para "
                "bodas, fiestas y eventos."
            ),
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


    # ========================================================
    # AÑADIR CANCIONES EN BLOQUES DE 100
    # ========================================================

    if uris:

        for inicio in range(0, len(uris), 100):

            bloque = uris[inicio:inicio + 100]

            add_result = requests.post(
                f"https://api.spotify.com/v1/playlists/"
                f"{playlist_id}/items",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "uris": bloque
                }
            )

            if add_result.status_code != 201:

                return HTMLResponse(f"""
                <html>

                <body>

                    <h2>
                        Playlist creada, pero hubo un error
                    </h2>

                    <p>
                        La playlist se ha creado correctamente,
                        pero Spotify no pudo añadir todas las
                        canciones.
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


    # ========================================================
    # RESULTADO FINAL
    # ========================================================

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

            h2 {{
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

        {mensaje}

        <p>
            <a href="/">
                Crear otra playlist
            </a>
        </p>

    </body>

    </html>

    """)
