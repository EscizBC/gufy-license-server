const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('admin'));

// Подключение к MongoDB
mongoose.connect(process.env.MONGODB_URI, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
})
.then(() => console.log('✅ Connected to MongoDB'))
.catch(err => console.error('❌ MongoDB connection error:', err));

// Middleware для проверки аутентификации
const requireAuth = (req, res, next) => {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Basic ')) {
        return res.status(401).json({ error: 'Требуется аутентификация' });
    }
    
    const credentials = Buffer.from(authHeader.slice(6), 'base64').toString();
    const [username, password] = credentials.split(':');
    
    const adminPassword = process.env.ADMIN_PASSWORD;
    if (username === 'admin' && password === adminPassword) {
        return next();
    }
    
    res.status(401).json({ error: 'Неверные учетные данные' });
};

// Public routes
app.get('/health', (req, res) => {
    res.json({ 
        status: 'OK', 
        message: 'Pfizer License Server v2',
        database: mongoose.connection.readyState === 1 ? 'Connected' : 'Disconnected',
        timestamp: new Date().toISOString()
    });
});

app.get('/test', (req, res) => {
    res.json({
        success: true,
        message: '✅ Server is working!',
        version: '2.0'
    });
});

// Login endpoint
app.post('/api/login', (req, res) => {
    const { username, password } = req.body;
    const adminPassword = process.env.ADMIN_PASSWORD;
    
    if (username === 'admin' && password === adminPassword) {
        res.json({ success: true, message: 'Успешный вход' });
    } else {
        res.status(401).json({ success: false, error: 'Неверные учетные данные' });
    }
});

// License endpoints (protected)
app.use('/api/licenses', requireAuth, require('./routes/licenses'));

// Admin panel
app.get('/admin', (req, res) => {
    res.sendFile(__dirname + '/admin/index.html');
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 Pfizer License Server v2 running on port ${PORT}`);
});