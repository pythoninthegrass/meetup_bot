// Variables with defaults that can be overridden
variable "REGISTRY_URL" {
  default = "ghcr.io"
}

variable "REGISTRY_USER" {
  default = ""              // Set from GitHub Actions
}

variable "IMAGE_NAME" {
  default = "meetup_bot"    // Matches the label in Dockerfile.web
}

variable "TAG" {
  default = "latest"
}

variable "DOCKERFILE" {
  default = "Dockerfile.web"
}

// Base target with shared configuration
target "base" {
  context = "."
  dockerfile = "${DOCKERFILE}"
  args = {
    PYTHON_VERSION = "3.11"
  }
}

// Default target that extends the base
target "build" {
  inherits = ["base"]
  tags = []
}

// Group target to build both platforms
group "default" {
  targets = ["build"]
}

// Optional specific targets for each platform
target "amd64" {
  inherits = ["build"]
  platforms = ["linux/amd64"]
  cache-from = [
    "type=gha,scope=linux/amd64",
    "type=registry,ref=${REGISTRY_URL}/${REGISTRY_USER}/${IMAGE_NAME}:buildcache"
  ]
  cache-to = [
    "type=gha,mode=max,scope=linux/amd64"
  ]
}

target "arm64" {
  inherits = ["build"]
  platforms = ["linux/arm64"]
  cache-from = [
    "type=gha,scope=linux/arm64",
    "type=registry,ref=${REGISTRY_URL}/${REGISTRY_USER}/${IMAGE_NAME}:buildcache"
  ]
  cache-to = [
    "type=gha,mode=max,scope=linux/arm64"
  ]
}

// Matrix build target for multi-platform builds
target "multi-platform" {
  inherits = ["build"]
  platforms = ["linux/amd64", "linux/arm64"]
  cache-from = [
    "type=gha,scope=build",
    "type=registry,ref=${REGISTRY_URL}/${REGISTRY_USER}/${IMAGE_NAME}:buildcache"
  ]
  cache-to = [
    "type=gha,mode=max,scope=build",
    "type=registry,ref=${REGISTRY_URL}/${REGISTRY_USER}/${IMAGE_NAME}:buildcache,mode=max"
  ]
}
