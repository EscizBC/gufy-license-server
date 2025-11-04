const mongoose = require('mongoose');

const licenseSchema = new mongoose.Schema({
    key: { 
        type: String, 
        required: true, 
        unique: true,
        match: /^PFIZER-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/
    },
    key_name: { 
        type: String, 
        default: "Без названия",
        maxlength: 100
    },
    hwid: { 
        type: String, 
        default: null 
    },
    is_active: { 
        type: Boolean, 
        default: true 
    },
    activation_date: { 
        type: Date, 
        default: null 
    },
    created_at: { 
        type: Date, 
        default: Date.now 
    },
    expires_at: { 
        type: Date, 
        default: null 
    },
    notes: {
        type: String,
        default: ""
    }
});

licenseSchema.index({ key: 1 });
licenseSchema.index({ hwid: 1 });
licenseSchema.index({ is_active: 1 });

module.exports = mongoose.model('License', licenseSchema);