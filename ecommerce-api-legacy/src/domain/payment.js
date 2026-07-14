// Payment domain rules. The gateway decision and status vocabulary live here as
// named concepts instead of literals scattered across the checkout handler.
const PaymentStatus = Object.freeze({
    PAID: 'PAID',
    DENIED: 'DENIED',
});

// Placeholder gateway rule preserved from the legacy behavior: a card number
// beginning with this prefix is approved, everything else is denied.
const APPROVED_CARD_PREFIX = '4';

function decidePaymentStatus(card) {
    return card.startsWith(APPROVED_CARD_PREFIX) ? PaymentStatus.PAID : PaymentStatus.DENIED;
}

module.exports = { PaymentStatus, APPROVED_CARD_PREFIX, decidePaymentStatus };
