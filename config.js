/**
 * Worldocs Frontend Configuration
 * 
 * Instructions:
 * 1. Deploy your backend (app.py) to a service like Render.com.
 * 2. Copy the URL of your deployed backend (e.g., https://worldocs-backend.onrender.com).
 * 3. Replace the placeholder below with your actual backend URL.
 */

const CONFIG = {
    // REPLACE THIS URL with your deployed backend URL from Render
    API_BASE_URL: "https://your-backend-name.onrender.com",
    
    // Automatically use localhost if running locally
    get API_URL() {
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            return 'http://127.0.0.1:8000';
        }
        return this.API_BASE_URL;
    },

    // WebSocket helper
    get WS_URL() {
        const url = this.API_URL.replace(/^http/, 'ws');
        return url;
    }
};

window.API_CONFIG = CONFIG;
