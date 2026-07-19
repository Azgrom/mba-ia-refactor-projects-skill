const { BadRequestError } = require('../errors');

const DEFAULT_REPORT_LIMIT = 100;
const MAX_REPORT_LIMIT = 100;

function parseBoundedInteger(value, { defaultValue, min, max }) {
    if (value == null || value === '') return defaultValue;
    const parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed < min || parsed > max) {
        throw new BadRequestError();
    }
    return parsed;
}

// Transport mapping for the financial report.
function reportController(reportService) {
    return async (req, res) => {
        const report = await reportService.buildFinancialReport({
            limit: parseBoundedInteger(req.query.limit, {
                defaultValue: DEFAULT_REPORT_LIMIT,
                min: 1,
                max: MAX_REPORT_LIMIT,
            }),
            offset: parseBoundedInteger(req.query.offset, {
                defaultValue: 0,
                min: 0,
                max: Number.MAX_SAFE_INTEGER,
            }),
        });
        res.json(report);
    };
}

module.exports = { reportController };
