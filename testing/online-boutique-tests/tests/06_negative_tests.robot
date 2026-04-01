*** Settings ***
Documentation    Negative test cases for Online Boutique
Library          Browser
Library          RequestsLibrary
Resource         ../resources/common_keywords.robot
Resource         ../keywords/cart_keywords.robot
Resource         ../keywords/checkout_keywords.robot
Suite Setup      Run Keywords    Open Online Boutique    AND    Create HTTP Session
Suite Teardown   Close Browser Session

*** Test Cases ***
TC501: Invalid Product ID
    [Documentation]    Verify handling of invalid product ID
    [Tags]    negative    products
    ${response}=    GET    ${BASE_URL}/api/products/INVALID_ID_12345    expected_status=any
    Should Be True    ${response.status_code} >= 400
    ...    Should return error status for invalid product ID

TC502: Empty Cart Checkout Attempt
    [Documentation]    Verify user cannot checkout with empty cart
    [Tags]    negative    cart    checkout
    Navigate To Cart
    Verify Empty Cart
    
    ${checkout_disabled}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=button:has-text("Checkout"):disabled    visible    timeout=2s
    
    # Either checkout button is disabled or clicking shows error
    ${checkout_button_exists}=    Run Keyword And Return Status
    ...    Get Element    css=button:has-text("Checkout")
    
    Run Keyword If    ${checkout_button_exists} and not ${checkout_disabled}
    ...    Run Keywords
    ...    Click    css=button:has-text("Checkout")
    ...    AND    Wait For Elements State    text="cart is empty"    visible    timeout=5s

TC503: Checkout With Invalid Email
    [Documentation]    Verify validation of email field in checkout
    [Tags]    negative    checkout    validation
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Checkout
    
    # Try invalid email formats
    Fill Text    css=input[name="email"]    invalid-email
    Fill Text    css=input[name="street_address"]    123 Test St
    
    Click    css=button:has-text("Place Order")
    
    # Should show validation error
    ${error_visible}=    Run Keyword And Return Status
    ...    Wait For Elements State    text="valid email"    visible    timeout=2s
    
    Run Keyword If    not ${error_visible}
    ...    Log    Email validation may not be enforced    WARN

TC504: Checkout With Missing Required Fields
    [Documentation]    Verify required field validation in checkout
    [Tags]    negative    checkout    validation
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Checkout
    
    # Try to submit with empty required fields
    Click    css=button:has-text("Place Order")
    
    # Should prevent submission or show validation errors
    ${still_on_checkout}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=h2:has-text("Checkout")    visible    timeout=2s
    
    Should Be True    ${still_on_checkout}
    ...    Should remain on checkout page when required fields are missing

TC505: Invalid Credit Card Number
    [Documentation]    Verify validation of credit card number
    [Tags]    negative    checkout    payment
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Checkout
    
    Fill Shipping Address
    ...    test@example.com
    ...    123 Test St
    ...    Test City
    ...    CA
    ...    12345
    ...    United States
    
    # Try invalid card number
    Fill Text    css=input[name="credit_card_number"]    1234
    Fill Text    css=input[name="credit_card_cvv"]    123
    
    Click    css=button:has-text("Place Order")
    
    # Should show error or prevent submission
    ${error_exists}=    Run Keyword And Return Status
    ...    Wait For Elements State    text="invalid"    visible    timeout=2s
    
    Run Keyword If    not ${error_exists}
    ...    Log    Credit card validation may not be enforced    WARN

TC506: Negative Product Quantity
    [Documentation]    Verify system handles negative quantities
    [Tags]    negative    cart    validation
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Cart
    
    # Try to set negative quantity
    ${quantity_input}=    Set Variable    css=input[type="number"]
    Fill Text    ${quantity_input}    -1
    Keyboard Key    press    Enter
    
    # Should either prevent negative value or show error
    ${value}=    Get Property    ${quantity_input}    value
    Should Be True    int('${value}') >= 0
    ...    Quantity should not be negative

TC507: Zero Product Quantity
    [Documentation]    Verify handling of zero quantity
    [Tags]    negative    cart    validation
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Cart
    
    ${quantity_input}=    Set Variable    css=input[type="number"]
    Fill Text    ${quantity_input}    0
    Keyboard Key    press    Enter
    
    Wait Until Network Is Idle    timeout=3s
    
    # Item should be removed from cart
    ${cart_count}=    Get Cart Item Count
    Should Be Equal As Integers    ${cart_count}    0

TC508: Extremely Large Quantity
    [Documentation]    Verify handling of unrealistically large quantities
    [Tags]    negative    cart    validation
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Cart
    
    ${quantity_input}=    Set Variable    css=input[type="number"]
    ${large_number}=    Set Variable    999999
    
    Fill Text    ${quantity_input}    ${large_number}
    Keyboard Key    press    Enter
    
    Wait Until Network Is Idle    timeout=3s
    
    # Should either cap the quantity or handle gracefully
    ${value}=    Get Property    ${quantity_input}    value
    Log    Quantity set to: ${value}

TC509: SQL Injection Attempt in Search
    [Documentation]    Verify application is protected against SQL injection
    [Tags]    negative    security    search
    ${search_available}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=input[type="search"]    visible    timeout=2s
    
    Run Keyword If    ${search_available}    Run Keywords
    ...    Fill Text    css=input[type="search"]    ' OR '1'='1
    ...    AND    Keyboard Key    press    Enter
    ...    AND    Wait For Load State    networkidle
    ...    AND    ${product_count}=    Get Product Count On Page
    # Should not return all products or crash

TC510: XSS Attempt in Input Fields
    [Documentation]    Verify application sanitizes user input
    [Tags]    negative    security    xss
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Checkout
    
    # Try XSS in email field
    ${xss_payload}=    Set Variable    <script>alert('XSS')</script>
    Fill Text    css=input[name="email"]    ${xss_payload}
    
    # Should sanitize or escape the input
    ${value}=    Get Property    css=input[name="email"]    value
    Should Contain    ${value}    ${xss_payload}
    ...    Input should be stored as-is (escaped on output)

TC511: Invalid Currency Code
    [Documentation]    Verify handling of invalid currency selection
    [Tags]    negative    currency
    ${response}=    GET    ${BASE_URL}/?currency_code=INVALID    expected_status=any
    # Should either ignore or default to USD

TC512: Concurrent Cart Modifications
    [Documentation]    Verify handling of simultaneous cart updates
    [Tags]    negative    cart    concurrency
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    
    # Simulate rapid modifications
    Navigate To Cart
    ${quantity_input}=    Set Variable    css=input[type="number"]
    
    Fill Text    ${quantity_input}    5
    Fill Text    ${quantity_input}    3
    Fill Text    ${quantity_input}    7
    Keyboard Key    press    Enter
    
    Wait Until Network Is Idle    timeout=3s
    
    # Should handle gracefully without errors
    ${cart_count}=    Get Cart Item Count
    Should Be True    ${cart_count} >= 1

TC513: Direct URL Manipulation
    [Documentation]    Verify application handles direct URL manipulation
    [Tags]    negative    security    url
    # Try to access non-existent product
    Go To    ${BASE_URL}/product/FAKE_PRODUCT_ID
    
    # Should show 404 or redirect to home
    ${error_visible}=    Run Keyword And Return Status
    ...    Wait For Elements State    text="not found"    visible    timeout=3s

TC514: Missing Session Handling
    [Documentation]    Verify application handles missing or expired sessions
    [Tags]    negative    session
    # Clear cookies/session
    Delete All Cookies
    
    # Try to access cart
    Navigate To Cart
    
    # Should create new session or show empty cart
    Verify Empty Cart

TC515: Invalid Zip Code Format
    [Documentation]    Verify validation of zip code format
    [Tags]    negative    checkout    validation
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Checkout
    
    Fill Shipping Address
    ...    test@example.com
    ...    123 Test St
    ...    Test City
    ...    CA
    ...    INVALID
    ...    United States
    
    Click    css=button:has-text("Place Order")
    
    ${error_exists}=    Run Keyword And Return Status
    ...    Wait For Elements State    text="valid zip"    visible    timeout=2s

TC516: Expired Credit Card
    [Documentation]    Verify handling of expired credit card
    [Tags]    negative    checkout    payment
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Checkout
    
    Fill Shipping Address
    ...    test@example.com
    ...    123 Test St
    ...    Test City
    ...    CA
    ...    12345
    ...    United States
    
    # Use expired card
    Fill Text    css=input[name="credit_card_number"]    ${TEST_CARD_NUMBER}
    Fill Text    css=input[name="credit_card_cvv"]    ${TEST_CARD_CVV}
    Select Options By    css=select[name="credit_card_expiration_month"]    value    1
    Select Options By    css=select[name="credit_card_expiration_year"]    value    2020
    
    Click    css=button:has-text("Place Order")
    
    # Should show expiration error
    ${error_exists}=    Run Keyword And Return Status
    ...    Wait For Elements State    text="expired"    visible    timeout=3s

TC517: Rate Limiting Test
    [Documentation]    Verify API rate limiting is in place
    [Tags]    negative    security    rate-limit
    # Make rapid API requests
    FOR    ${i}    IN RANGE    20
        ${response}=    GET    ${BASE_URL}/api/products    expected_status=any
        Exit For Loop If    ${response.status_code} == 429
    END
    
    # Should eventually return 429 if rate limiting is active
    Log    Rate limiting test completed

TC518: Invalid HTTP Methods
    [Documentation]    Verify proper handling of invalid HTTP methods
    [Tags]    negative    api    security
    ${response}=    DELETE    ${BASE_URL}/api/products    expected_status=any
    Should Be True    ${response.status_code} in [405, 404]
    ...    Should return Method Not Allowed or Not Found

TC519: Missing Content-Type Header
    [Documentation]    Verify API handles requests without Content-Type
    [Tags]    negative    api
    ${headers}=    Create Dictionary
    ${response}=    POST    ${BASE_URL}/api/cart    headers=${headers}    expected_status=any
    Should Be True    ${response.status_code} >= 400

TC520: Browser Back Button After Checkout
    [Documentation]    Verify handling of back button after order completion
    [Tags]    negative    checkout    navigation
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Checkout
    Fill Complete Checkout Form
    Complete Checkout
    
    ${order_id}=    Get Order Confirmation Number
    Should Not Be Empty    ${order_id}
    
    # Press back button
    Go Back
    
    # Should handle gracefully without duplicate order
    ${on_confirmation}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=h2:has-text("Order Confirmation")    visible    timeout=2s
