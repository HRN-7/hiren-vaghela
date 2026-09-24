"""Read-only configuration check. Prints names/statuses, never credential values."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', default='.env')
    parser.add_argument('--component', choices=['all', 'frontend', 'backend'], default='all')
    args = parser.parse_args()
    config = {**dotenv_values(Path(args.env_file)), **os.environ}
    checks = []
    def required(key):
        ok = bool(str(config.get(key) or '').strip())
        checks.append({'name': key, 'status': 'present' if ok else 'missing'})
        return ok
    if args.component in ['all', 'frontend']:
        for key in ['VITE_API_BASE_URL', 'VITE_FIREBASE_API_KEY', 'VITE_FIREBASE_AUTH_DOMAIN',
                    'VITE_FIREBASE_PROJECT_ID', 'VITE_FIREBASE_APP_ID']:
            required(key)
        url = urlparse(config.get('VITE_API_BASE_URL') or '')
        checks.append({'name': 'Frontend production API URL', 'status': 'valid' if url.scheme == 'https' and url.netloc and url.path.rstrip('/').endswith('/api') else 'missing_or_invalid'})
    if args.component in ['all', 'backend']:
        for key in ['DATABASE_URL', 'FIREBASE_PROJECT_ID', 'FIREBASE_SERVICE_ACCOUNT_JSON', 'CORS_ORIGINS']:
            required(key)
        url = config.get('DATABASE_URL') or ''
        checks.append({'name': 'PostgreSQL URL', 'status': 'valid' if url.startswith(('postgres://','postgresql://','postgresql+psycopg://')) else 'missing_or_invalid'})
        try:
            account = json.loads(config.get('FIREBASE_SERVICE_ACCOUNT_JSON') or '{}')
            valid = all(account.get(k) for k in ['project_id', 'client_email', 'private_key']) and account.get('project_id') == config.get('FIREBASE_PROJECT_ID')
        except (ValueError, AttributeError):valid = False
        checks.append({'name': 'Backend Firebase service account shape/project', 'status': 'valid' if valid else 'missing_or_invalid'})
        origins = [value.strip() for value in (config.get('CORS_ORIGINS') or '').split(',') if value.strip()]
        valid = bool(origins) and all(urlparse(value).scheme == 'https' and urlparse(value).netloc and not urlparse(value).path and '*' not in value for value in origins)
        checks.append({'name': 'Exact HTTPS production CORS origins', 'status': 'valid' if valid else 'missing_or_invalid'})
    optional = {key: bool(config.get(key)) for key in ['VITE_FIREBASE_VAPID_KEY', 'VITE_FIREBASE_MESSAGING_SENDER_ID', 'DATA_GOV_API_KEY', 'PARTNER_DATA_URL', 'PARTNER_API_KEY']}
    ready = all(row['status'] in ['present', 'valid'] for row in checks)
    print(json.dumps({'configured': ready, 'checks': checks, 'optional_features': optional,
                      'note': 'Configuration shape only; no login, connection, migration, deployment or message send was attempted.'}, indent=2))
    return 0 if ready else 1


if __name__ == '__main__':
    raise SystemExit(main())
