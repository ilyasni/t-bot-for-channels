#!/bin/bash

set -e

# Source the utilities file
source "$(dirname "$0")/utils.sh"

# Set the compose command explicitly to use docker compose subcommand
COMPOSE_CMD="docker compose"

# Navigate to the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Project root directory (one level up from scripts)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"
# Path to the 05_run_services.sh script (Corrected from original update.sh which had 04)
RUN_SERVICES_SCRIPT="$SCRIPT_DIR/05_run_services.sh"
# Compose files (Not strictly needed here unless used directly, but good for context)
# MAIN_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
# SUPABASE_COMPOSE_FILE="$PROJECT_ROOT/supabase/docker/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"

# Check if run services script exists
if [ ! -f "$RUN_SERVICES_SCRIPT" ]; then
    log_error "$RUN_SERVICES_SCRIPT not found."
    exit 1
fi

cd "$PROJECT_ROOT"

# --- Call 03_generate_secrets.sh in update mode --- 
log_info "Ensuring .env file is up-to-date with all variables..."
bash "$SCRIPT_DIR/03_generate_secrets.sh" --update || {
    log_error "Failed to update .env configuration via 03_generate_secrets.sh. Update process cannot continue."
    exit 1
}
log_success ".env file checked and updated."
# --- End of .env update ---

# Stop all services for project 'localai'
log_info "Stopping all services for project 'localai'..."
PROJECT_CONTAINERS=$(docker ps -a -q --filter "label=com.docker.compose.project=localai")
if [ -n "$PROJECT_CONTAINERS" ]; then
    docker stop $PROJECT_CONTAINERS || log_warning "Some containers for project 'localai' failed to stop."
    # User has opted to remove 'docker rm $PROJECT_CONTAINERS' in a previous step or it was not included.
else
    log_info "No containers found for project 'localai' to stop/remove."
fi

# --- Run Service Selection Wizard FIRST to get updated profiles --- 
log_info "Running Service Selection Wizard to update service choices..."
bash "$SCRIPT_DIR/04_wizard.sh" || {
    log_error "Service Selection Wizard failed. Update process cannot continue."
    exit 1
}
log_success "Service selection updated."
# --- End of Service Selection Wizard ---

# Pull latest versions of selected containers based on updated .env
log_info "Pulling latest versions of selected containers..."
COMPOSE_FILES_FOR_PULL=("-f" "$PROJECT_ROOT/docker-compose.yml")
SUPABASE_DOCKER_DIR="$PROJECT_ROOT/supabase/docker"
SUPABASE_COMPOSE_FILE_PATH="$SUPABASE_DOCKER_DIR/docker-compose.yml"

# Check if Supabase directory and its docker-compose.yml exist
if [ -d "$SUPABASE_DOCKER_DIR" ] && [ -f "$SUPABASE_COMPOSE_FILE_PATH" ]; then
    COMPOSE_FILES_FOR_PULL+=("-f" "$SUPABASE_COMPOSE_FILE_PATH")
fi

# Use the project name "localai" for consistency.
# This command WILL respect COMPOSE_PROFILES from the .env file (updated by the wizard above).
$COMPOSE_CMD -p "localai" "${COMPOSE_FILES_FOR_PULL[@]}" pull --ignore-buildable || {
  log_error "Failed to pull Docker images for selected services. Check network connection and Docker Hub status."
  exit 1
}

# Ask user about n8n import and modify .env file
if [ -f "$ENV_FILE" ]; then
    N8N_WORKFLOWS_IMPORTED_EVER=$(grep "^N8N_WORKFLOWS_IMPORTED_EVER=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' || echo "false")

    if [[ "$N8N_WORKFLOWS_IMPORTED_EVER" == "true" ]]; then
        # Use a temporary file for sed portability
        sed 's/^RUN_N8N_IMPORT=.*/RUN_N8N_IMPORT=false/' "$ENV_FILE" > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "$ENV_FILE" || {
            log_error "Failed to set RUN_N8N_IMPORT=false in $ENV_FILE. Check permissions."
            rm -f "${ENV_FILE}.tmp"
        }
    else
        echo ""
        read -p "Import n8n workflow? (y/n) : " import_choice
        case "$import_choice" in
            [yY] | [yY][eE][sS] )
                # Use a temporary file for sed portability
                sed 's/^RUN_N8N_IMPORT=.*/RUN_N8N_IMPORT=true/' "$ENV_FILE" > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "$ENV_FILE" || {
                    log_error "Failed to set RUN_N8N_IMPORT=true in $ENV_FILE. Check permissions."
                    rm -f "${ENV_FILE}.tmp"
                }
                # Update N8N_WORKFLOWS_IMPORTED_EVER to true
                if grep -q "^N8N_WORKFLOWS_IMPORTED_EVER=" "$ENV_FILE"; then
                    sed 's/^N8N_WORKFLOWS_IMPORTED_EVER=.*/N8N_WORKFLOWS_IMPORTED_EVER=true/' "$ENV_FILE" > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "$ENV_FILE" || {
                        log_error "Failed to set N8N_WORKFLOWS_IMPORTED_EVER=true in $ENV_FILE. Check permissions."
                        rm -f "${ENV_FILE}.tmp"
                    }
                else
                    echo "N8N_WORKFLOWS_IMPORTED_EVER=true" >> "$ENV_FILE"
                fi
                ;;
            * )
                # Use a temporary file for sed portability
                sed 's/^RUN_N8N_IMPORT=.*/RUN_N8N_IMPORT=false/' "$ENV_FILE" > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "$ENV_FILE" || {
                    log_error "Failed to set RUN_N8N_IMPORT=false in $ENV_FILE. Check permissions."
                    rm -f "${ENV_FILE}.tmp"
                }
                # N8N_WORKFLOWS_IMPORTED_EVER remains false (or its current state if already in file)
                ;;
        esac
    fi

    # Ask user about n8n worker count
    if grep -q "^N8N_WORKER_COUNT=" "$ENV_FILE"; then
        CURRENT_WORKER_COUNT=$(grep "^N8N_WORKER_COUNT=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"')
        echo ""
        read -p "Enter new n8n worker count (leave empty to keep current: $CURRENT_WORKER_COUNT): " new_worker_count_raw

        if [[ -n "$new_worker_count_raw" ]]; then
            # Validate input: must be a positive integer
            if [[ "$new_worker_count_raw" =~ ^[1-9][0-9]*$ ]]; then
                NEW_WORKER_COUNT="$new_worker_count_raw"
                # Use a temporary file for sed portability (-i needs backup suffix on macOS without -e)
                sed "s/^N8N_WORKER_COUNT=.*/N8N_WORKER_COUNT=\"$NEW_WORKER_COUNT\"/" "$ENV_FILE" > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "$ENV_FILE" || {
                    log_error "Failed to update N8N_WORKER_COUNT in $ENV_FILE. Check permissions."
                    rm -f "${ENV_FILE}.tmp" # Clean up temp file on failure
                }
            else
                log_warning "Invalid input '$new_worker_count_raw'. Worker count must be a positive integer. Keeping current value ($CURRENT_WORKER_COUNT)."
            fi
        else
            log_info "Keeping current n8n worker count ($CURRENT_WORKER_COUNT)."
        fi
    else
        # This case might occur if .env exists but N8N_WORKER_COUNT was manually removed.
        # 03_generate_secrets.sh should ensure it exists on initial setup.
        log_warning "N8N_WORKER_COUNT line not found in $ENV_FILE. Cannot update worker count during this update."
        # Optionally, prompt user to add it if needed:
        # echo ""
        # read -p "N8N_WORKER_COUNT line not found. Add it now? (Enter number, or leave empty to skip): " add_worker_count
        # if [[ "$add_worker_count" =~ ^[1-9][0-9]*$ ]]; then
        #     echo "N8N_WORKER_COUNT="$add_worker_count"" >> "$ENV_FILE"
        #     log_info "Added N8N_WORKER_COUNT=$add_worker_count to $ENV_FILE."
    fi
else
    log_warning "$ENV_FILE not found. Cannot configure RUN_N8N_IMPORT or N8N_WORKER_COUNT."
fi

# Start services using the 05_run_services.sh script
log_info "Running Services..."
bash "$RUN_SERVICES_SCRIPT" || { log_error "Failed to start services. Check logs for details."; exit 1; }

log_success "Update application completed successfully!"

# --- Display Final Report with Credentials ---
bash "$SCRIPT_DIR/06_final_report.sh" || {
    log_warning "Failed to display the final report. This does not affect the update."
    # We don't exit 1 here as the update itself was successful.
}
# --- End of Final Report ---

exit 0 