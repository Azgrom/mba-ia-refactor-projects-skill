// Transport mapping for the financial report.
function reportController(reportService) {
    return async (req, res) => {
        const report = await reportService.buildFinancialReport();
        res.json(report);
    };
}

module.exports = { reportController };
