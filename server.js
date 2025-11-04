const express = require('express');
require('dotenv').config();

const app = express();

// Middleware
app.use(express.json());
app.use(express.static('admin'));

// Простой health check
app.get('/health', (req, res) => {
    res.json({ 
        status: 'OK', 
        message: 'Server is running',
        timestamp: new Date().toISOString()
    });
});

// Тестовый endpoint
app.get('/test', (req, res) => {
    res.json({
        message: '✅ Server is working!',
        version: '2.0',
        env: process.env.NODE_ENV || 'development'
    });
});

// Простой лицензионный endpoint
app.post('/api/licenses', (req, res) => {
    res.json({
        success: true,
        message: 'License endpoint is working',
        action: req.body.action
    });
});

// Serve admin panel
app.get('/admin', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pfizer Admin - TEST</title>
            <style>
                body { background: #1a1a1a; color: white; font-family: Arial; padding: 50px; text-align: center; }
                .success { color: #28a428; font-size: 24px; }
            </style>
        </head>
        <body>
            <h1 class="success">✅ Админ-панель работает!</h1>
            <p>Версия: 2.0 - Тестовая</p>
            <p>Время: ${new Date()}</p>
            <button onclick="testAPI()">Тест API</button>
            <script>
                async function testAPI() {
                    const response = await fetch('/api/licenses', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({action: 'test'})
                    });
                    const result = await response.json();
                    alert('API Response: ' + JSON.stringify(result));
                }
            </script>
        </body>
        </html>
    `);
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 TEST Server running on port ${PORT}`);
    console.log(`📊 Health check: http://localhost:${PORT}/health`);
    console.log(`🔧 Admin panel: http://localhost:${PORT}/admin`);
});