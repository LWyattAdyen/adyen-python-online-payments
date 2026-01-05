const clientKey = document.getElementById("clientKey").innerHTML;
const { AdyenCheckout, ApplePay } = window.AdyenWeb;

// Used to finalize a checkout call in case of redirect
const urlParams = new URLSearchParams(window.location.search);
const sessionId = urlParams.get('sessionId'); // Unique identifier for the payment session
const redirectResult = urlParams.get('redirectResult');

// Some payment methods use redirects. This is where we finalize the operation
async function finalizeCheckout() {
    try {
        // Create AdyenCheckout re-using existing Session
        const checkout = await createAdyenCheckout({id: sessionId});

        // Submit the extracted redirectResult (to trigger onPaymentCompleted(result, component) handler)
        checkout.submitDetails({details: {redirectResult}});
    } catch (error) {
        console.error(error);
        alert("Error occurred. Look at console for details");
    }
}


// Calls server endpoints
async function callServer(url, data, method) {
    if (!method) {
        method = "POST"
    }
	const res = await fetch(url, {
		method: method,
		body: data ? JSON.stringify(data) : "",
		headers: {
			"Content-Type": "application/json"
		}
	});

	return await res.json();
}

// Handles responses sent from your server to the client
function handleServerResponse(res, component) {
    console.log(res);
	if (res.action) {
		component.handleAction(res.action);
	} else {
		switch (res.resultCode) {
			case "Authorised":
				window.location.href = "/result/success";
				break;
			case "Pending":
			case "Received":
				window.location.href = "/result/pending";
				break;
			case "Refused":
				window.location.href = "/result/failed";
				break;
			default:
				window.location.href = "/result/success";
				break;
		}
	}
}


async function startCheckout() {

    // get /paymentMethods API response
    // paymentMethodsResponse = await callServer("/api/paymentMethods");

    orderState = await callServer("/getOrderState");
    amount = orderState['amount']
    
    const configuration = {
        clientKey,
        amount: amount,
        environment: "test",
        locale: "en-US",
        countryCode: "GB",
        // paymentMethodsResponse: paymentMethodsResponse,
        onSubmit: async (state, component) => {
            res = await callServer("/api/payments", state)
            if (res.order && res.order.remainingAmount.value > 0) {
                paymentMethodsResponse = await callServer("/api/paymentMethods");
                console.log(adyenCheckout)
                await adyenCheckout.update({amount: res.order.remainingAmount, order: res.order, paymentMethodsResponse: paymentMethodsResponse})
            } else {
                handleServerResponse(res, component);
            }
        },
        onAdditionalDetails: async (state, component) => {
            res = callServer("/api/payments/details", state);
            handleServerResponse(res, component);
        },
        onPaymentCompleted: (result, component) => {
            handleServerResponse(result, component);
        },
        onError: (error, component) => {
            console.error(error.name, error.message, error.stack, component);
        }
    };
    const applePayConfiguration = {
                buttonColor: "black",
                configuration: {
                    merchantId: '000000000311099',
                    merchantName: 'BananaStand'
                }
            };

    // Start the AdyenCheckout and mount the element onto the 'payment' div.
    const adyenCheckout = await AdyenCheckout(configuration);
    const applepay = new ApplePay(adyenCheckout, applePayConfiguration).mount("#dropin-container");
}

startCheckout();