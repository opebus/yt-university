from modal import Dict, Image, Secret, Stub, asgi_app

stub = Stub("yt-university")

in_progress = Dict.from_name("progress", create_if_missing=True)

shared_webapp_image = (
    Image.debian_slim(python_version="3.12")
    .apt_install("libpq-dev")
    .pip_install(
        "python-dotenv", "psycopg2", "asyncpg", "sqlalchemy", "supabase", "svix"
    )
)


@stub.function(
    image=shared_webapp_image, keep_warm=1, secrets=[Secret.from_name("university")]
)
@asgi_app()
def app():
    from yt_university.api.app import web_app

    return web_app
