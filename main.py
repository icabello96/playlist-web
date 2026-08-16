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

        <link rel="icon"
              href="https://losperrostratos.es/wp-content/uploads/2025/11/cropped-bk2a2736.jpg">

        <title>Creador de playlists</title>

        <style>

            body {
                font-family: Arial, Helvetica, sans-serif;
                font-size: 18px;

                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100svh;

                padding: 10px;

                position: relative;
            }

            body::before {
                content: "";
                position: fixed;
                inset: 0;

                background-image: url('https://losperrostratos.es/wp-content/uploads/2026/01/zevento.jpeg');
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;

                box-shadow: inset 0 0 0 1000px rgba(0,0,0,0.5);

                z-index: -1;
            }

            .container {
                width: 100%;
                max-width: 600px;
            }

            input, textarea {
                width: 100%;
                font-size: 18px;
                padding: 10px;
                box-sizing: border-box;
                border-radius: 6px;
                border: none;
            }

            textarea {
                height: 250px;
                resize: vertical;
            }

            button {
                font-size: 18px;
                padding: 12px 16px;
                margin-top: 10px;
                width: 100%;
                border-radius: 6px;
                border: none;
                cursor: pointer;
                background: #7b2727;
                color: white;
            }

            button:hover {
                opacity: 0.9;
            }

            h1, label {
                color: white;
                font-weight: bold;
            }

            h1 {
                text-align: center;
            }

            @media (max-width: 600px) {

                body {
                    align-items: flex-start;
                    padding: 15px;
                    font-size: 20px;
                }

                .container {
                    max-width: 100%;
                }

                input, textarea {
                    font-size: 20px;
                    padding: 12px;
                }

                textarea {
                    height: 50vh;
                }

                button {
                    font-size: 20px;
                    padding: 14px;
                }

                h1 {
                    font-size: 24px;
                }

            }

        </style>

    </head>

    <body>

    <div class="container">

        <h1>Creador de playlists</h1>

        <form action="/buscar_canciones/" method="post">

            <label>
                Nombre de la playlist
            </label>

            <br><br>

            <input
                type="text"
                name="nombre_playlist"
                required
            >

            <br><br>

            <label>
                Canciones (una por línea)
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

    </div>

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
        <html>
        <head>
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, Helvetica, sans-serif;
                    padding: 20px;
                }}
            </style>
        </head>
        <body>
            <h2>Error obteniendo acceso a Spotify</h2>
            <pre>{html.escape(error)}</pre>
            <p><a href="/">Volver</a></p>
        </body>
        </html>
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

    # "Desliza →" solo aparece una vez
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

        <link rel="icon"
              href="https://losperrostratos.es/wp-content/uploads/2025/11/cropped-bk2a2736.jpg">

        <title>Seleccionar canciones</title>

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: Arial, Helvetica, sans-serif;
                font-size: 18px;

                margin: 0;
                padding: 20px;

                color: #222;

                min-height: 100svh;

                position: relative;
            }}

            body::before {{
                content: "";
                position: fixed;
                inset: 0;

                background-image: url('https://losperrostratos.es/wp-content/uploads/2026/01/zevento.jpeg');
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;

                box-shadow: inset 0 0 0 1000px rgba(0,0,0,0.5);

                z-index: -1;
            }}

            .container {{
                width: 100%;
                max-width: 700px;

                margin: 0 auto;
            }}

            h1 {{
                text-align: center;
                color: white;
                margin-bottom: 8px;
            }}

            .intro {{
                text-align: center;
                color: white;
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
                border: 2px solid #7b2727;
                background: #f5e6e6;
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

                color: white;

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

                background: white;
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

                background: #7b2727;

                color: white;

                margin-top: 10px;
            }}

            button:hover {{
                opacity: 0.9;
            }}

            /* =================================================
               ENLACE
               ================================================= */

            .volver {{
                color: white;
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

        <div class="container">

            <h1>Seleccionar canciones</h1>

            <p class="intro">
                Revisa que esté seleccionada la versión correcta.
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
                <a class="volver" href="/">
                    Empezar de nuevo
                </a>
            </p>

        </div>

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
        <html>
        <head>
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, Helvetica, sans-serif;
                    padding: 20px;
                }}
            </style>
        </head>
        <body>
            <h2>Error obteniendo acceso a Spotify</h2>
            <pre>{html.escape(error)}</pre>
            <p><a href="/">Volver</a></p>
        </body>
        </html>
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
                "Grupo de música para bodas y eventos en Madrid. "
                "Música en directo para bodas, fiestas y eventos."
            ),
            "public": False
        }
    )

    if playlist.status_code != 201:

        return HTMLResponse(f"""
        <html>

        <head>

            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">

            <style>

                body {{
                    font-family: Arial, Helvetica, sans-serif;
                    padding: 20px;
                }}

            </style>

        </head>

        <body>

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

                <head>

                    <meta name="viewport"
                          content="width=device-width, initial-scale=1.0">

                    <style>

                        body {{
                            font-family: Arial, Helvetica, sans-serif;
                            padding: 20px;

                            position: relative;
                            min-height: 100svh;
                        }}

                        body::before {{
                            content: "";
                            position: fixed;
                            inset: 0;

                            background-image: url('https://losperrostratos.es/wp-content/uploads/2026/01/zevento.jpeg');
                            background-size: cover;
                            background-position: center;
                            background-repeat: no-repeat;

                            box-shadow: inset 0 0 0 1000px rgba(0,0,0,0.5);

                            z-index: -1;
                        }}

                        .container {{
                            max-width: 700px;
                            margin: auto;
                        }}

                        h2, p, pre {{
                            color: white;
                        }}

                        a {{
                            color: white;
                        }}

                    </style>

                </head>

                <body>

                <div class="container">

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

                    <pre>{html.escape(add_result.text)}</pre>

                    <p>
                        <a href="/">
                            Crear otra playlist
                        </a>
                    </p>

                </div>

                </body>

                </html>
                """)


    # ========================================================
    # RESULTADO FINAL
    # ========================================================

    if uris:

        mensaje = f"""
        <p>
            {len(uris)} canciones añadidas correctamente.
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

        <link rel="icon"
              href="https://losperrostratos.es/wp-content/uploads/2025/11/cropped-bk2a2736.jpg">

        <title>Playlist creada</title>

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: Arial, Helvetica, sans-serif;
                font-size: 18px;

                margin: 0;
                padding: 20px;

                color: white;

                min-height: 100svh;

                position: relative;
            }}

            body::before {{
                content: "";
                position: fixed;
                inset: 0;

                background-image: url('https://losperrostratos.es/wp-content/uploads/2026/01/zevento.jpeg');
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;

                box-shadow: inset 0 0 0 1000px rgba(0,0,0,0.5);

                z-index: -1;
            }}

            .container {{
                width: 100%;
                max-width: 700px;
                margin: 0 auto;
            }}

            h2 {{
                text-align: center;
                margin-bottom: 30px;
            }}

            .resultado {{
                background: rgba(255,255,255,0.92);
                color: #222;

                border-radius: 8px;

                padding: 20px;

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

            .volver {{
                color: white;
            }}

        </style>

    </head>

    <body>

        <div class="container">

            <h2>Playlist creada</h2>

            <div class="resultado">

                <p>
                    <strong>Nombre:</strong>
                    {html.escape(nombre_playlist)}
                </p>

                {mensaje}

            </div>

            <p>
                <a class="volver" href="/">
                    Crear otra playlist
                </a>
            </p>

        </div>

    </body>

    </html>

    """)
