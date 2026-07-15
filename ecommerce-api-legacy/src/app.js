const { buildApp } = require('./appFactory');

// Executable entry point: build the app and start listening. Startup is the only
// side effect and lives here, not in the composition module.
async function main() {
    const { app, config } = await buildApp();

    app.listen(config.port, () => {
        console.log(`LMS API rodando na porta ${config.port}...`);
        if (config.adminTokenGenerated) {
            console.log(`[auth] ADMIN_TOKEN not set; generated admin token: ${config.adminToken}`);
        }
    });
}

main().catch((err) => {
    console.error('Falha ao iniciar a aplicação:', err);
    process.exit(1);
});
