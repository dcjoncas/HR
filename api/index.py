from app import app as application

# Vercel entry point for Flask
def handler(environ, start_response):
    return application.wsgi_app(environ, start_response)
