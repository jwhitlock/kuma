(function(win, doc, $, StripeCheckout) {
    'use strict';
    var form = $('#contribute-form'),
        amountRadio = form.find('input[name=amount-selector]'),
        defaultAmount = form.find('input[type="radio"]:checked'),
        stripePublicKey = form.find('#id_stripe_public_key');

    var handler = StripeCheckout.configure({
        key: stripePublicKey.val(),
        locale: 'en',
        name: 'Sand Castles United',
        description: 'One-time donation',
        token: function(token) {
            $('input#stripeToken').val(token.id);
            $('form').submit();
        }
    });

    var selectedAmount = defaultAmount.length ? defaultAmount[0].value * 100 : 0;

    function onAmountSelect(ev) {
        selectedAmount = ev.target.value * 100;
    }

    function onSubmit(ev) {
        ev.preventDefault();
        handler.open({
            image: 'https://avatars1.githubusercontent.com/u/7565578?s=280&v=4',
            name: 'MDN Web Docs',
            description: 'Contribute to MDN Web Docs',
            zipCode: true,
            amount: selectedAmount,
            closed: function() {
                form.removeClass('disabled');
            }
        });
    }

    // Register event handlers
    amountRadio.change(onAmountSelect);
    $('#stripe_submit').click(onSubmit);

    // Destroy event handlers
})(window, document, jQuery, null /*StripeCheckout*/);
