# Minimal C++ sandbox for secure code execution
# Security: Read-only root, no network, resource limits enforced at runtime

FROM gcc:13-bookworm

# Security: Create non-root user
RUN groupadd -r runner && useradd -r -g runner runner

# Install minimal utilities (g++ already in gcc image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libc++-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create sandbox directory
RUN mkdir -p /sandbox /tmp && \
    chown runner:runner /sandbox /tmp && \
    chmod 1777 /tmp

WORKDIR /sandbox

# Run as non-root user
USER runner

# Default command (compile and run)
CMD ["g++"]
