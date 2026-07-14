// Transport mapping for checkout: read and rename the request fields, call the
// service, and serialize the result. No business logic or SQL here.
function checkoutController(checkoutService) {
    return async (req, res) => {
        const result = await checkoutService.checkoutCourse({
            name: req.body.usr,
            email: req.body.eml,
            password: req.body.pwd,
            courseId: req.body.c_id,
            card: req.body.card,
        });
        res.status(200).json(result);
    };
}

module.exports = { checkoutController };
