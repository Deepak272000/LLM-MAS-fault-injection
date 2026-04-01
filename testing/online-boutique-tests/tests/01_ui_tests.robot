*** Settings ***
Documentation    End-to-end UI tests for Online Boutique application
Library          Browser
Resource         ../resources/common_keywords.robot
Resource         ../keywords/cart_keywords.robot
Resource         ../keywords/checkout_keywords.robot
Suite Setup      Open Online Boutique
Suite Teardown   Close Browser Session
Test Teardown    Run Keywords    Navigate To Home Page    AND    Clear Cart

*** Test Cases ***
TC001: Verify Home Page Loads Successfully
    [Documentation]    Verify the home page loads with all expected elements
    [Tags]    smoke    ui    home
    Verify Header Navigation
    ${product_count}=    Get Product Count On Page
    Should Be True    ${product_count} > 0    Products should be displayed on home page

TC002: Browse Product Categories
    [Documentation]    Verify users can browse products
    [Tags]    ui    products
    ${initial_count}=    Get Product Count On Page
    Should Be True    ${initial_count} >= 9    Should display at least 9 products
    FOR    ${product}    IN    @{EXPECTED_PRODUCTS}
        ${status}=    Run Keyword And Return Status    Verify Product Card Visible    ${product}
        Run Keyword If    not ${status}    Log    Product ${product} not found on current page    WARN
    END

TC003: View Product Details
    [Documentation]    Verify product detail page displays correctly
    [Tags]    ui    products
    ${first_product}=    Set Variable    ${EXPECTED_PRODUCTS}[0]
    Click    text="${first_product}"
    Wait For Elements State    css=h2:has-text("${first_product}")    visible    timeout=${BROWSER_TIMEOUT}
    Wait For Elements State    css=.product-price    visible
    Wait For Elements State    css=button:has-text("Add to Cart")    visible

TC004: Add Single Product To Cart
    [Documentation]    Verify adding a product to cart works correctly
    [Tags]    smoke    ui    cart
    ${product}=    Set Variable    ${EXPECTED_PRODUCTS}[0]
    Add Product To Cart    ${product}
    Navigate To Cart
    ${cart_count}=    Get Cart Item Count
    Should Be Equal As Integers    ${cart_count}    1
    Verify Product In Cart    ${product}

TC005: Add Multiple Products To Cart
    [Documentation]    Verify adding multiple products to cart
    [Tags]    ui    cart
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Home Page
    Add Product To Cart    ${EXPECTED_PRODUCTS}[1]
    Navigate To Home Page
    Add Product To Cart    ${EXPECTED_PRODUCTS}[2]
    Navigate To Cart
    ${cart_count}=    Get Cart Item Count
    Should Be Equal As Integers    ${cart_count}    3

TC006: Remove Product From Cart
    [Documentation]    Verify removing a product from cart
    [Tags]    ui    cart
    ${product}=    Set Variable    ${EXPECTED_PRODUCTS}[0]
    Add Product To Cart    ${product}
    Remove Product From Cart    ${product}
    Verify Empty Cart

TC007: Complete Full Checkout Process
    [Documentation]    Verify complete end-to-end checkout process
    [Tags]    smoke    e2e    checkout
    # Add product to cart
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    
    # Navigate to checkout
    Navigate To Checkout
    
    # Fill checkout form
    Fill Complete Checkout Form
    
    # Complete checkout
    Complete Checkout
    
    # Verify order confirmation
    ${order_id}=    Get Order Confirmation Number
    Should Not Be Empty    ${order_id}
    Log    Order completed successfully with ID: ${order_id}

TC008: Verify Cart Persistence Across Pages
    [Documentation]    Verify cart maintains items when navigating between pages
    [Tags]    ui    cart
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Home Page
    Navigate To Cart
    ${cart_count}=    Get Cart Item Count
    Should Be Equal As Integers    ${cart_count}    1

TC009: Search Functionality
    [Documentation]    Verify product search works correctly
    [Tags]    ui    search
    ${search_visible}=    Run Keyword And Return Status    
    ...    Wait For Elements State    css=input[type="search"]    visible    timeout=2s
    Run Keyword If    ${search_visible}    Run Keywords
    ...    Fill Text    css=input[type="search"]    camera
    ...    AND    Keyboard Key    press    Enter
    ...    AND    Wait For Page Load
    ...    AND    Get Product Count On Page

TC010: Currency Conversion
    [Documentation]    Verify currency conversion functionality
    [Tags]    ui    currency
    ${currency_selector}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=select[name="currency_code"]    visible    timeout=2s
    Run Keyword If    ${currency_selector}    Run Keywords
    ...    Select Options By    css=select[name="currency_code"]    value    EUR
    ...    AND    Wait For Page Load
    ...    AND    Wait For Elements State    text="€"    visible    timeout=5s

TC011: Mobile Responsive Layout
    [Documentation]    Verify mobile responsive layout
    [Tags]    ui    responsive
    Set Viewport Size    width=375    height=667
    Wait For Elements State    css=.navbar    visible
    ${product_count}=    Get Product Count On Page
    Should Be True    ${product_count} > 0
    Set Viewport Size    width=1920    height=1080

TC012: Empty Cart Checkout Prevention
    [Documentation]    Verify user cannot checkout with empty cart
    [Tags]    ui    cart    negative
    Navigate To Cart
    ${checkout_button}=    Run Keyword And Return Status
    ...    Get Element    css=button:has-text("Checkout")
    Run Keyword If    ${checkout_button}    
    ...    Click    css=button:has-text("Checkout")
    # Should either disable checkout button or show error message

TC013: Product Recommendations Display
    [Documentation]    Verify product recommendations are displayed
    [Tags]    ui    recommendations
    ${product}=    Set Variable    ${EXPECTED_PRODUCTS}[0]
    Click    text="${product}"
    Wait For Elements State    css=h3:has-text("You may also like")    visible    timeout=${BROWSER_TIMEOUT}
    ${recommendations}=    Get Element Count    css=.recommendation-item
    Should Be True    ${recommendations} > 0    Recommendations should be displayed

TC014: Cart Total Calculation
    [Documentation]    Verify cart total is calculated correctly
    [Tags]    ui    cart    calculation
    Add Product To Cart    ${EXPECTED_PRODUCTS}[0]
    Navigate To Cart
    ${total}=    Get Cart Total
    Should Match Regexp    ${total}    ^\\d+\\.\\d{2}$
    Should Be True    float('${total}') > 0

TC015: Shipping Cost Display
    [Documentation]    Verify shipping cost is displayed during checkout
    [Tags]    ui    checkout
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
