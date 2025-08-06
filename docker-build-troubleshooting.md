# Docker Build Troubleshooting Guide

## grpcio-tools Compilation Issues

If you encounter compilation errors with grpcio-tools during Docker build, try these solutions:

### Solution 1: Use the Updated Dockerfile.dev (Recommended)
The updated `Dockerfile.dev` includes:
- Specific grpcio versions (1.59.0) that are more stable
- Additional build environment variables
- Cython3 installation for better compilation support
- Staged installation approach with fallback

### Solution 2: Use Alternative Ubuntu-based Dockerfile
If the Python slim image continues to cause issues, use:
```bash
docker build -f Dockerfile.dev.alternative -t transcriber-dev .
```

### Solution 3: Local Build with Different Approach
If both Docker approaches fail, try building directly with:
```bash
# Install grpcio first with binary wheels
pip install --prefer-binary grpcio==1.59.0 grpcio-tools==1.59.0

# Then install other requirements
pip install -r requirements-dev.txt
```

### Solution 4: Use Different Base Image
Modify the Dockerfile to use:
- `python:3.11` (full version instead of slim)
- `ubuntu:22.04` with manual Python installation

### Environment Variables for grpcio
The following environment variables help with grpcio compilation:
- `GRPC_PYTHON_BUILD_WITH_CYTHON=1`: Use Cython for compilation
- `GRPC_PYTHON_DISABLE_LIBC_COMPATIBILITY=1`: Disable libc compatibility checks
- `PIP_NO_BUILD_ISOLATION=1`: Allow pip to use system packages during build

### Common Issues and Fixes

1. **Compilation warnings as errors**: Fixed by using precompiled wheels with `--prefer-binary` and `--only-binary` flags

2. **Missing system dependencies**: Added `cython3`, `python3-dev`, and `libc6-dev` packages

3. **Version conflicts**: Pinned grpcio to specific stable version (1.59.0)

### Testing the Build
```bash
# Test the main Dockerfile
docker build -f Dockerfile.dev -t transcriber-dev .

# Test the alternative if main fails
docker build -f Dockerfile.dev.alternative -t transcriber-dev .
```

### If All Else Fails
Consider removing speechkit temporarily to isolate if it's the cause:
1. Comment out `speechkit==2.2.0` in requirements.txt
2. Build the container
3. Install speechkit manually inside the running container