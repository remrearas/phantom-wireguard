#!/bin/bash
# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS

set -uo pipefail

# ============================================================================
# PHANTOM HIDDEN SERVICE DEPLOYMENT
# ============================================================================

echo "=== Phantom Hidden Service Deployment ==="
echo ""

# ============================================================================
# STEP 1: Cleanup Existing Deployment
# ============================================================================
echo "Step 1: Checking for existing deployment..."

DEPLOY_DIR="/opt/phantom-hidden-service"

if [ -d "$DEPLOY_DIR" ]; then
    echo "Existing deployment found at $DEPLOY_DIR"

    # Check if docker-compose.hidden.yml exists
    if [ -f "$DEPLOY_DIR/docker-compose.hidden.yml" ]; then
        echo "Stopping and removing existing deployment..."
        cd "$DEPLOY_DIR" || exit 1

        # Stop and remove containers, networks (keep volumes for persistent onion address)
        docker compose -f docker-compose.hidden.yml down --remove-orphans

        # Force remove any remaining containers
        docker compose -f docker-compose.hidden.yml rm -f

        echo "Existing deployment stopped"
    else
        echo "No docker-compose file found, skipping container cleanup"
    fi

    # Clean deployment directory contents
    echo "Cleaning deployment directory contents..."
    cd /
    rm -rf "${DEPLOY_DIR:?}"/*
    rm -rf "${DEPLOY_DIR:?}"/.[!.]*
    echo "Directory contents cleaned"
else
    echo "No existing deployment found"
    echo "Creating deployment directory..."
    mkdir -p "$DEPLOY_DIR"
fi

echo ""

# ============================================================================
# STEP 2: Prepare Deployment Directory
# ============================================================================
echo "Step 2: Preparing deployment directory..."

# Ensure deployment directory exists
mkdir -p "$DEPLOY_DIR"

# Copy files from deployment source to deployment directory
echo "Copying new deployment files to $DEPLOY_DIR..."
cp -r "$DEPLOYMENT_FILES"/* "$DEPLOY_DIR/"

# Verify files copied
echo "Verifying deployment files..."
if [ -f "$DEPLOY_DIR/docker-compose.hidden.yml" ]; then
    echo "Deployment files copied successfully"
else
    echo "ERROR: docker-compose.hidden.yml not found!"
    exit 1
fi

# Set working directory
cd "$DEPLOY_DIR" || exit 1

echo "Deployment directory prepared"
echo ""

# ============================================================================
# STEP 3: Start Hidden Service
# ============================================================================
echo "Step 3: Starting Hidden Service containers..."

# Start services using docker-compose.hidden.yml
echo "Pulling images (if available)..."
docker compose -f docker-compose.hidden.yml pull || true

echo "Building containers..."
docker compose -f docker-compose.hidden.yml build --no-cache

echo "Starting containers in detached mode..."
docker compose -f docker-compose.hidden.yml up -d

echo "Containers started"
echo ""

# ============================================================================
# STEP 4: Wait for Onion Address
# ============================================================================
echo "Step 4: Waiting for Onion address generation..."
echo "This may take up to 90 seconds..."

MAX_ATTEMPTS=30
ATTEMPT=0
ONION_ADDRESS=""

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Try to get onion address
    ONION_ADDRESS=$(docker compose -f docker-compose.hidden.yml exec -T onion cat /var/lib/tor/hidden_service/hostname 2>&1 | grep -v "the input device is not a TTY" | grep ".onion" || true)

    if [ -n "$ONION_ADDRESS" ]; then
        break
    fi

    sleep 3
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
done
echo ""

# ============================================================================
# STEP 5: Display Results
# ============================================================================
echo ""
echo "============================================================"
echo "   HIDDEN SERVICE DEPLOYMENT COMPLETED!"
echo "============================================================"
echo ""

if [ -n "$ONION_ADDRESS" ]; then
    echo "Onion Address:"
    echo "   http://$ONION_ADDRESS"
    echo ""
    echo "Access your Phantom Deployment Wizard via Tor Browser:"
    echo "   http://$ONION_ADDRESS"
else
    echo "Warning: Could not retrieve Onion address automatically"
    echo "You can check it manually with:"
    echo "   cd $DEPLOY_DIR"
    echo "   docker compose -f docker-compose.hidden.yml exec onion cat /var/lib/tor/hidden_service/hostname"
fi

echo ""
echo "Deployment Location:"
echo "   $DEPLOY_DIR"
echo ""
echo "Docker Commands:"
echo "   View logs:  cd $DEPLOY_DIR && docker compose -f docker-compose.hidden.yml logs -f"
echo "   Restart:    cd $DEPLOY_DIR && docker compose -f docker-compose.hidden.yml restart"
echo "   Stop:       cd $DEPLOY_DIR && docker compose -f docker-compose.hidden.yml down"
echo ""

# ============================================================================
# STEP 6: Cleanup Temporary Files
# ============================================================================
echo "Step 6: Cleaning up temporary deployment files..."

if [ -d "$DEPLOYMENT_ROOT" ]; then
    echo "Removing $DEPLOYMENT_ROOT directory..."
    rm -rf "$DEPLOYMENT_ROOT"
    echo "Temporary files cleaned up"
else
    echo "No temporary files to clean (already removed)"
fi

echo ""
echo "Deployment completed successfully!"