const express = require('express');
const router = express.Router();
const License = require('../models/License');

// Активация и проверка лицензии
router.post('/', async (req, res) => {
    try {
        const { action, key, hwid } = req.body;
        
        if (!action || !key) {
            return res.status(400).json({ success: false, error: 'Неверные параметры запроса' });
        }

        if (action === 'activate') {
            const license = await License.findOne({ key });
            
            if (!license) {
                return res.json({ success: false, error: 'Ключ не найден' });
            }
            
            if (!license.is_active) {
                return res.json({ success: false, error: 'Ключ деактивирован' });
            }
            
            if (license.expires_at && new Date() > license.expires_at) {
                license.is_active = false;
                await license.save();
                return res.json({ success: false, error: 'Срок действия лицензии истек' });
            }
            
            if (license.hwid && license.hwid !== hwid) {
                return res.json({ success: false, error: 'Ключ уже активирован на другом устройстве' });
            }
            
            license.hwid = hwid;
            license.activation_date = new Date();
            await license.save();
            
            return res.json({
                success: true,
                key_name: license.key_name,
                license_data: {
                    key: license.key,
                    key_name: license.key_name,
                    hwid: license.hwid,
                    activation_date: license.activation_date,
                    expires: license.expires_at ? license.expires_at.toISOString().split('T')[0] : 'Бессрочно'
                }
            });
        }
        
        if (action === 'validate') {
            const license = await License.findOne({ key, hwid });
            
            if (!license) {
                return res.json({ valid: false, error: 'Лицензия не найдена' });
            }
            
            if (!license.is_active) {
                return res.json({ valid: false, error: 'Лицензия деактивирована' });
            }
            
            if (license.expires_at && new Date() > license.expires_at) {
                license.is_active = false;
                await license.save();
                return res.json({ valid: false, error: 'Срок действия лицензии истек' });
            }
            
            return res.json({
                valid: true,
                key_name: license.key_name,
                license_data: {
                    key: license.key,
                    key_name: license.key_name,
                    hwid: license.hwid,
                    activation_date: license.activation_date,
                    expires: license.expires_at ? license.expires_at.toISOString().split('T')[0] : 'Бессрочно'
                }
            });
        }
        
        res.json({ success: false, error: 'Неизвестное действие' });
        
    } catch (error) {
        console.error('License error:', error);
        res.status(500).json({ success: false, error: 'Внутренняя ошибка сервера' });
    }
});

// Админ роуты
router.get('/admin', async (req, res) => {
    try {
        const licenses = await License.find().sort({ created_at: -1 });
        res.json(licenses);
    } catch (error) {
        res.status(500).json({ error: 'Ошибка получения ключей' });
    }
});

router.post('/admin', async (req, res) => {
    try {
        const { key, key_name, expires_at, notes } = req.body;
        
        const keyRegex = /^PFIZER-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/;
        if (!keyRegex.test(key)) {
            return res.status(400).json({ error: 'Неверный формат ключа' });
        }
        
        const license = new License({
            key,
            key_name: key_name || "Без названия",
            expires_at: expires_at ? new Date(expires_at) : null,
            notes: notes || ""
        });
        
        await license.save();
        res.json({ success: true, license });
    } catch (error) {
        if (error.code === 11000) {
            res.status(400).json({ error: 'Ключ уже существует' });
        } else {
            res.status(500).json({ error: 'Ошибка создания ключа' });
        }
    }
});

router.put('/admin/:id', async (req, res) => {
    try {
        const { key_name, is_active, expires_at, notes } = req.body;
        
        const license = await License.findById(req.params.id);
        if (!license) {
            return res.status(404).json({ error: 'Ключ не найден' });
        }
        
        if (key_name !== undefined) license.key_name = key_name;
        if (is_active !== undefined) license.is_active = is_active;
        if (expires_at !== undefined) license.expires_at = expires_at ? new Date(expires_at) : null;
        if (notes !== undefined) license.notes = notes;
        
        await license.save();
        res.json({ success: true, license });
    } catch (error) {
        res.status(500).json({ error: 'Ошибка обновления ключа' });
    }
});

router.delete('/admin/:id', async (req, res) => {
    try {
        await License.findByIdAndDelete(req.params.id);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: 'Ошибка удаления ключа' });
    }
});

module.exports = router;