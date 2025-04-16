import os

# Create 'api' folder if it doesn't exist
os.makedirs('api', exist_ok=True)

# Create __init__.py (empty)
with open('api/__init__.py', 'w') as f:
    pass

# Create index.py to wrap Flask app
with open('api/index.py', 'w') as f:
    f.write("""from app import app as application

# Vercel entry point for Flask
def handler(environ, start_response):
    return application.wsgi_app(environ, start_response)
""")

# Create vercel.json in root
with open('vercel.json', 'w') as f:
    f.write("""{
  "version": 2,
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "api/index.py" }
  ]
}
""")

# Update or create requirements.txt
with open('requirements.txt', 'w') as f:
    f.write("""flask
gunicorn
reportlab
""")

print("✅ Vercel setup files created successfully.")
print("📦 Now commit and push to GitHub, then deploy via https://vercel.com/import")
