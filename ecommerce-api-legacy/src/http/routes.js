const express = require('express');
const { asyncHandler } = require('./asyncHandler');
const { requireAdmin } = require('./auth');
const { checkoutController } = require('./checkoutController');
const { reportController } = require('./reportController');
const { deleteUserController } = require('./userController');

// Registers the HTTP surface. Paths and methods are unchanged from the legacy
// app; the two administrative endpoints now sit behind the admin guard.
function registerRoutes(app, { config, checkoutService, reportService, userService }) {
    const admin = requireAdmin(config);

    app.post('/api/checkout', asyncHandler(checkoutController(checkoutService)));

    app.get(
        '/api/admin/financial-report',
        admin,
        asyncHandler(reportController(reportService))
    );

    app.delete('/api/users/:id', admin, asyncHandler(deleteUserController(userService)));

    return app;
}

module.exports = { registerRoutes, express };
