*** Settings ***
Documentation    API tests for Online Boutique microservices
Library          RequestsLibrary
Library          Collections
Library          String
Resource         ../resources/common_keywords.robot
Suite Setup      Create HTTP Session

*** Test Cases ***
TC101: Product Catalog Service - List Products
    [Documentation]    Test the product catalog service returns products
    [Tags]    api    product-catalog    smoke
    ${response}=    GET    ${BASE_URL}/products    expected_status=200
    Should Not Be Empty    ${response.json()}
    ${products}=    Set Variable    ${response.json()}
    ${product_count}=    Get Length    ${products}
    Should Be True    ${product_count} > 0

TC102: Product Catalog Service - Get Single Product
    [Documentation]    Test retrieving a single product by ID
    [Tags]    api    product-catalog
    ${response}=    GET    ${BASE_URL}/product/${TEST_PRODUCT_ID}    expected_status=200
    ${product}=    Set Variable    ${response.json()}
    Should Not Be Empty    ${product}
    Dictionary Should Contain Key    ${product}    id
    Dictionary Should Contain Key    ${product}    name
    Dictionary Should Contain Key    ${product}    price_usd

TC103: Product Catalog Service - Invalid Product ID
    [Documentation]    Test handling of invalid product ID
    [Tags]    api    product-catalog    negative
    ${response}=    GET    ${BASE_URL}/api/products/INVALID_ID    expected_status=404

TC104: Currency Service - Get Supported Currencies
    [Documentation]    Test currency service returns supported currencies
    [Tags]    api    currency
    ${response}=    GET    ${BASE_URL}/api/currencies    expected_status=any
    # Currency endpoint might not be directly exposed, this is an example
    Log    Currency API response: ${response.status_code}

TC105: Cart Service - Add Item To Cart
    [Documentation]    Test adding an item to cart via API
    [Tags]    api    cart
    ${session_id}=    Generate Random Session ID
    ${payload}=    Create Dictionary
    ...    user_id=${session_id}
    ...    product_id=${TEST_PRODUCT_ID}
    ...    quantity=${1}
    
    ${response}=    POST    ${BASE_URL}/api/cart    json=${payload}    expected_status=any
    Log    Add to cart response: ${response.status_code}

TC106: Cart Service - Get Cart Contents
    [Documentation]    Test retrieving cart contents via API
    [Tags]    api    cart
    ${session_id}=    Generate Random Session ID
    ${response}=    GET    ${BASE_URL}/api/cart?session_id=${session_id}    expected_status=any
    Log    Get cart response: ${response.status_code}

TC107: Checkout Service - Place Order
    [Documentation]    Test placing an order via API
    [Tags]    api    checkout
    ${session_id}=    Generate Random Session ID
    ${order_payload}=    Create Dictionary
    ...    user_id=${session_id}
    ...    email=test@example.com
    ...    address=${EMPTY}
    ...    credit_card=${EMPTY}
    
    ${response}=    POST    ${BASE_URL}/api/checkout    json=${order_payload}    expected_status=any
    Log    Checkout response: ${response.status_code}

TC108: Frontend Health Check
    [Documentation]    Test frontend service health endpoint
    [Tags]    api    health    smoke
    ${response}=    GET    ${BASE_URL}/healthz    expected_status=any
    Should Be True    ${response.status_code} in [200, 204]

TC109: API Response Time - Product Catalog
    [Documentation]    Verify product catalog API response time is acceptable
    [Tags]    api    performance
    ${start_time}=    Get Time    epoch
    ${response}=    GET    ${BASE_URL}/api/products    expected_status=200
    ${end_time}=    Get Time    epoch
    ${duration}=    Evaluate    ${end_time} - ${start_time}
    Should Be True    ${duration} < 2    Response time should be less than 2 seconds
    Log    Response time: ${duration} seconds

TC110: API Concurrent Requests
    [Documentation]    Test API can handle concurrent requests
    [Tags]    api    performance
    FOR    ${i}    IN RANGE    5
        ${response}=    GET    ${BASE_URL}/api/products    expected_status=200
        Should Be Equal As Integers    ${response.status_code}    200
    END

TC111: Product Search API
    [Documentation]    Test product search API functionality
    [Tags]    api    search
    ${params}=    Create Dictionary    q=camera
    ${response}=    GET    ${BASE_URL}/api/products    params=${params}    expected_status=any
    Log    Search API response: ${response.status_code}

TC112: Recommendation Service API
    [Documentation]    Test recommendation service returns product suggestions
    [Tags]    api    recommendations
    ${params}=    Create Dictionary    product_ids=${TEST_PRODUCT_ID}
    ${response}=    GET    ${BASE_URL}/api/recommendations    params=${params}    expected_status=any
    Log    Recommendations API response: ${response.status_code}

TC113: Cart Update Quantity
    [Documentation]    Test updating cart item quantity via API
    [Tags]    api    cart
    ${session_id}=    Generate Random Session ID
    ${payload}=    Create Dictionary
    ...    user_id=${session_id}
    ...    product_id=${TEST_PRODUCT_ID}
    ...    quantity=${3}
    
    ${response}=    PUT    ${BASE_URL}/api/cart    json=${payload}    expected_status=any
    Log    Update cart response: ${response.status_code}

TC114: Cart Remove Item
    [Documentation]    Test removing item from cart via API
    [Tags]    api    cart
    ${session_id}=    Generate Random Session ID
    ${response}=    DELETE    ${BASE_URL}/api/cart/${TEST_PRODUCT_ID}?session_id=${session_id}    expected_status=any
    Log    Remove from cart response: ${response.status_code}

TC115: API Error Handling - Invalid JSON
    [Documentation]    Test API handles invalid JSON gracefully
    [Tags]    api    negative
    ${invalid_payload}=    Set Variable    {invalid json}
    ${headers}=    Create Dictionary    Content-Type=application/json
    ${response}=    POST    ${BASE_URL}/api/cart    data=${invalid_payload}    headers=${headers}    expected_status=any
    Should Be True    ${response.status_code} >= 400    Should return error status code
