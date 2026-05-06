"""
Tests for main API endpoints.

These test the basic API functionality without hitting specific routes.
"""

def test_root_endpoint(client):
    """
    Test the root endpoint (/) returns a welcome message.
    
    What this tests:
    - API is responding
    - Root path works
    - Returns correct JSON structure
    
    How it works:
    1. client.get("/") makes a simulated HTTP GET request
    2. We check the status code is 200 (success)
    3. We verify the response JSON contains expected data
    """
    response = client.get("/")
    
    # Assert means "verify this is true, or the test fails"
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["version"] == "1.0.0"


def test_health_endpoint(client):
    """
    Test the /health endpoint.
    
    Health endpoints are used by monitoring systems to check if
    your API is running. If this fails, something is very wrong!
    """
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_nonexistent_endpoint(client):
    """
    Test that invalid endpoints return 404.
    
    This verifies your API properly handles requests to paths that don't exist.
    Good error handling is as important as correct functionality!
    """
    response = client.get("/this/does/not/exist")
    
    # 404 = Not Found
    assert response.status_code == 404
