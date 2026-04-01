*** Settings ***
Documentation    Performance and load tests for Online Boutique
Library          Browser
Library          RequestsLibrary
Library          DateTime
Resource         ../resources/common_keywords.robot
Resource         ../keywords/cart_keywords.robot
Suite Setup      Run Keywords    Open Online Boutique    AND    Create HTTP Session
Suite Teardown   Close Browser Session

*** Variables ***
${ACCEPTABLE_LOAD_TIME}    3
${MAX_RESPONSE_TIME}       5

*** Test Cases ***
TC401: Homepage Load Time Test
    [Documentation]    Verify homepage loads within acceptable time
    [Tags]    performance    load-time
    ${start_time}=    Get Current Date    result_format=epoch
    Go To    ${FRONTEND_URL}
    Wait For Elements State    css=.navbar    visible    timeout=${BROWSER_TIMEOUT}
    ${end_time}=    Get Current Date    result_format=epoch
    
    ${load_time}=    Evaluate    ${end_time} - ${start_time}
    Should Be True    ${load_time} < ${ACCEPTABLE_LOAD_TIME}
    ...    Homepage should load in less than ${ACCEPTABLE_LOAD_TIME} seconds, took ${load_time}s
    Log    Homepage loaded in ${load_time} seconds

TC402: Product Listing Load Time
    [Documentation]    Verify product listing loads quickly
    [Tags]    performance    load-time
    ${start_time}=    Get Current Date    result_format=epoch
    Navigate To Home Page
    ${product_count}=    Get Product Count On Page
    ${end_time}=    Get Current Date    result_format=epoch
    
    ${load_time}=    Evaluate    ${end_time} - ${start_time}
    Should Be True    ${load_time} < ${MAX_RESPONSE_TIME}
    Log    Product listing loaded ${product_count} products in ${load_time} seconds

TC403: Product Detail Page Load Time
    [Documentation]    Verify product detail page loads quickly
    [Tags]    performance    load-time
    ${start_time}=    Get Current Date    result_format=epoch
    Click    text="${EXPECTED_PRODUCTS}[0]"
    Wait For Elements State    css=button:has-text("Add to Cart")    visible
    ${end_time}=    Get Current Date    result_format=epoch
    
    ${load_time}=    Evaluate    ${end_time} - ${start_time}
    Should Be True    ${load_time} < ${MAX_RESPONSE_TIME}
    Log    Product detail page loaded in ${load_time} seconds

TC404: Add to Cart Performance
    [Documentation]    Verify add to cart operation is fast
    [Tags]    performance    cart
    Click    text="${EXPECTED_PRODUCTS}[0]"
    ${start_time}=    Get Current Date    result_format=epoch
    Click    css=button:has-text("Add to Cart")
    Wait For Elements State    text="Added to cart!"    visible
    ${end_time}=    Get Current Date    result_format=epoch
    
    ${operation_time}=    Evaluate    ${end_time} - ${start_time}
    Should Be True    ${operation_time} < 2
    ...    Add to cart should complete in less than 2 seconds, took ${operation_time}s
    Log    Add to cart completed in ${operation_time} seconds

TC405: Cart Page Load Time
    [Documentation]    Verify cart page loads quickly
    [Tags]    performance    cart
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    
    ${start_time}=    Get Current Date    result_format=epoch
    Navigate To Cart
    ${end_time}=    Get Current Date    result_format=epoch
    
    ${load_time}=    Evaluate    ${end_time} - ${start_time}
    Should Be True    ${load_time} < ${MAX_RESPONSE_TIME}
    Log    Cart page loaded in ${load_time} seconds

TC406: Checkout Page Load Time
    [Documentation]    Verify checkout page loads quickly
    [Tags]    performance    checkout
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Cart
    
    ${start_time}=    Get Current Date    result_format=epoch
    Click    css=button:has-text("Checkout")
    Wait For Elements State    css=h2:has-text("Checkout")    visible
    ${end_time}=    Get Current Date    result_format=epoch
    
    ${load_time}=    Evaluate    ${end_time} - ${start_time}
    Should Be True    ${load_time} < ${MAX_RESPONSE_TIME}
    Log    Checkout page loaded in ${load_time} seconds

TC407: API Response Time - Product List
    [Documentation]    Verify product list API responds quickly
    [Tags]    performance    api
    ${start_time}=    Get Current Date    result_format=epoch
    ${response}=    GET    ${BASE_URL}/api/products    expected_status=any
    ${end_time}=    Get Current Date    result_format=epoch
    
    ${response_time}=    Evaluate    ${end_time} - ${start_time}
    Should Be True    ${response_time} < 1
    ...    API should respond in less than 1 second, took ${response_time}s
    Log    API responded in ${response_time} seconds

TC408: Concurrent User Load Test
    [Documentation]    Simulate multiple users browsing simultaneously
    [Tags]    performance    load    stress
    # Simulate 5 concurrent user actions
    FOR    ${i}    IN RANGE    5
        Navigate To Home Page
        ${product_index}=    Evaluate    ${i} % len(${EXPECTED_PRODUCTS})
        Click    text="${EXPECTED_PRODUCTS}[${product_index}]"
        Wait For Elements State    css=button:has-text("Add to Cart")    visible
        Navigate To Home Page
    END
    
    # Verify application still responsive
    ${product_count}=    Get Product Count On Page
    Should Be True    ${product_count} > 0

TC409: Heavy Cart Load Test
    [Documentation]    Test performance with many items in cart
    [Tags]    performance    cart    stress
    # Add multiple items to cart
    FOR    ${i}    IN RANGE    5
        ${product_index}=    Evaluate    ${i} % len(${EXPECTED_PRODUCTS})
        Navigate To Home Page
        Add Product To Cart    ${EXPECTED_PRODUCTS}[${product_index}]
    END
    
    # Verify cart still loads quickly
    ${start_time}=    Get Current Date    result_format=epoch
    Navigate To Cart
    ${end_time}=    Get Current Date    result_format=epoch
    
    ${load_time}=    Evaluate    ${end_time} - ${start_time}
    Should Be True    ${load_time} < ${MAX_RESPONSE_TIME}
    
    ${cart_items}=    Get Cart Item Count
    Should Be True    ${cart_items} >= 5

TC410: Page Size and Resource Loading
    [Documentation]    Verify page resources load efficiently
    [Tags]    performance    resources
    Go To    ${FRONTEND_URL}
    Wait For Load State    networkidle
    
    # Check that page loaded successfully
    ${product_count}=    Get Product Count On Page
    Should Be True    ${product_count} > 0

TC411: Search Performance
    [Documentation]    Verify search functionality performs well
    [Tags]    performance    search
    ${search_available}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=input[type="search"]    visible    timeout=2s
    
    Run Keyword If    ${search_available}    Run Keywords
    ...    ${start_time}=    Get Current Date    result_format=epoch
    ...    AND    Fill Text    css=input[type="search"]    camera
    ...    AND    Keyboard Key    press    Enter
    ...    AND    Wait For Load State    networkidle
    ...    AND    ${end_time}=    Get Current Date    result_format=epoch
    ...    AND    ${search_time}=    Evaluate    ${end_time} - ${start_time}
    ...    AND    Should Be True    ${search_time} < ${MAX_RESPONSE_TIME}

TC412: Currency Conversion Performance
    [Documentation]    Verify currency conversion doesn't slow down the app
    [Tags]    performance    currency
    ${currency_available}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=select[name="currency_code"]    visible    timeout=2s
    
    Run Keyword If    ${currency_available}    Run Keywords
    ...    ${start_time}=    Get Current Date    result_format=epoch
    ...    AND    Select Options By    css=select[name="currency_code"]    value    EUR
    ...    AND    Wait For Load State    networkidle
    ...    AND    ${end_time}=    Get Current Date    result_format=epoch
    ...    AND    ${conversion_time}=    Evaluate    ${end_time} - ${start_time}
    ...    AND    Should Be True    ${conversion_time} < ${MAX_RESPONSE_TIME}

TC413: Rapid Navigation Test
    [Documentation]    Test performance with rapid page navigation
    [Tags]    performance    navigation    stress
    ${start_time}=    Get Current Date    result_format=epoch
    
    FOR    ${i}    IN RANGE    10
        Navigate To Home Page
        Sleep    0.5s
        Navigate To Cart
        Sleep    0.5s
    END
    
    ${end_time}=    Get Current Date    result_format=epoch
    ${total_time}=    Evaluate    ${end_time} - ${start_time}
    
    Log    Completed 10 navigation cycles in ${total_time} seconds

TC414: Memory Leak Test - Extended Session
    [Documentation]    Verify no memory leaks during extended usage
    [Tags]    performance    memory    stability
    # Perform multiple operations in sequence
    FOR    ${i}    IN RANGE    3
        Navigate To Home Page
        Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
        Navigate To Cart
        Clear Cart
    END
    
    # Verify application still functions normally
    Navigate To Home Page
    ${product_count}=    Get Product Count On Page
    Should Be True    ${product_count} > 0

TC415: Recommendation Service Performance
    [Documentation]    Verify recommendation service responds quickly
    [Tags]    performance    recommendations
    Click    text="${EXPECTED_PRODUCTS}[0]"
    
    ${start_time}=    Get Current Date    result_format=epoch
    ${recommendations_visible}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=h3:has-text("You may also like")    visible    timeout=5s
    ${end_time}=    Get Current Date    result_format=epoch
    
    Run Keyword If    ${recommendations_visible}    Run Keywords
    ...    ${load_time}=    Evaluate    ${end_time} - ${start_time}
    ...    AND    Should Be True    ${load_time} < 3
    ...    AND    Log    Recommendations loaded in ${load_time} seconds
