#!/bin/bash
# NPS V3 Analysis System - Automated Deployment Script
# Comprehensive deployment automation for production, staging, and development environments

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"

# Default configuration
DEFAULT_ENV="production"
DEFAULT_VERSION="latest"
DEFAULT_REGISTRY="yldc-docker.pkg.coding.yili.com"
DEFAULT_IMAGE_NAME="nps-v3-analyzer"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_debug() { [[ "${DEBUG:-false}" == "true" ]] && echo -e "${BLUE}[DEBUG]${NC} $*"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $*"; }

# Display usage information
usage() {
    cat << EOF
NPS V3 Analysis System - Deployment Script

Usage: $0 [OPTIONS] COMMAND

Commands:
  build                 Build Docker images
  deploy               Deploy to specified environment
  start                Start services
  stop                 Stop services
  restart              Restart services
  status               Show service status
  logs                 Show service logs
  health               Run health checks
  backup               Backup data
  rollback             Rollback to previous version
  cleanup              Cleanup unused resources

Options:
  -e, --env ENV        Target environment (production|staging|development) [default: production]
  -v, --version VER    Image version tag [default: latest]
  -r, --registry REG   Docker registry [default: yldc-docker.pkg.coding.yili.com]
  -i, --image IMAGE    Image name [default: nps-v3-analyzer]
  -f, --force          Force operation without confirmation
  -d, --debug          Enable debug mode
  -h, --help           Show this help message

Environment Variables:
  DOCKER_BUILDKIT=1    Enable Docker BuildKit (recommended)
  COMPOSE_PROJECT_NAME Override Docker Compose project name
  NPS_V3_VERSION       Override version tag

Examples:
  # Deploy to production
  $0 -e production deploy

  # Build and deploy development environment
  $0 -e development build deploy

  # Check service status
  $0 -e production status

  # View logs
  $0 -e production logs

  # Backup production data
  $0 -e production backup

  # Rollback to previous version
  $0 -e production rollback
EOF
}

# Parse command line arguments
parse_args() {
    ENV="$DEFAULT_ENV"
    VERSION="$DEFAULT_VERSION"
    REGISTRY="$DEFAULT_REGISTRY"
    IMAGE_NAME="$DEFAULT_IMAGE_NAME"
    FORCE=false
    DEBUG=false
    COMMAND=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--env)
                ENV="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -i|--image)
                IMAGE_NAME="$2"
                shift 2
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -d|--debug)
                DEBUG=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            build|deploy|start|stop|restart|status|logs|health|backup|rollback|cleanup)
                COMMAND="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    if [[ -z "$COMMAND" ]]; then
        log_error "No command specified"
        usage
        exit 1
    fi

    # Validate environment
    case "$ENV" in
        production|staging|development)
            ;;
        *)
            log_error "Invalid environment: $ENV"
            exit 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites"

    local missing_tools=()

    # Check required tools
    for tool in docker docker-compose curl; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        return 1
    fi

    # Check Docker Compose version
    local compose_version
    compose_version=$(docker-compose version --short 2>/dev/null || echo "unknown")
    log_debug "Docker Compose version: $compose_version"

    log_info "Prerequisites check passed"
    return 0
}

# Setup environment
setup_environment() {
    log_step "Setting up environment: $ENV"

    # Set environment-specific variables
    case "$ENV" in
        production)
            COMPOSE_FILE="$DEPLOYMENT_DIR/docker-compose.yml"
            ENV_FILE="$DEPLOYMENT_DIR/env/.env.production"
            ;;
        staging)
            COMPOSE_FILE="$DEPLOYMENT_DIR/docker-compose.staging.yml"
            ENV_FILE="$DEPLOYMENT_DIR/env/.env.staging"
            ;;
        development)
            COMPOSE_FILE="$DEPLOYMENT_DIR/docker-compose.dev.yml"
            ENV_FILE="$DEPLOYMENT_DIR/env/.env.development"
            ;;
    esac

    # Check if environment file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file not found: $ENV_FILE"
        return 1
    fi

    # Check if compose file exists
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Compose file not found: $COMPOSE_FILE"
        return 1
    fi

    # Export environment variables
    export COMPOSE_FILE
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-nps-v3-${ENV}}"
    export NPS_V3_VERSION="$VERSION"
    export NPS_V3_REGISTRY="$REGISTRY"
    export NPS_V3_IMAGE_NAME="$IMAGE_NAME"

    log_info "Environment setup completed"
    log_debug "Compose file: $COMPOSE_FILE"
    log_debug "Environment file: $ENV_FILE"
    log_debug "Project name: $COMPOSE_PROJECT_NAME"

    return 0
}

# Build Docker images
build_images() {
    log_step "Building Docker images"

    local full_image_name="$REGISTRY/$IMAGE_NAME:$VERSION"

    log_info "Building image: $full_image_name"

    # Change to project root for build context
    cd "$PROJECT_ROOT"

    # Build image with BuildKit if available
    if command -v docker buildx &> /dev/null; then
        log_debug "Using Docker BuildKit"
        docker buildx build \
            --tag "$full_image_name" \
            --file "deployment/Dockerfile" \
            --build-arg "BUILD_ENV=$ENV" \
            --build-arg "VERSION=$VERSION" \
            --progress=plain \
            .
    else
        log_debug "Using standard Docker build"
        DOCKER_BUILDKIT=1 docker build \
            --tag "$full_image_name" \
            --file "deployment/Dockerfile" \
            --build-arg "BUILD_ENV=$ENV" \
            --build-arg "VERSION=$VERSION" \
            .
    fi

    log_info "Image built successfully: $full_image_name"

    # Tag as latest for the environment
    local latest_tag="$REGISTRY/$IMAGE_NAME:$ENV-latest"
    docker tag "$full_image_name" "$latest_tag"
    log_info "Tagged as: $latest_tag"

    return 0
}

# Deploy services
deploy_services() {
    log_step "Deploying services to $ENV environment"

    # Create necessary directories
    local dirs=(
        "$PROJECT_ROOT/logs"
        "$PROJECT_ROOT/outputs/results"
        "$PROJECT_ROOT/outputs/reports"
        "$PROJECT_ROOT/outputs/monitoring"
        "$PROJECT_ROOT/data/cache"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log_debug "Created directory: $dir"
    done

    # Load environment variables
    if [[ -f "$ENV_FILE" ]]; then
        set -a
        source "$ENV_FILE"
        set +a
        log_debug "Loaded environment variables from: $ENV_FILE"
    fi

    # Pull images if not building locally
    if [[ "$COMMAND" != "build" ]]; then
        log_info "Pulling latest images"
        docker-compose -f "$COMPOSE_FILE" pull
    fi

    # Deploy services
    log_info "Starting services"
    docker-compose -f "$COMPOSE_FILE" up -d

    # Wait for services to be ready
    log_info "Waiting for services to be ready"
    wait_for_services

    log_info "Deployment completed successfully"
    return 0
}

# Wait for services to be ready
wait_for_services() {
    local max_wait=300  # 5 minutes
    local wait_interval=10
    local elapsed=0

    log_info "Waiting for services to be healthy"

    while [[ $elapsed -lt $max_wait ]]; do
        if check_service_health; then
            log_info "All services are healthy"
            return 0
        fi

        log_debug "Services not ready yet, waiting ${wait_interval}s..."
        sleep $wait_interval
        ((elapsed += wait_interval))
    done

    log_error "Services did not become healthy within ${max_wait}s"
    return 1
}

# Check service health
check_service_health() {
    local service_name="nps-v3-api"

    if [[ "$ENV" == "development" ]]; then
        service_name="nps-v3-api-dev"
    fi

    local container_id
    container_id=$(docker-compose -f "$COMPOSE_FILE" ps -q "$service_name" 2>/dev/null)

    if [[ -z "$container_id" ]]; then
        log_debug "Service container not found: $service_name"
        return 1
    fi

    local health_status
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "unknown")

    case "$health_status" in
        "healthy")
            return 0
            ;;
        "unhealthy")
            log_debug "Service is unhealthy: $service_name"
            return 1
            ;;
        "starting")
            log_debug "Service is starting: $service_name"
            return 1
            ;;
        *)
            # If no health check is defined, check if container is running
            local container_status
            container_status=$(docker inspect --format='{{.State.Status}}' "$container_id" 2>/dev/null || echo "unknown")

            if [[ "$container_status" == "running" ]]; then
                return 0
            else
                log_debug "Service is not running: $service_name ($container_status)"
                return 1
            fi
            ;;
    esac
}

# Start services
start_services() {
    log_step "Starting services"

    docker-compose -f "$COMPOSE_FILE" up -d
    wait_for_services

    log_info "Services started successfully"
    return 0
}

# Stop services
stop_services() {
    log_step "Stopping services"

    docker-compose -f "$COMPOSE_FILE" down

    log_info "Services stopped successfully"
    return 0
}

# Restart services
restart_services() {
    log_step "Restarting services"

    docker-compose -f "$COMPOSE_FILE" restart
    wait_for_services

    log_info "Services restarted successfully"
    return 0
}

# Show service status
show_status() {
    log_step "Service Status"

    docker-compose -f "$COMPOSE_FILE" ps

    # Show additional info for main service
    local service_name="nps-v3-api"
    if [[ "$ENV" == "development" ]]; then
        service_name="nps-v3-api-dev"
    fi

    local container_id
    container_id=$(docker-compose -f "$COMPOSE_FILE" ps -q "$service_name" 2>/dev/null)

    if [[ -n "$container_id" ]]; then
        echo ""
        log_info "Health Status:"
        docker inspect --format='Health: {{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "Health: No health check configured"

        echo ""
        log_info "Resource Usage:"
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" "$container_id"
    fi

    return 0
}

# Show service logs
show_logs() {
    log_step "Service Logs"

    local service=""
    if [[ $# -gt 0 ]]; then
        service="$1"
    fi

    if [[ -n "$service" ]]; then
        docker-compose -f "$COMPOSE_FILE" logs -f "$service"
    else
        docker-compose -f "$COMPOSE_FILE" logs -f
    fi

    return 0
}

# Run health checks
run_health_check() {
    log_step "Running health checks"

    local service_name="nps-v3-api"
    if [[ "$ENV" == "development" ]]; then
        service_name="nps-v3-api-dev"
    fi

    local container_id
    container_id=$(docker-compose -f "$COMPOSE_FILE" ps -q "$service_name" 2>/dev/null)

    if [[ -z "$container_id" ]]; then
        log_error "Service container not found: $service_name"
        return 1
    fi

    log_info "Executing health check script"
    docker exec "$container_id" /usr/local/bin/health_check.sh

    return $?
}

# Backup data
backup_data() {
    log_step "Backing up data"

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$PROJECT_ROOT/backups/$ENV/$timestamp"

    mkdir -p "$backup_dir"

    # Backup MongoDB
    log_info "Backing up MongoDB data"
    local mongo_container
    mongo_container=$(docker-compose -f "$COMPOSE_FILE" ps -q mongodb 2>/dev/null || docker-compose -f "$COMPOSE_FILE" ps -q mongodb-dev 2>/dev/null)

    if [[ -n "$mongo_container" ]]; then
        docker exec "$mongo_container" mongodump --out /tmp/backup
        docker cp "$mongo_container:/tmp/backup" "$backup_dir/mongodb"
        log_info "MongoDB backup completed"
    fi

    # Backup application data
    log_info "Backing up application data"
    cp -r "$PROJECT_ROOT/outputs" "$backup_dir/outputs"
    cp -r "$PROJECT_ROOT/logs" "$backup_dir/logs"

    log_info "Backup completed: $backup_dir"
    return 0
}

# Rollback to previous version
rollback_deployment() {
    log_step "Rolling back deployment"

    log_warn "Rollback functionality is not yet implemented"
    log_info "To manually rollback:"
    log_info "1. Stop current services: $0 -e $ENV stop"
    log_info "2. Deploy previous version: $0 -e $ENV -v PREVIOUS_VERSION deploy"

    return 1
}

# Cleanup unused resources
cleanup_resources() {
    log_step "Cleaning up unused resources"

    # Remove unused images
    log_info "Removing unused Docker images"
    docker image prune -f

    # Remove unused volumes (with confirmation)
    if [[ "$FORCE" == "true" ]]; then
        log_info "Removing unused Docker volumes"
        docker volume prune -f
    else
        log_warn "Skipping volume cleanup (use --force to enable)"
    fi

    # Remove unused networks
    log_info "Removing unused Docker networks"
    docker network prune -f

    log_info "Cleanup completed"
    return 0
}

# Main execution flow
main() {
    log_info "NPS V3 Deployment Script"
    log_info "Environment: $ENV | Version: $VERSION | Command: $COMMAND"

    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi

    # Setup environment
    if ! setup_environment; then
        exit 1
    fi

    # Execute command
    case "$COMMAND" in
        build)
            build_images
            ;;
        deploy)
            if [[ "$FORCE" == "false" ]]; then
                echo -n "Deploy to $ENV environment? [y/N] "
                read -r response
                if [[ ! "$response" =~ ^[Yy]$ ]]; then
                    log_info "Deployment cancelled"
                    exit 0
                fi
            fi
            deploy_services
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$@"
            ;;
        health)
            run_health_check
            ;;
        backup)
            backup_data
            ;;
        rollback)
            rollback_deployment
            ;;
        cleanup)
            cleanup_resources
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            usage
            exit 1
            ;;
    esac

    local exit_code=$?
    if [[ $exit_code -eq 0 ]]; then
        log_info "Operation completed successfully"
    else
        log_error "Operation failed with exit code: $exit_code"
    fi

    exit $exit_code
}

# Parse arguments and run main function
parse_args "$@"
main "$@"