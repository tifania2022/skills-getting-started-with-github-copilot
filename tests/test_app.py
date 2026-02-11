"""
Tests for Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities(client):
    """Reset activities to a known state before each test"""
    # Get current activities to reset them
    response = client.get("/activities")
    activities = response.json()
    
    # Store original state
    original_state = {name: activity.copy() for name, activity in activities.items()}
    
    yield client
    
    # Reset activities after test
    from src.app import activities
    for name, activity in original_state.items():
        activities[name]["participants"] = activity["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        activities = response.json()
        assert isinstance(activities, dict)
        assert "Basketball" in activities
        assert "Tennis Club" in activities
    
    def test_activities_have_required_fields(self, client):
        """Test that activities have all required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, reset_activities):
        """Test successful signup for an activity"""
        client = reset_activities
        response = client.post(
            "/activities/Basketball/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Signed up" in data["message"]
    
    def test_signup_adds_participant(self, reset_activities):
        """Test that signup actually adds the participant"""
        client = reset_activities
        
        # Get initial participants count
        response = client.get("/activities")
        initial_count = len(response.json()["Basketball"]["participants"])
        
        # Sign up a new participant
        client.post(
            "/activities/Basketball/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        
        # Verify participant was added
        response = client.get("/activities")
        final_count = len(response.json()["Basketball"]["participants"])
        assert final_count == initial_count + 1
        assert "newstudent@mergington.edu" in response.json()["Basketball"]["participants"]
    
    def test_signup_duplicate_student(self, reset_activities):
        """Test that a student cannot sign up twice for the same activity"""
        client = reset_activities
        
        # Sign up for an activity
        client.post(
            "/activities/Basketball/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        
        # Try to sign up again
        response = client.post(
            "/activities/Basketball/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_invalid_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/NonExistentActivity/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_signup_activity_full(self, reset_activities):
        """Test signup when activity is at max capacity"""
        client = reset_activities
        from src.app import activities
        
        # Set Chess Club to have only 1 spot and fill it
        activities["Chess Club"]["max_participants"] = 1
        activities["Chess Club"]["participants"] = ["student1@mergington.edu"]
        
        # Try to sign up for full activity
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "student2@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "full" in data["detail"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup/{email} endpoint"""
    
    def test_unregister_success(self, reset_activities):
        """Test successful unregistration from an activity"""
        client = reset_activities
        from src.app import activities
        
        # First sign up a student
        test_email = "unregister@mergington.edu"
        activities["Basketball"]["participants"].append(test_email)
        
        # Then unregister
        response = client.delete(
            f"/activities/Basketball/signup/{test_email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_participant(self, reset_activities):
        """Test that unregister actually removes the participant"""
        client = reset_activities
        from src.app import activities
        
        test_email = "toremove@mergington.edu"
        activities["Basketball"]["participants"].append(test_email)
        
        # Verify participant was added
        response = client.get("/activities")
        assert test_email in response.json()["Basketball"]["participants"]
        
        # Unregister
        client.delete(f"/activities/Basketball/signup/{test_email}")
        
        # Verify participant was removed
        response = client.get("/activities")
        assert test_email not in response.json()["Basketball"]["participants"]
    
    def test_unregister_nonexistent_student(self, client):
        """Test unregistering a student not in the activity"""
        response = client.delete(
            "/activities/Basketball/signup/nonexistent@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_unregister_invalid_activity(self, client):
        """Test unregistering from non-existent activity"""
        response = client.delete(
            "/activities/NonExistent/signup/test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestRoot:
    """Tests for root endpoint"""
    
    def test_root_redirect(self, client):
        """Test that root redirects to static pages"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
