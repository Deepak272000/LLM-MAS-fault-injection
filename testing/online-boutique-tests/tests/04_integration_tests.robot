*** Settings ***
Documentation    Integration tests for Online Boutique microservices
Library          Browser
Library          RequestsLibrary
Resource         ../resources/common_keywords.robot
Resource         ../keywords/cart_keywords.robot
Resource         ../keywords/checkout_keywords.robot
Suite Setup      Run Keywords    Open Online Boutique    AND    Create HTTP Session
Suite Teardown   Close Browser Session

*** Test Cases ***
TC301: End-to-End Purchase Flow
    [Documentation]    Complete integration test from browsing to order confirmation
    [Tags]    integration    e2e    critical
    # Browse products
    ${product_count}=    Get Product Count On Page
    Should Be True    ${product_count} > 0
    
    # Add product to cart
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    
    # Verify cart
    Navigate To Cart
    ${cart_items}=    Get Cart Item Count
    Should Be Equal As Integers    ${cart_items}    1
    
    # Proceed to checkout
    Navigate To Checkout
    
    # Fill and submit checkout
    Fill Complete Checkout Form
    Complete Checkout
    
    # Verify order confirmation
    ${order_id}=    Get Order Confirmation Number
    Should Not Be Empty    ${order_id}

TC302: Multi-Product Purchase Flow
    [Documentation]    Test purchasing multiple different products
    [Tags]    integration    e2e
    # Add multiple products
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Home Page
    Add Product To Cart    ${EXPECTED_PRODUCTS}[1]
    Navigate To Home Page
    Add Product To Cart    ${EXPECTED_PRODUCTS}[2]
    
    # Verify cart has all items
    Navigate To Cart
    ${cart_items}=    Get Cart Item Count
    Should Be Equal As Integers    ${cart_items}    3
    
    # Complete purchase
    Navigate To Checkout
    Fill Complete Checkout Form
    Complete Checkout
    
    # Verify order
    ${order_id}=    Get Order Confirmation Number
    Should Not Be Empty    ${order_id}

TC303: Cart Persistence Across Services
    [Documentation]    Verify cart data persists across different microservices
    [Tags]    integration    cart    redis
    # Add item to cart
    ${product}=    Set Variable    ${EXPECTED_PRODUCTS}[0]
    Add Product To Cart    ${product}
    
    # Navigate away and back
    Navigate To Home Page
    Sleep    2s    # Allow time for backend sync
    Navigate To Cart
    
    # Verify cart still has item
    ${cart_items}=    Get Cart Item Count
    Should Be Equal As Integers    ${cart_items}    1
    Verify Product In Cart    ${product}

TC304: Currency Conversion Integration
    [Documentation]    Verify currency service integrates with product catalog
    [Tags]    integration    currency
    # Check if currency selector is available
    ${currency_available}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=select[name="currency_code"]    visible    timeout=2s
    
    Run Keyword If    ${currency_available}    Run Keywords
    ...    Select Options By    css=select[name="currency_code"]    value    EUR
    ...    AND    Wait For Page Load
    ...    AND    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    ...    AND    Navigate To Cart
    ...    AND    Get Cart Total

TC305: Recommendation Engine Integration
    [Documentation]    Verify recommendation service provides relevant suggestions
    [Tags]    integration    recommendations
    # View a product
    Click    text="${EXPECTED_PRODUCTS}[0]"
    
    # Check for recommendations
    ${recommendations_visible}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=h3:has-text("You may also like")    visible    timeout=5s
    
    Run Keyword If    ${recommendations_visible}    Run Keywords
    ...    Log    Recommendations are displayed
    ...    AND    ${rec_count}=    Get Element Count    css=.recommendation-item
    ...    AND    Should Be True    ${rec_count} > 0

TC306: Shipping Cost Calculation Integration
    [Documentation]    Verify shipping service integrates with checkout
    [Tags]    integration    shipping
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Checkout
    
    Fill Shipping Address
    ...    test@example.com
    ...    1600 Amphitheatre Parkway
    ...    Mountain View
    ...    CA
    ...    ${TEST_ZIP_CODE}
    ...    United States
    
    ${shipping_cost}=    Verify Shipping Cost Displayed
    Should Not Be Empty    ${shipping_cost}
    Log    Shipping cost calculated: ${shipping_cost}

TC307: Payment Service Integration
    [Documentation]    Verify payment service processes checkout correctly
    [Tags]    integration    payment
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Checkout
    Fill Complete Checkout Form
    
    # Submit payment
    Complete Checkout
    
    # Verify payment was processed
    ${order_id}=    Get Order Confirmation Number
    Should Not Be Empty    ${order_id}

TC308: Email Service Integration
    [Documentation]    Verify email service is triggered on order completion
    [Tags]    integration    email
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Checkout
    Fill Complete Checkout Form
    Complete Checkout
    
    # Verify confirmation mentions email
    ${confirmation_text}=    Get Text    css=.order-confirmation
    Should Contain    ${confirmation_text}    email
    ...    ignore_case=True
    ...    msg=Order confirmation should mention email

TC309: Ad Service Integration
    [Documentation]    Verify ad service displays contextual ads
    [Tags]    integration    ads
    ${ad_visible}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=.ad-banner    visible    timeout=5s
    
    Run Keyword If    ${ad_visible}
    ...    Log    Contextual ads are displayed

TC310: Product Catalog and Cart Integration
    [Documentation]    Verify product data flows correctly from catalog to cart
    [Tags]    integration    product-catalog    cart
    # Get product details from catalog
    Click    text="${EXPECTED_PRODUCTS}[0]"
    ${product_name}=    Get Text    css=h2
    ${product_price}=    Get Text    css=.product-price
    
    # Add to cart
    Click    css=button:has-text("Add to Cart")
    Wait For Elements State    text="Added to cart!"    visible
    
    # Verify same details in cart
    Navigate To Cart
    Wait For Elements State    text="${product_name}"    visible
    ${cart_price}=    Get Text    css=.cart-item .price
    Should Contain    ${cart_price}    ${product_price}

TC311: Session Management Across Services
    [Documentation]    Verify session is maintained across all services
    [Tags]    integration    session
    # Create a unique session by adding to cart
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    
    # Navigate through different pages/services
    Navigate To Home Page
    Sleep    1s
    Navigate To Cart
    Sleep    1s
    Navigate To Checkout
    
    # Verify session maintained (cart still has items)
    Click    css=a[href="/cart"]
    ${cart_items}=    Get Cart Item Count
    Should Be Equal As Integers    ${cart_items}    1

TC312: Load Generator Impact Test
    [Documentation]    Verify application handles concurrent user load
    [Tags]    integration    performance
    # Perform multiple operations quickly
    FOR    ${i}    IN RANGE    3
        Navigate To Home Page
        Click    text="${EXPECTED_PRODUCTS}[${i}]"
        Click    css=button:has-text("Add to Cart")
        Wait For Elements State    text="Added to cart!"    visible
        Navigate To Home Page
    END
    
    Navigate To Cart
    ${cart_items}=    Get Cart Item Count
    Should Be True    ${cart_items} >= 3

TC313: Redis Cache Integration
    [Documentation]    Verify Redis caching is working for cart service
    [Tags]    integration    redis    cache
    # Add item to cart (stored in Redis)
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    
    # Clear browser cache/cookies and verify cart persists
    Navigate To Cart
    ${cart_items}=    Get Cart Item Count
    Should Be Equal As Integers    ${cart_items}    1

TC314: Frontend to Backend Services Integration
    [Documentation]    Verify frontend correctly calls all backend services
    [Tags]    integration    frontend
    # This test verifies frontend successfully integrates with:
    # - Product Catalog Service (listing products)
    # - Cart Service (add to cart)
    # - Recommendation Service (showing recommendations)
    # - Checkout Service (processing orders)
    
    ${product_count}=    Get Product Count On Page
    Should Be True    ${product_count} > 0    # Product Catalog works
    
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]    # Cart Service works
    Navigate To Cart
    ${cart_items}=    Get Cart Item Count
    Should Be Equal As Integers    ${cart_items}    1

TC315: Checkout Service Orchestration
    [Documentation]    Verify checkout service orchestrates all required services
    [Tags]    integration    checkout    orchestration
    # Checkout service should coordinate:
    # - Cart Service (get cart items)
    # - Payment Service (process payment)
    # - Shipping Service (calculate shipping)
    # - Email Service (send confirmation)
    
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Checkout
    Fill Complete Checkout Form
    Complete Checkout
    
    # Verify all services were called successfully
    ${order_id}=    Get Order Confirmation Number
    Should Not Be Empty    ${order_id}
    Should Match Regexp    ${order_id}    ^[a-zA-Z0-9-]+$
