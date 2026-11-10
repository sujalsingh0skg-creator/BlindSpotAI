"""Isolated, nonproduction key material for automated tests only."""
import os

os.environ.setdefault("BLINDSPOT_ENCRYPTION_KEYS", '{"test-v1":"MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="}')
os.environ.setdefault("BLINDSPOT_ACTIVE_KEY_VERSION", "test-v1")
os.environ.setdefault("ADMIN_NAME", "Test Administrator")
os.environ.setdefault("ADMIN_PASSWORD", "TestAdminPassword9!")
