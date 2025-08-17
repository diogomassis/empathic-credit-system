#!/bin/bash

set -e

ROOT_DIR="$(dirname "$0")/services"


find "$ROOT_DIR" -type f -name "Dockerfile" | while read dockerfile; do
    SERVICE_DIR="$(dirname "$dockerfile")"
    SERVICE_NAME="$(basename "$SERVICE_DIR")"
    IMAGE_NAME="empathic-credit-system/$SERVICE_NAME"
    echo "Building image for $IMAGE_NAME in $SERVICE_DIR"
    docker build -t "$IMAGE_NAME" "$SERVICE_DIR"
done

echo "All images have been built successfully!"
