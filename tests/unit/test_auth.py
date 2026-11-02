import pytest

def test_register_and_login(client):
    # 1. Register User
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "kartik@university.edu",
            "username": "kartik",
            "full_name": "Kartik Lakhera",
            "password": "SecurePassword123",
            "role": "ADMIN",
        },
    )
    assert reg_response.status_code == 201
    user_data = reg_response.json()
    assert user_data["username"] == "kartik"
    assert user_data["role"] == "ADMIN"

    # 2. Login User
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "kartik", "password": "SecurePassword123"},
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 3. Access /me Endpoint
    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["username"] == "kartik"
    assert me_data["email"] == "kartik@university.edu"
