#!/bin/bash
# NPS V3 Analysis System - Comprehensive Health Check Script
# Performs thorough health checks for container and service status

set -e

# Configuration
SERVICE_HOST="${NPS_V3_HOST:-localhost}"
SERVICE_PORT="${NPS_V3_PORT:-8000}"
HEALTH_ENDPOINT="${SERVICE_HOST}:${SERVICE_PORT}/healthz"
TIMEOUT="${HEALTH_CHECK_TIMEOUT:-30}"
RETRIES="${HEALTH_CHECK_RETRIES:-3}"
RETRY_DELAY=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case $level in
        INFO)
            echo -e "${timestamp} ${GREEN}[INFO]${NC} $message"
            ;;
        WARN)
            echo -e "${timestamp} ${YELLOW}[WARN]${NC} $message"
            ;;
        ERROR)
            echo -e "${timestamp} ${RED}[ERROR]${NC} $message"
            ;;
        DEBUG)
            if [[ "${NPS_V3_DEBUG:-false}" == "true" ]]; then
                echo -e "${timestamp} ${BLUE}[DEBUG]${NC} $message"
            fi
            ;;
    esac
}

# Check if required commands are available
check_dependencies() {
    local missing_deps=()

    for cmd in curl timeout; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log ERROR "Missing required dependencies: ${missing_deps[*]}"
        return 1
    fi

    return 0
}

# Check basic HTTP health endpoint
check_http_health() {
    local url="http://${HEALTH_ENDPOINT}"
    local attempt=1

    log INFO "Checking HTTP health endpoint: $url"

    while [[ $attempt -le $RETRIES ]]; do
        log DEBUG "Health check attempt $attempt/$RETRIES"

        if timeout "$TIMEOUT" curl -f -s "$url" > /dev/null 2>&1; then
            log INFO "HTTP health check passed"
            return 0
        fi

        if [[ $attempt -lt $RETRIES ]]; then
            log WARN "Health check attempt $attempt failed, retrying in ${RETRY_DELAY}s..."
            sleep "$RETRY_DELAY"
        fi

        ((attempt++))
    done

    log ERROR "HTTP health check failed after $RETRIES attempts"
    return 1
}

# Check detailed health status
check_detailed_health() {
    local url="http://${HEALTH_ENDPOINT}/detailed"
    local response

    log INFO "Checking detailed health status"

    response=$(timeout "$TIMEOUT" curl -s "$url" 2>/dev/null) || {
        log WARN "Could not retrieve detailed health status"
        return 0  # Non-critical failure
    }

    # Parse JSON response (basic parsing)
    if echo "$response" | grep -q '"status":"healthy"'; then
        log INFO "Detailed health check: HEALTHY"

        # Extract and log component status if available
        if echo "$response" | grep -q '"components"'; then
            log DEBUG "Component health details available"
        fi

        return 0
    elif echo "$response" | grep -q '"status":"unhealthy"'; then
        log WARN "Detailed health check: UNHEALTHY"

        # Try to extract error details
        local errors
        errors=$(echo "$response" | sed -n 's/.*"errors":\[\([^]]*\)\].*/\1/p' | tr ',' '\n' | head -3)
        if [[ -n "$errors" ]]; then
            log WARN "Health issues detected:"
            echo "$errors" | while IFS= read -r error; do
                log WARN "  - $(echo "$error" | sed 's/[\"{}]//g')"
            done
        fi

        return 1
    else
        log WARN "Could not parse detailed health response"
        return 0  # Non-critical failure
    fi
}

# Check database connectivity
check_database() {
    local url="http://${HEALTH_ENDPOINT}/db"

    log INFO "Checking database connectivity"

    if timeout "$TIMEOUT" curl -f -s "$url" > /dev/null 2>&1; then
        log INFO "Database connectivity check passed"
        return 0
    else
        log ERROR "Database connectivity check failed"
        return 1
    fi
}

# Check cache connectivity (Redis)
check_cache() {
    local url="http://${HEALTH_ENDPOINT}/cache"

    log INFO "Checking cache connectivity"

    if timeout "$TIMEOUT" curl -f -s "$url" > /dev/null 2>&1; then
        log INFO "Cache connectivity check passed"
        return 0
    else
        log WARN "Cache connectivity check failed (non-critical)"
        return 0  # Cache failure is non-critical for basic operation
    fi
}

# Check LLM service availability
check_llm_service() {
    local url="http://${HEALTH_ENDPOINT}/llm"

    log INFO "Checking LLM service availability"

    if timeout "$TIMEOUT" curl -f -s "$url" > /dev/null 2>&1; then
        log INFO "LLM service availability check passed"
        return 0
    else
        log WARN "LLM service availability check failed (non-critical)"
        return 0  # LLM service failure is non-critical for basic health
    fi
}

# Check system resources
check_system_resources() {
    log INFO "Checking system resources"

    # Check disk space
    local disk_usage
    disk_usage=$(df /app 2>/dev/null | awk 'NR==2{print $5}' | sed 's/%//')

    if [[ -n "$disk_usage" ]] && [[ "$disk_usage" -lt 95 ]]; then
        log INFO "Disk usage: ${disk_usage}% (OK)"
    elif [[ -n "$disk_usage" ]]; then
        log WARN "Disk usage: ${disk_usage}% (HIGH)"
    else
        log DEBUG "Could not check disk usage"
    fi

    # Check memory usage (if available)
    if command -v free &> /dev/null; then
        local mem_usage
        mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')

        if [[ "$mem_usage" -lt 90 ]]; then
            log INFO "Memory usage: ${mem_usage}% (OK)"
        else
            log WARN "Memory usage: ${mem_usage}% (HIGH)"
        fi
    fi

    return 0
}

# Check log file accessibility
check_logs() {
    local log_dir="/app/logs"

    log DEBUG "Checking log file accessibility"

    if [[ -d "$log_dir" ]] && [[ -w "$log_dir" ]]; then
        log DEBUG "Log directory is accessible and writable"
        return 0
    else
        log WARN "Log directory is not accessible or not writable"
        return 0  # Non-critical for health check
    fi
}

# Check output directory accessibility
check_outputs() {
    local output_dir="/app/outputs"

    log DEBUG "Checking output directory accessibility"

    if [[ -d "$output_dir" ]] && [[ -w "$output_dir" ]]; then
        log DEBUG "Output directory is accessible and writable"
        return 0
    else
        log WARN "Output directory is not accessible or not writable"
        return 0  # Non-critical for health check
    fi
}

# Main health check function
main() {
    local exit_code=0
    local start_time
    start_time=$(date +%s)

    log INFO "Starting NPS V3 health check (PID: $$)"
    log INFO "Configuration: HOST=$SERVICE_HOST, PORT=$SERVICE_PORT, TIMEOUT=${TIMEOUT}s, RETRIES=$RETRIES"

    # Check dependencies first
    if ! check_dependencies; then
        log ERROR "Health check cannot proceed due to missing dependencies"
        exit 1
    fi

    # Perform all health checks
    local checks=(
        "check_http_health:CRITICAL"
        "check_detailed_health:OPTIONAL"
        "check_database:CRITICAL"
        "check_cache:OPTIONAL"
        "check_llm_service:OPTIONAL"
        "check_system_resources:OPTIONAL"
        "check_logs:OPTIONAL"
        "check_outputs:OPTIONAL"
    )

    local failed_critical=0
    local failed_optional=0

    for check_spec in "${checks[@]}"; do
        local check_func="${check_spec%:*}"
        local check_type="${check_spec#*:}"

        log DEBUG "Running check: $check_func ($check_type)"

        if ! "$check_func"; then
            if [[ "$check_type" == "CRITICAL" ]]; then
                ((failed_critical++))
                exit_code=1
            else
                ((failed_optional++))
            fi
        fi
    done

    # Calculate execution time
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Report results
    log INFO "Health check completed in ${duration}s"

    if [[ $failed_critical -eq 0 ]]; then
        log INFO "HEALTH CHECK PASSED - Service is healthy"
        if [[ $failed_optional -gt 0 ]]; then
            log WARN "Note: $failed_optional optional checks failed (non-critical)"
        fi
    else
        log ERROR "HEALTH CHECK FAILED - $failed_critical critical checks failed"
        if [[ $failed_optional -gt 0 ]]; then
            log ERROR "Additionally: $failed_optional optional checks failed"
        fi
    fi

    exit $exit_code
}

# Handle signals for graceful shutdown
trap 'log WARN "Health check interrupted"; exit 130' INT TERM

# Run main function
main "$@"