#!/usr/bin/env bash
set -e

SECRETS_DIR="/run/secrets"

declare -A REQUIRED_SECRETS=(
    ["django_secret_key"]="DJANGO_SECRET_KEY"
    ["django_database_url"]="DJANGO_DATABASE_URL"
)

declare -A OPTIONAL_SECRETS=(
    ["django_debug"]="DJANGO_DEBUG"
    ["django_allowed_hosts"]="DJANGO_ALLOWED_HOSTS"

    ["django_deploy_url"]="DJANGO_DEPLOY_URL"
    ["django_cors_allowed_origins"]="DJANGO_CORS_ALLOWED_ORIGINS"
    ["django_csrf_trusted_origins"]="DJANGO_CSRF_TRUSTED_ORIGINS"
)

load_secret() {
    local secret_name="$1"
    local env_name="$2"
    local required="$3"

    if [ -f "$SECRETS_DIR/$secret_name" ]; then
        export "$env_name"="$(tr -d '\n' < "$SECRETS_DIR/$secret_name")"
        echo "Loaded $env_name from /run/secrets/$secret_name"
        return
    fi

    local file_var="${env_name}_FILE"
    if [ -n "${!file_var}" ] && [ -f "${!file_var}" ]; then
        export "$env_name"="$(tr -d '\n' < "${!file_var}")"
        echo "Loaded $env_name from ${!file_var}"
        return
    fi

    if [ -n "${!env_name}" ]; then
        echo "Using existing environment variable $env_name"
        return
    fi

    if [ "$required" = "true" ]; then
        echo "ERROR: Required secret $env_name is not set."
        exit 1
    else
        echo "Warning: Optional secret $env_name not set."
    fi
}

echo "Loading required secrets..."
for secret_file in "${!REQUIRED_SECRETS[@]}"; do
    load_secret "$secret_file" "${REQUIRED_SECRETS[$secret_file]}" "true"
done

echo "Loading optional secrets..."
for secret_file in "${!OPTIONAL_SECRETS[@]}"; do
    load_secret "$secret_file" "${OPTIONAL_SECRETS[$secret_file]}" "false"
done

echo "Starting Gunicorn..."
exec gunicorn config.asgi:application -c gunicorn.conf.py
