// test_javascript_fetch.js - Example API fetch with error handling

async function fetchUserData(userId) {
    try {
      const response = await fetch(`https://jsonplaceholder.typicode.com/users/${userId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Failed to fetch user data:', error);
      return null;
    }
  }
  
  // Usage example
  fetchUserData(1).then(user => {
    if (user) {
      console.log('User name:', user.name);
    }
  });