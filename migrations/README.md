# Database migrations

Flask-Migrate is configured for this project. For a fresh migration history, run:

```powershell
$env:FLASK_APP = "run.py"
flask db init
flask db migrate -m "Initial ParkSmart schema"
flask db upgrade
```

Local SQLite development can also use `flask init-db`. Production deployments should use reviewed migrations rather than automatic table creation.

