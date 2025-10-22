import Adyen
from Adyen.client import AdyenClient
from Adyen.services import AdyenCheckoutApi

import json
import uuid
from main.config import get_adyen_api_key, get_adyen_merchant_account

# Init cart total
cartTotal = 10000
orderPaid = 0
gcBalance = -1
numGiftcards = 0
currency = "GBP"


def adyen_sessions(host_url):
    # Create and configure the core AdyenClient
    adyen_client = AdyenClient()
    adyen_client.xapikey = get_adyen_api_key()
    adyen_client.platform = "test" # change to live for production
    checkout_service = AdyenCheckoutApi(client=adyen_client)
    
    request = {}

    request['amount'] = {"value": "10000", "currency": "GBP"}  # amount in minor units
    request['reference'] = f"Reference {uuid.uuid4()}"  # provide your unique payment reference
    # set redirect URL required for some payment methods
    request['returnUrl'] = f"{host_url}handleShopperRedirect?shopperOrder=myRef"
    request['countryCode'] = "GB"
    request['shopperInteraction'] = "Ecommerce"

    # set lineItems: required for some payment methods (ie Klarna)
    request['lineItems'] = \
        [{"quantity": 1, "amountIncludingTax": 5000, "description": "Sunglasses"}, # amount in minor units
         {"quantity": 1, "amountIncludingTax": 5000, "description": "Headphones"}] # amount in minor units

    request['merchantAccount'] = get_adyen_merchant_account()

    result = checkout_service.payments_api.sessions(request)

    formatted_response = json.dumps((json.loads(result.raw_response)))
    print("/sessions response:\n" + formatted_response)

    return formatted_response

def adyen_getOrderState():
    global cartTotal, orderPaid, gcBalance, numGiftcards
    # init all global values, this API call is only made when instantiating the checkout
    cartTotal = 1000
    gcBalance = -1
    orderPaid = 0
    numGiftcards = 0

    jsonState = {}

    jsonState['amount'] = {"value": cartTotal, "currency": currency}
    return jsonState

def adyen_paymentMethods():
    adyen = Adyen.Adyen()
    adyen.payment.client.xapikey = get_adyen_api_key()
    adyen.payment.client.platform = "test"
    adyen.payment.client.merchant_account = get_adyen_merchant_account()
    global cartTotal, orderPaid, numGiftcards

    request = {}

    request['amount'] = {"value": cartTotal - orderPaid,"currency": currency}
    # request['shopperLocale'] = "en-US"
    request['merchantAccount'] = get_adyen_merchant_account()
    # request['countryCode'] = "GB"
    # request['shopperReference'] = "MKShopperRef"
    # request['shopperEmail'] = "liam.wyatt@adyen.com"
    # request['blockedPaymentMethods'] = ['klarna', 'klarna_account', 'klarna_paynow']


    if (numGiftcards >= 2):
        request['blockedPaymentMethods'] = ["giftcard"]

    paymentMethods = adyen.checkout.payments_api.payment_methods(request)
    formatted_paymentMethods = json.dumps((json.loads(paymentMethods.raw_response)))

    return formatted_paymentMethods

def adyen_payments(state, host_url):

    format_state = json.loads(state)

    adyen = Adyen.Adyen()
    adyen.payment.client.xapikey = get_adyen_api_key()
    adyen.payment.client.platform = "test"
    adyen.payment.client.merchant_account = get_adyen_merchant_account()

    global cartTotal, orderPaid, gcBalance, numGiftcards
    remainderAmount = cartTotal - orderPaid

    request = {}

    # If gcBalance still at initial value, there was no balance check, we just do payment
    # If gcBalance covers the remainder, we pay the remainder
    # If gcBalance not sufficient, we redeem the full value

    if 'lineItems' not in request:
        if numGiftcards == 0:
            request['lineItems'] = \
                [{"quantity": 1, "amountIncludingTax": int(cartTotal / 2), "description": "My most prestigious item"}, # amount in minor units
                 {"quantity": 1, "amountIncludingTax": int(cartTotal / 2), "description": "Equal but different item"}] 
        else:
            request['lineItems'] = \
                [{"quantity": 1, "amountIncludingTax": int(cartTotal / 2), "description": "My most prestigious item"}, 
                 {"quantity": 1, "amountIncludingTax": int(cartTotal / 2), "description": "Equal but different item"}]
                 # {"quantity": 1, "amountIncludingTax": int(0 - orderPaid), "description": "Redeemed Giftcard"}] 

    if format_state['data']['paymentMethod']['type'] == 'giftcard' and 'order' in format_state['data']:
        request['order'] = format_state['data']['order']
        numGiftcards = numGiftcards + 1
        if gcBalance >= (cartTotal - orderPaid):
            remainderAmount = cartTotal - orderPaid
            orderPaid = orderPaid + remainderAmount
        else:
            remainderAmount = gcBalance
            orderPaid = orderPaid + gcBalance
    elif 'order' in format_state['data']:
        request['order'] = format_state['data']['order']

    request['merchantAccount'] = get_adyen_merchant_account()
    request['reference'] = f"Reference {uuid.uuid4()}"  # provide your unique payment reference
    request['amount'] = {"value": remainderAmount,"currency": currency}
    request['shopperReference'] = "shopperReference"
    request['paymentMethod'] = format_state['data']['paymentMethod']
    request['returnUrl'] = f"{host_url}/redirect"
    request['shopperReference'] = "MKShopperRef"
    request['recurringProcessingModel'] = "CardOnFile"
    request['storePaymentMethod'] = "true"
    request['shopperEmail'] = "liam.wyatt@adyen.com"
    request['countryCode'] = "NL"
    # request['additionalAmount'] = {"value": 100,"currency": currency}

    if format_state['data']['paymentMethod']['type'] == "scheme":
        request['browserInfo'] = format_state['data']['browserInfo']

    paymentsResponse = adyen.checkout.payments_api.payments(request)
    formatted_payments = json.dumps((json.loads(paymentsResponse.raw_response)))

    return formatted_payments

def adyen_paymentsdetails(state):

    format_state = json.loads(state)

    adyen = Adyen.Adyen()
    adyen.payment.client.xapikey = get_adyen_api_key()
    adyen.payment.client.platform = "test" 
    adyen.payment.client.merchant_account = get_adyen_merchant_account()

    request = {}

    request = format_state['data']
    
    paymentsDetailsResponse = adyen.checkout.payments_api.payments_details(request)
    formatted_details = json.dumps((json.loads(paymentsDetailsResponse.raw_response)))

    return formatted_details

def adyen_paymentMethodsBalance(state):
    format_state = json.loads(state)
    adyen = Adyen.Adyen()
    adyen.payment.client.xapikey = get_adyen_api_key()
    adyen.payment.client.platform = "test"
    adyen.payment.client.merchant_account = get_adyen_merchant_account()

    global cartTotal, orderPaid
    remainderAmount = cartTotal - orderPaid

    request = {}

    request['amount'] = {"value": remainderAmount, "currency": currency}  # amount in minor units
    request['paymentMethod'] = format_state['paymentMethod']
    request['merchantAccount'] = get_adyen_merchant_account()

    paymentMethodsBalance = adyen.checkout.orders_api.get_balance_of_gift_card(request)
    formatted_paymentMethodsBalance = json.dumps((json.loads(paymentMethodsBalance.raw_response)))
   
    global gcBalance
    gcBalance = json.loads(formatted_paymentMethodsBalance)['balance']['value']

    return formatted_paymentMethodsBalance

def adyen_orders(state):
    adyen = Adyen.Adyen()
    adyen.payment.client.xapikey = get_adyen_api_key()
    adyen.payment.client.platform = "test"  # change to live for production
    adyen.payment.client.merchant_account = get_adyen_merchant_account()

    global cartTotal

    request = {}
    request['reference'] = "myOrderReference"
    request['amount'] = {"value": cartTotal, "currency": currency}  # amount in minor units
    request['merchantAccount'] = get_adyen_merchant_account()

    orders = adyen.checkout.orders_api.orders(request)
    formatted_orders = json.dumps((json.loads(orders.raw_response)))

    return formatted_orders

def adyen_orders_cancel(state):
    adyen = Adyen.Adyen()
    adyen.payment.client.xapikey = get_adyen_api_key()
    adyen.payment.client.platform = "test"  # change to live for production
    adyen.payment.client.merchant_account = get_adyen_merchant_account()

    format_state = json.loads(state)

    request = {}
    request['order'] = {}
    request['order']['pspReference'] = format_state['order']['pspReference']
    request['order']['orderData'] = format_state['order']['orderData']
    request['merchantAccount'] = get_adyen_merchant_account()

    orders = adyen.checkout.orders_api.cancel_order(request)
    formatted_ordersCancel = json.dumps((json.loads(orders.raw_response)))

    return formatted_ordersCancel

def adyen_pmDisable(state):
    adyen = Adyen.Adyen()
    adyen.payment.client.xapikey = get_adyen_api_key()
    adyen.payment.client.platform = "test"  # change to live for production
    adyen.payment.client.merchant_account = get_adyen_merchant_account()

    format_state = json.loads(state)
    print(format_state)

    shopperRef = "MKShopperRef"
    merchantAccount = get_adyen_merchant_account()

    endpoint = f"https://checkout-test.adyen.com/v71/storedPaymentMethods/?merchantAccount={merchantAccount}&shopperReference={shopperRef}"

    # delete = adyen.checkout.recurring_api.delete_token_for_stored_payment_details("MKShopperRef", format_state)

    return adyen.call_adyen_api(None, "checkout", "DELETE", endpoint)

    return formatted_ordersCancel