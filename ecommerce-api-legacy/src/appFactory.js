const express = require('express');
const sqlite3 = require('sqlite3').verbose();

const { loadConfig } = require('./config');
const { Database } = require('./db/database');
const { initSchema } = require('./db/schema');
const { UserRepository } = require('./repositories/userRepository');
const { CourseRepository } = require('./repositories/courseRepository');
const { CheckoutRepository } = require('./repositories/checkoutRepository');
const { ReportRepository } = require('./repositories/reportRepository');
const { CheckoutService } = require('./services/checkoutService');
const { ReportService } = require('./services/reportService');
const { UserService } = require('./services/userService');
const { registerRoutes } = require('./http/routes');
const { errorHandler } = require('./http/errorHandler');

// Composition root: build configuration, storage, repositories, services, and
// the wired Express app. Importing this module has no side effects — it neither
// starts a server nor touches valuable state — so tools and tests can build the
// app in isolation.
async function buildApp(overrides = {}) {
    const config = overrides.config || loadConfig();
    const db = new Database(new sqlite3.Database(':memory:'));
    await initSchema(db);

    const users = new UserRepository(db);
    const courses = new CourseRepository(db);
    const checkout = new CheckoutRepository();
    const report = new ReportRepository(db);

    const checkoutService = new CheckoutService({ db, users, courses, checkout });
    const reportService = new ReportService({ report });
    const userService = new UserService({ users });

    const app = express();
    app.use(express.json());
    registerRoutes(app, { config, checkoutService, reportService, userService });
    app.use(errorHandler());

    return { app, config };
}

module.exports = { buildApp };
